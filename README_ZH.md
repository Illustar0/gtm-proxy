# GTM Proxy

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

[English](README.md) | [中文](README_ZH.md)

## 描述

GTM Proxy是一个轻量级的 Google Tag Manager 和 Google Analytics 代理服务，旨在绕过跟踪拦截器并提高数据收集可靠性。

## 特性

- 代理 Google Tag Manager JavaScript
- 处理 Google Analytics 收集端点
- 可自定义路径和主机名
- 使用 TOML 进行简单配置
- 支持缓存的高性能

## 使用方法

```bash
docker run -d --restart always --name gtm-proxy \
        -p 8000:8000 \
        -v /path/to/config.toml:/app/config/config.toml \
        illustar0/gtm-proxy:latest
```
或
```bash
docker run -d --restart always --name gtm-proxy \
        -p 8000:8000 \
        -v /path/to/config.toml:/app/config/config.toml \
        ghcr.io/illustar0/gtm-proxy:latest
```

### 配置选项

#### 通用
- `useHost`: 使用请求的 Host 头(true)或 customHost(false)
- `customHost`: 代理使用的自定义主机名
- `customGtmJsPath`: GTM JavaScript 文件的路径
- `customGtagJsPath`: Gtag JavaScript 文件的路径
- `customGtagDestinationPath`: Gtag 目标端点的路径
- `customAnalyticsCollectPath`: Analytics 收集端点的路径
- `serverHeader`: 添加服务器标识头

#### HTTP
- `timeout`: HTTP 请求超时（秒）
- `maxConnections`: 最大并发连接数
- `cacheCapacity`: 响应缓存大小

#### 服务器
- `host`: 服务器绑定地址
- `port`: 服务器端口
- `reload`: 启用开发环境自动重载

### 集成

在您的网站中，将标准 GTM 脚本替换为：
```html
<!-- 将 GTM-XXXXXXXX 替换为您实际的 GTM ID（base64 编码）-->
<script async src="http://yourdomain.com/js/jQuery.js?id=R1RNLVhYWFhYWFhY"></script>
```

## 许可证

本项目使用 MIT 许可证 - 有关详细信息，请参阅 LICENSE 文件。

## 致谢

- [FastAPI](https://fastapi.tiangolo.com/)
- [Uvicorn](https://www.uvicorn.org/)
- [HTTPX](https://www.python-httpx.org/)
- [Hishel](https://hishel.com/) 