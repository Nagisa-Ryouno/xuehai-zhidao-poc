# -*- coding: utf-8 -*-
"""
scripts/serve_cloud.py
学海智导 · 云端单进程服务（Render/Fly/自有服务器通用）

在单容器内同时运行：
  1. 后端网关 uvicorn（内部 127.0.0.1:8011）
  2. 前端静态站（0.0.0.0:$PORT，Render 注入 PORT，默认 8080）
     并把 /api 请求代理到内部后端 + SPA 路由回退
浏览器访问同源 /api，无跨域问题；PWA 经云端 HTTPS 正常工作。
"""
from __future__ import annotations

import http.server
import os
import socketserver
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "frontend" / "dist"
API_PORT = 8011
PORT = int(os.environ.get("PORT", "8080"))


def start_backend() -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "gateway.api:app",
         "--host", "127.0.0.1", "--port", str(API_PORT)],
        cwd=ROOT,
    )


class CloudHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIST), **kwargs)

    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path.startswith("/api/"):
            return self._proxy()
        return super().do_GET()

    def _proxy(self):
        url = f"http://127.0.0.1:{API_PORT}{self.path}"
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                body = resp.read()
                self.send_response(resp.status)
                self.send_header("Content-Type", resp.headers.get("Content-Type", "application/json"))
                self.end_headers()
                self.wfile.write(body)
        except Exception as exc:
            body = f'{{"error": "backend unreachable: {exc}"}}'.encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

    def send_head(self):
        if not self.path.startswith("/api/") and "." not in Path(self.path).name:
            self.path = "/index.html"
        return super().send_head()


def wait_backend_ready(timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{API_PORT}/api/health", timeout=2):
                return
        except Exception:
            time.sleep(0.5)


def main() -> None:
    if not DIST.exists():
        print("frontend/dist 不存在（镜像构建阶段应先完成前端构建）", flush=True)
        sys.exit(1)

    backend = start_backend()
    wait_backend_ready()
    print(f"backend ready on 127.0.0.1:{API_PORT}", flush=True)

    try:
        with socketserver.ThreadingTCPServer(("0.0.0.0", PORT), CloudHandler) as httpd:
            print(f"xuehai cloud serving on 0.0.0.0:{PORT}", flush=True)
            httpd.serve_forever()
    finally:
        backend.terminate()


if __name__ == "__main__":
    main()
