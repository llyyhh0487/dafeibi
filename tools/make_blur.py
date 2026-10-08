# -*- coding: utf-8 -*-
"""
合成大菲比 · 模糊占位图生成
===========================
生成 blur.js：把 12 张贴图各缩到 CELL×CELL，横向拼成一张 sprite sheet，
以 data URL 内联进 JS（零额外请求），WebP 编码后 base64。

game.js:839 的用法：
  drawImage(blurImg, idx * cell, 0, cell, cell, ...)
所以 cell 与 cols 都要写进 blur.js，整张表为 (CELL*12) x CELL。

CELL=24 时整张表约 7 KB，和原版（6.7 KB）基本持平；再小会更糊但更省流量。

用途：贴图还没下载完时先画这张极模糊的占位，观感是「图正在慢慢变清晰」，
而不是「图挂了」。

用法：python tools/make_blur.py
"""
import base64
import io
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FR = os.path.join(ROOT, "assets", "fruits")
CELL = 24
QUALITY = 80


def main():
    files = sorted(f for f in os.listdir(FR) if f.endswith(".webp"))
    cols = len(files)
    sheet = Image.new("RGBA", (CELL * cols, CELL), (0, 0, 0, 0))
    for i, f in enumerate(files):
        im = Image.open(os.path.join(FR, f)).convert("RGBA")
        sheet.paste(im.resize((CELL, CELL), Image.LANCZOS), (i * CELL, 0))

    buf = io.BytesIO()
    sheet.save(buf, "WEBP", quality=QUALITY, method=6)
    raw = buf.getvalue()
    b64 = base64.b64encode(raw).decode("ascii")

    js = (
        "/* 自动生成，别手改 —— 改缩略图请跑 tools/make_blur.py */\n"
        "/* 贴图还没到位时画的极模糊占位（内联 data URL，零额外请求） */\n"
        "window.FRUIT_BLUR = {\n"
        "  src: 'data:image/webp;base64," + b64 + "',\n"
        f"  cell: {CELL},\n"
        f"  cols: {cols}\n"
        "};\n"
    )
    out = os.path.join(FR, "blur.js")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(js)
    print(f"  sheet {sheet.size}  webp {len(raw)/1024:.1f} KB  "
          f"-> {out} ({os.path.getsize(out)/1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
