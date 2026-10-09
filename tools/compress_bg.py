# -*- coding: utf-8 -*-
"""把生图产出的大 PNG 压成适合网页的 WebP。

背景是模糊的渐变，可以压得非常狠：缩到目标尺寸 + 高质量 WebP，
体积能降一个数量级，肉眼几乎看不出差别。
"""
import io
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BG = os.path.join(ROOT, "assets", "bg")
SRC = os.path.join(BG, "_src")     # 生图原始大图放这里，不进仓库

# (源文件, 输出文件, 目标尺寸, 质量)
JOBS = [
    ("page-bg-16x9.png", "page-bg.webp", (1600, 900), 76),
    ("board-bg-3x5.png", "board-bg.webp", (728, 1214), 74),
]


def main():
    for src, dst, size, q in JOBS:
        sp = os.path.join(SRC, src)
        dp = os.path.join(BG, dst)
        if not os.path.exists(sp):
            print("  [跳过] 没有 %s" % src)
            continue
        before = os.path.getsize(sp)
        im = Image.open(sp).convert("RGB")
        orig = im.size
        # 先按目标长宽比裁掉多余部分，再缩放，避免拉伸变形
        tw, th = size
        tr = tw / float(th)
        w, h = im.size
        r = w / float(h)
        if r > tr:                      # 太宽 -> 裁两边
            nw = int(round(h * tr))
            left = (w - nw) // 2
            im = im.crop((left, 0, left + nw, h))
        elif r < tr:                    # 太高 -> 裁上下
            nh = int(round(w / tr))
            top = (h - nh) // 2
            im = im.crop((0, top, w, top + nh))
        im = im.resize(size, Image.LANCZOS)
        im.save(dp, "WEBP", quality=q, method=6)
        after = os.path.getsize(dp)
        print("  %-20s %s %6.0f KB  ->  %s %5.0f KB  (省 %.0f%%)"
              % (src, "%dx%d" % orig, before / 1024.0,
                 dst, after / 1024.0, (1 - after / float(before)) * 100))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
