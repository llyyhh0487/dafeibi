# -*- coding: utf-8 -*-
"""从生图的按钮素材里裁出「可拉伸的中段」，做成网页用的按钮底图。

思路：
  生成的药丸两头是圆的。如果整张拉伸，圆头会被拉变形；
  如果做 border-image 九宫格，又要多写不少 CSS。
  这里直接取药丸正中间的一条竖带（只有上下渐变、左右均匀），
  拉伸到按钮尺寸，圆角交给 CSS 的 border-radius 处理 —— 最简单也最稳。

背景是纯品红，先按颜色把药丸的包围盒找出来。
"""
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BG = os.path.join(ROOT, "assets", "bg")
SRC = os.path.join(BG, "_src")     # 生图原始大图放这里，不进仓库

JOBS = [
    ("btn-base.png", "btn-face.webp", 96),
    ("btn-primary.png", "btn-face-primary.webp", 96),
]

# 品红背景的判定：只比 R 和 G，避免和药丸的暖色混淆
TOL = 60.0


def find_pill(im):
    a = np.asarray(im.convert("RGB")).astype(np.int16)
    bg = a[2, 2].copy()                       # 取左上角当背景色
    # 只要 G 明显低于背景、且 R 接近或高于背景，就认为是品红背景
    is_bg = (np.abs(a[:, :, 0] - bg[0]) < TOL) & (a[:, :, 1] < bg[1] + 40) & \
            (np.abs(a[:, :, 2] - bg[2]) < TOL)
    fg = ~is_bg
    rows = np.where(fg.any(axis=1))[0]
    cols = np.where(fg.any(axis=0))[0]
    if not len(rows) or not len(cols):
        return None
    return int(cols[0]), int(rows[0]), int(cols[-1]), int(rows[-1])


def main():
    for src, dst, out_h in JOBS:
        sp = os.path.join(SRC, src)
        if not os.path.exists(sp):
            print("  [跳过] 没有 %s" % src)
            continue
        im = Image.open(sp)
        box = find_pill(im)
        if box is None:
            print("  [失败] %s 找不到药丸" % src)
            continue
        l, t, r, b = box
        w = r - l
        h = b - t
        # 上下各内缩 2px，避开和品红混色的边缘
        t2, b2 = t + 2, b - 2
        # 取中间 30% 宽的竖带，完全避开两端的圆头
        x0 = l + int(w * 0.35)
        x1 = l + int(w * 0.65)
        strip = im.crop((x0, t2, x1, b2))
        sw, sh = strip.size
        out_w = max(8, int(round(out_h * sw / float(sh))))
        strip = strip.resize((out_w, out_h), Image.LANCZOS)
        dp = os.path.join(BG, dst)
        strip.convert("RGB").save(dp, "WEBP", quality=88, method=6)
        print("  %-18s 药丸 %dx%d  @(%d,%d)  ->  中段 %dx%d  ->  %s %dx%d %.1f KB"
              % (src, w, h, l, t, sw, sh, dst, out_w, out_h,
                 os.path.getsize(dp) / 1024.0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
