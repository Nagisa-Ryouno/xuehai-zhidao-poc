# -*- coding: utf-8 -*-
"""
scripts/serve_dist.py
学海智导 · 一键本地体验服务器

用途：
  1. 启动后端网关（uvicorn, 127.0.0.1:8011）
  2. 以 8080 端口托管 frontend/dist（PWA 生产构建），并把 /api 请求代理到 8011
  3. 自动打开浏览器

使用：
  pip install -r requirements.txt
  npm --prefix frontend run build        # 若 frontend/dist 不存在才需要
  python scripts/serve_dist.py
"""
from __future__ import annotations

import http.server
import socketserver
import subprocess
import sys
import threading
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "frontend" / "dist"
API_PORT = 8011
WEB_PORT = 8080


def start_backend() -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "gateway.api:app",
         "--host", "127.0.0.1", "--port", str(API_PORT)],
        cwd=ROOT,
    )


def is_alive(url: str, timeout: float = 1.5) -> bool:
    """服务是否已在运行（避免重复启动时静默崩溃）"""
    try:
        with urllib.request.urlopen(url, timeout=timeout):
            return True
    except Exception:
        return False


class DistHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIST), **kwargs)

    def log_message(self, *args):  # 静音请求日志
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
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)
        except Exception as exc:  # 后端未启动时给出可读错误
            body = f'{{"error": "backend unreachable: {exc}"}}'.encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

    # SPA 路由回退：非文件路径交给 index.html
    def send_head(self):
        if not self.path.startswith("/api/") and "." not in Path(self.path).name:
            self.path = "/index.html"
        return super().send_head()


def main() -> None:
    if not DIST.exists():
        print("frontend/dist 不存在，请先执行：npm --prefix frontend install && npm --prefix frontend run build")
        sys.exit(1)

    # 已在运行：直接打开浏览器，双击多少次都不会报错
    if is_alive(f"http://127.0.0.1:{WEB_PORT}/"):
        print(f"学海智导已在运行: http://127.0.0.1:{WEB_PORT} ，正在打开浏览器…")
        webbrowser.open(f"http://127.0.0.1:{WEB_PORT}")
        return

    # 后端已在运行（如之前残留）：复用，不重复启动
    backend = None
    if is_alive(f"http://127.0.0.1:{API_PORT}/api/health"):
        print(f"检测到后端已在运行: http://127.0.0.1:{API_PORT}")
    else:
        backend = start_backend()
        print(f"后端网关已启动: http://127.0.0.1:{API_PORT}")
    try:
        with socketserver.ThreadingTCPServer(("127.0.0.1", WEB_PORT), DistHandler) as httpd:
            url = f"http://127.0.0.1:{WEB_PORT}"
            print(f"学海智导已就绪: {url}  (Ctrl+C 停止)")
            threading.Timer(1.0, lambda: webbrowser.open(url)).start()
            httpd.serve_forever()
    finally:
        if backend is not None:
            backend.terminate()


if __name__ == "__main__":
    main()
