import base64
import os
import time
import tomllib
from typing import Tuple

import uvicorn
from cachetools import FIFOCache, cached
from fastapi import FastAPI
from hishel import AsyncCacheClient, AsyncInMemoryStorage
from httpx import Limits
from loguru import logger
from pydantic import BaseModel, Field
from starlette.background import BackgroundTasks
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.status import HTTP_204_NO_CONTENT, HTTP_200_OK

CONFIG_PATH = os.getenv(
    "CONFIG_PATH",
    os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    + os.sep
    + "config"
    + os.sep
    + "config.toml",
)

DEFAULT_CONFIG = {
    "Common": {
        "use_host": True,
        "custom_host": "",
        "real_ip_header": "x-real-ip",
        "custom_gtm_js_path": "/js/jQuery.js",
        "custom_gtag_js_path": "/js/bootstrap.bundle.min.js",
        "custom_gtag_destination_path": "/admin/dest",
        "custom_analytics_collect_path": "/admin/login",
        "server_header": True,
    },
    "Http": {"timeout": 10.0, "max_connections": 1000, "cache_capacity": 64},
    "Server": {"host": "0.0.0.0", "port": 8000, "reload": True, "workers": 1},
}


class CommonConfigModel(BaseModel):
    use_host: bool = Field(
        True, description="Whether to use the Host in the request header directly"
    )
    """Whether to use the Host in the request header directly"""
    custom_host: str = Field("", description="Custom Host")
    """Custom Host"""
    real_ip_header: str = Field("x-real-ip", description="Real IP Header")
    """Real IP Header"""
    custom_gtm_js_path: str = Field(
        "/js/jQuery.js", description="Google Tag Manager JavaScript Path"
    )
    """Google Tag Manager JavaScript Path"""
    custom_gtag_js_path: str = Field(
        "/js/bootstrap.bundle.min.js", description="Gtag JavaScript Path"
    )
    """Gtag JavaScript Path"""
    custom_gtag_destination_path: str = Field(
        "/admin/dest", description="Gtag Destination Path"
    )
    """Gtag Destination Path"""
    custom_analytics_collect_path: str = Field(
        "/admin/login", description="Analytics Collect Path"
    )
    """Analytics Collect Path"""
    server_header: bool = Field(
        True,
        description='Whether to carry {"X-Server": "gtm-proxy"} in the response header',
    )
    """Whether to carry {"X--Server": "gtm-proxy"} in the response header"""
    cache_capacity: int = Field(64, description="Cache capacity")
    """Cache capacity"""


class HttpConfigModel(BaseModel):
    timeout: float = Field(10.0, description="Timeout")
    """Timeout"""
    max_connections: int = Field(1000, description="Maximum number of connections")
    """Maximum number of connections"""
    cache_capacity: int = Field(64, description="Cache capacity")
    """Cache capacity"""


class ServerConfigModel(BaseModel):
    host: str = Field("0.0.0.0", description="Server bind address")
    """Server bind address"""
    port: int = Field(8000, description="Server port")
    """Server port"""
    reload: bool = Field(True, description="Enable auto-reload for development")
    """Enable auto-reload for development"""
    workers: int = Field(1, description="Number of worker processes")
    """Number of worker processes"""


class GtmProxyConfig(BaseModel):
    Common: CommonConfigModel
    Http: HttpConfigModel
    Server: ServerConfigModel


