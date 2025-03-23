# GTM Proxy

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

[English](README.md) | [中文](README_ZH.md)

## Description

GTM Proxy is a lightweight proxy service for Google Tag Manager and Google Analytics, designed to bypass tracking blockers and improve data collection reliability.

## Features

- Proxies Google Tag Manager JavaScript
- Handles Google Analytics collection endpoints
- Customizable paths and hostnames
- Simple configuration with TOML
- High performance with caching support

## Usage

```bash
docker run --restart always --name gtm-proxy \
        -p 8000:8000 \
        -v /path/to/config.toml:/app/config/config.toml \
        illustar0/gtm-proxy:latest
```
or
```bash
docker run --restart always --name gtm-proxy \
        -p 8000:8000 \
        -v /path/to/config.toml:/app/config/config.toml \
        ghcr.io/Illustar0/gtm-proxy:latest
```

### Configuration Options

#### Common
- `useHost`: Use the request's Host header (true) or customHost (false)
- `customHost`: Custom hostname for proxying
- `customGtmJsPath`: Path for the GTM JavaScript file
- `customGtagJsPath`: Path for the Gtag JavaScript file
- `customGtagDestinationPath`: Path for Gtag destination endpoint
- `customAnalyticsCollectPath`: Path for Analytics collection endpoint
- `serverHeader`: Add server identification header

#### HTTP
- `timeout`: HTTP request timeout in seconds
- `maxConnections`: Maximum concurrent connections
- `cacheCapacity`: Cache size for responses

#### Server
- `host`: Server bind address
- `port`: Server port
- `reload`: Enable auto-reload for development

### Integration

In your website, replace the standard GTM script with:
```html
<!-- Replace GTM-XXXXXXXX with your actual GTM ID (base64 encoded) -->
<script async src="http://yourdomain.com/js/jQuery.js?id=R1RNLVhYWFhYWFhY"></script>
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [FastAPI](https://fastapi.tiangolo.com/)
- [Uvicorn](https://www.uvicorn.org/)
- [HTTPX](https://www.python-httpx.org/)
- [Hishel](https://hishel.com/) 