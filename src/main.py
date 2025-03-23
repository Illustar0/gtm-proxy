import base64
import os
import uvicorn
import tomllib
from typing import Tuple
from cachetools import FIFOCache, cached
from fastapi import FastAPI
from hishel import AsyncCacheClient, AsyncInMemoryStorage
from httpx import Limits
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
try:
    with open(CONFIG_PATH, "rb") as f:
        config = tomllib.load(f)
# 配置不存在就使用默认配置
except FileNotFoundError:
    config = {}

common_config = config.get("common", {})
http_config = config.get("http", {})
server_config = config.get("server", {})

# Common 配置
USE_HOST = common_config.get("useHost", True)
CUSTOM_HOST = common_config.get("customHost", "")
CUSTOM_GTM_JS_PATH = common_config.get("customGtmJsPath", "/js/jQuery.js")
CUSTOM_GTAG_JS_PATH = common_config.get(
    "customGtagJsPath", "/js/bootstrap.bundle.min.js"
)
CUSTOM_GTAG_DESTINATION_PATH = common_config.get(
    "customGtagDestinationPath", "/admin/dest"
)
CUSTOM_ANALYTICS_COLLECT_PATH = common_config.get(
    "customAnalyticsCollectPath", "/admin/login"
)
SERVER_HEADER = common_config.get("serverHeader", True)

# HTTP 配置
HTTP_TIMEOUT = http_config.get("timeout", 10.0)
MAX_CONNECTIONS = http_config.get("maxConnections", 1000)
CACHE_CAPACITY = http_config.get("cacheCapacity", 64)

# Server 配置
SERVER_HOST = server_config.get("host", "0.0.0.0")
SERVER_PORT = server_config.get("port", 8000)
SERVER_RELOAD = server_config.get("reload", True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,  # noqa
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = AsyncCacheClient(
    limits=Limits(max_connections=MAX_CONNECTIONS),
    storage=AsyncInMemoryStorage(capacity=CACHE_CAPACITY),
    timeout=HTTP_TIMEOUT,
)


# 优化缓存函数
@cached(cache=FIFOCache(maxsize=CACHE_CAPACITY))
def replace(data: str, old: Tuple, new: Tuple) -> str:
    """
    替换字符串中的内容，使用缓存提高性能
    """
    for i in range(len(old)):
        data = data.replace(old[i], new[i])
    return data


@app.get(CUSTOM_GTM_JS_PATH)
async def get_gtm_js(id: str, request: Request) -> Response:
    headers = dict(request.headers).pop("X-Forwarded-For".lower(), None)
    gtm_js = await client.get(
        f"https://www.googletagmanager.com/gtm.js?id={str(base64.b64decode(id), 'utf-8')}",
        params=request.query_params,
        headers=headers,
    )
    gtm_js_content = replace(
        gtm_js.text,
        ("www.googletagmanager.com", "/gtag/js", "/gtag/destination"),
        (
            CUSTOM_HOST if USE_HOST is False else request.headers["Host"],
            CUSTOM_GTAG_JS_PATH,
            CUSTOM_GTAG_DESTINATION_PATH,
        ),
    )
    return Response(
        content=gtm_js_content,
        media_type=gtm_js.headers["Content-Type"],
        headers={"X-Server": "gtm-proxy"} if SERVER_HEADER else {},
    )


@app.get(CUSTOM_GTAG_JS_PATH)
async def get_gtag_js(id: str, request: Request) -> Response:
    headers = dict(request.headers).pop("X-Forwarded-For".lower(), None)
    gtag_js = await client.get(
        f"https://www.googletagmanager.com/gtag/js?id={str(base64.b64decode(id), 'utf-8')}",
        params=request.query_params,
        headers=headers,
    )
    gtag_js_content = replace(
        gtag_js.text,
        (
            '"+a+".google-analytics.com/g/collect',
            '"+(a?a+".":"")+"analytics.google.com/g/collect',
        ),
        (
            CUSTOM_HOST + CUSTOM_ANALYTICS_COLLECT_PATH
            if USE_HOST is False
            else request.headers["Host"] + CUSTOM_ANALYTICS_COLLECT_PATH,
            CUSTOM_HOST + CUSTOM_ANALYTICS_COLLECT_PATH
            if USE_HOST is False
            else request.headers["Host"] + CUSTOM_ANALYTICS_COLLECT_PATH,
        ),
    )
    return Response(
        content=gtag_js_content,
        media_type=gtag_js.headers["Content-Type"],
        headers={"X-Server": "gtm-proxy"} if SERVER_HEADER else {},
    )


@app.post(CUSTOM_ANALYTICS_COLLECT_PATH)
async def get_collect_content(
    request: Request,
    background_tasks: BackgroundTasks,
):
    base_params = dict(request.query_params)

    params = {
        **base_params,
        "uip": request.client.host,
        "_uip": request.client.host,
    }
    headers = dict(request.headers).pop("X-Forwarded-For".lower(), None)
    background_tasks.add_task(
        client.post,
        url="https://www.google-analytics.com/g/collect",
        params=params,
        headers=headers,
    )
    return Response(status_code=HTTP_204_NO_CONTENT)


@app.get(CUSTOM_GTAG_DESTINATION_PATH)
async def get_collect_content(
    request: Request,
    background_tasks: BackgroundTasks,
):
    headers = dict(request.headers).pop("X-Forwarded-For".lower(), None)
    background_tasks.add_task(
        client.get,
        url="https://www.googletagmanager.com/gtag/destination",
        params=request.query_params,
        headers=headers,
    )
    return Response(status_code=HTTP_200_OK)


@app.get("/")
async def root():
    return Response(content="Welcome to gtm-proxy.")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        server_header=False,
        proxy_headers=True,
        forwarded_allow_ips="*",
        reload=SERVER_RELOAD,
    )