class AppConfig:
    def __init__(self, config_path: str | os.PathLike = "./config.toml"):
        super().__init__()
        self.config_path = config_path
        self.data: GtmProxyConfig | None = None

        if os.path.exists(self.config_path):
            self.load()
        else:
            # noinspection PyArgumentList
            self.data = GtmProxyConfig.model_validate(DEFAULT_CONFIG)
            logger.info(f"Configuration loaded from default config")

    def load(self) -> None:
        """加载配置"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                toml_data = tomllib.loads(f.read())
            # 💩
            # noinspection PyTypeChecker
            toml_data = dict(toml_data)
            self.data = GtmProxyConfig.model_validate(toml_data)
            logger.info(f"Configuration loaded from {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")


config = AppConfig(config_path=CONFIG_PATH)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,  # noqa
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = AsyncCacheClient(
    limits=Limits(max_connections=config.data.Http.max_connections),
    storage=AsyncInMemoryStorage(capacity=config.data.Http.cache_capacity),
    timeout=config.data.Http.timeout,
)


# 优化缓存函数
@cached(cache=FIFOCache(maxsize=config.data.Common.cache_capacity))
def replace(data: str, old: Tuple, new: Tuple) -> str:
    """
    替换字符串中的内容，使用缓存提高性能
    """
    for i in range(len(old)):
        data = data.replace(old[i], new[i])
    return data


@app.get(config.data.Common.custom_gtm_js_path)
async def get_gtm_js(id: str, request: Request) -> Response:
    headers_to_exclude = {
        config.data.Common.real_ip_header.lower(),
        "x-forwarded-for",
        "x-real-ip",
        "x-forwarded-proto",
        "host",
        "content-length",  # 通常需要移除
        "transfer-encoding",  # 通常需要移除
    }
    headers = {
        k: v for k, v in request.headers.items() if k.lower() not in headers_to_exclude
    }
    query_params = dict(request.query_params)
    try:
        query_params["id"] = str(base64.b64decode(query_params["id"]), "utf-8")
    except:
        pass
    gtm_js = await client.get(
        f"https://www.googletagmanager.com/gtm.js",
        params=query_params,
        headers=headers,
    )
    gtm_js_content = replace(
        gtm_js.text,
        ("www.googletagmanager.com", "/gtag/js", "/gtag/destination"),
        (
            config.data.Common.custom_host
            if config.data.Common.use_host is False
            else request.headers["Host"],
            config.data.Common.custom_gtag_js_path,
            config.data.Common.custom_gtag_destination_path,
        ),
    )
    return Response(
        content=gtm_js_content,
        media_type=gtm_js.headers["Content-Type"],
        headers={"X-Server": "gtm-proxy"} if config.data.Common.server_header else {},
    )


@app.get(config.data.Common.custom_gtag_js_path)
async def get_gtag_js(id: str, request: Request) -> Response:
    headers_to_exclude = {
        config.data.Common.real_ip_header.lower(),
        "x-forwarded-for",
        "x-real-ip",
        "x-forwarded-proto",
        "host",
        "content-length",  # 通常需要移除
        "transfer-encoding",  # 通常需要移除
    }
    headers = {
        k: v for k, v in request.headers.items() if k.lower() not in headers_to_exclude
    }
    query_params = dict(request.query_params)
    try:
        query_params["id"] = str(base64.b64decode(query_params["id"]), "utf-8")
    except:
        pass
    gtag_js = await client.get(
        "https://www.googletagmanager.com/gtag/js",
        params=query_params,
        headers=headers,
    )
    gtag_js_content = replace(
        gtag_js.text,
        (
            '"+a+".google-analytics.com/g/collect',
            '"+(a?a+".":"")+"analytics.google.com/g/collect',
        ),
        (
            config.data.Common.custom_host
            + config.data.Common.custom_analytics_collect_path
            if config.data.Common.use_host is False
            else request.headers["Host"]
            + config.data.Common.custom_analytics_collect_path,
            config.data.Common.custom_host
            + config.data.Common.custom_analytics_collect_path
            if config.data.Common.use_host is False
            else request.headers["Host"]
            + config.data.Common.custom_analytics_collect_path,
        ),
    )
    return Response(
        content=gtag_js_content,
        media_type=gtag_js.headers["Content-Type"],
        headers={"X-Server": "gtm-proxy"} if config.data.Common.server_header else {},
    )


@app.post(config.data.Common.custom_analytics_collect_path)
async def send_collect_request(
    request: Request,
    background_tasks: BackgroundTasks,
):
    base_params = dict(request.query_params)

    params = {
        **base_params,
        "uip": request.headers[config.data.Common.real_ip_header.lower()],
        "_uip": request.headers[config.data.Common.real_ip_header.lower()],
    }
    headers_to_exclude = {
        config.data.Common.real_ip_header.lower(),
        "x-forwarded-for",
        "x-real-ip",
        "x-forwarded-proto",
        "host",
        "content-length",  # 通常需要移除
        "transfer-encoding",  # 通常需要移除
    }
    headers = {
        k: v for k, v in request.headers.items() if k.lower() not in headers_to_exclude
    }
    background_tasks.add_task(
        client.post,
        url="https://www.google-analytics.com/g/collect",
        params=params,
        headers=headers,
    )
    return Response(status_code=HTTP_204_NO_CONTENT)


@app.get(config.data.Common.custom_gtag_destination_path)
async def send_destination_request(
    request: Request,
    background_tasks: BackgroundTasks,
):
    headers_to_exclude = {
        config.data.Common.real_ip_header.lower(),
        "x-forwarded-for",
        "x-real-ip",
        "x-forwarded-proto",
        "host",
        "content-length",  # 通常需要移除
        "transfer-encoding",  # 通常需要移除
    }
    headers = {
        k: v for k, v in request.headers.items() if k.lower() not in headers_to_exclude
    }
    background_tasks.add_task(
        client.get,
        url="https://www.googletagmanager.com/gtag/destination",
        params=request.query_params,
        headers=headers,
    )
    return Response(status_code=HTTP_200_OK)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": int(round(time.time() * 1000))}


@app.get("/")
async def root():
    return Response(content="Welcome to gtm-proxy.")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.data.Server.host,
        port=config.data.Server.port,
        workers=config.data.Server.workers,
        server_header=False,
        proxy_headers=True,
        forwarded_allow_ips="*",
        reload=config.data.Server.reload,
    )
