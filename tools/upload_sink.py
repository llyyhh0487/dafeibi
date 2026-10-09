# -*- coding: utf-8 -*-
"""一个只用来接收浏览器 POST 上传的小服务 —— 把重编码后的音频存到磁盘。

为什么需要它：浏览器里跑完 MediaRecorder 得到的是 Blob，
通过 Playwright 把几百 KB 的 base64 传回来会撑爆上下文，
所以让页面直接 POST 到本机。

用法：python tools/upload_sink.py <保存目录> [端口]
"""
import io
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


class Handler(BaseHTTPRequestHandler):
    out_dir = "."

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        name = (q.get("name") or ["upload.bin"])[0]
        name = os.path.basename(name)                 # 防目录穿越
        n = int(self.headers.get("Content-Length") or 0)
        data = self.rfile.read(n) if n else b""
        path = os.path.join(self.out_dir, name)
        with io.open(path, "wb") as f:
            f.write(data)
        print("  收到 %s  %d 字节" % (name, len(data)), flush=True)
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, fmt, *args):
        pass


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8154
    os.makedirs(out_dir, exist_ok=True)
    Handler.out_dir = out_dir
    print("  监听 127.0.0.1:%d  保存到 %s" % (port, out_dir), flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
