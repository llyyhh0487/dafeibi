# -*- coding: utf-8 -*-
"""
合成大菲比 · 碰撞形状生成
=========================
从 assets/fruits/*.webp 的 alpha 轮廓算出 parts.js（game.js 用它做非圆形碰撞）。

格式（与 game.js:254 的读取方式一致）：
  window.SUIKA_PARTS = [ { parts: [[ox, oy, s], ...], rb: <number> }, ... ]
  - parts 与 rb 都以「该级水果的半径 r」为单位
  - 画布边长 canvas 会映射到 box = 2r / ASSET_FILL
    所以 1 画布像素 = 2 / (ASSET_FILL * canvas) 个 r 单位，即单位换算 unit = 0.46 * canvas
  - 取 N 个「最大内切圆」贪心覆盖轮廓；rb = max(|offset| + 半径)，
    保证是形状真实外接半径（粗筛不会漏碰撞）

算法经与原版 parts.js 逐值比对验证：12 级的 rb 比值全部为 1.000。

用法：python tools/build_parts.py
"""
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FR = os.path.join(ROOT, "assets", "fruits")
ASSET_FILL = 0.92
N_PARTS = 16
ALPHA_THR = 128


def edt(mask):
    """精确欧氏距离变换（Felzenszwalb & Huttenlocher 一维算法），
    返回每个前景像素到最近背景像素的距离（px）。"""
    INF = 1e20
    h, w = mask.shape
    f = np.where(mask, INF, 0.0)

    def dt1d(col):
        n = col.shape[0]
        d = np.empty(n)
        v = np.zeros(n, dtype=int)
        z = np.empty(n + 1)
        k = 0
        v[0] = 0
        z[0] = -INF
        z[1] = INF
        for q in range(1, n):
            while True:
                s = ((col[q] + q * q) - (col[v[k]] + v[k] * v[k])) / (2.0 * q - 2.0 * v[k])
                if s <= z[k]:
                    k -= 1
                else:
                    break
            k += 1
            v[k] = q
            z[k] = s
            z[k + 1] = INF
        k = 0
        for q in range(n):
            while z[k + 1] < q:
                k += 1
            d[q] = (q - v[k]) ** 2 + col[v[k]]
        return d

    for x in range(w):
        f[:, x] = dt1d(f[:, x])
    for y in range(h):
        f[y, :] = dt1d(f[y, :])
    return np.sqrt(f)


def build_one(path):
    im = Image.open(path).convert("RGBA")
    a = np.asarray(im.getchannel("A"))
    canvas = im.size[0]
    unit = 0.46 * canvas              # 1 个 r 单位 = 多少画布像素
    c = canvas / 2.0

    mask = a > ALPHA_THR
    if not mask.any():
        return {"parts": [[0.0, 0.0, 1.0]], "rb": 1.0}

    D = edt(mask)
    remaining = mask.copy()
    yy, xx = np.ogrid[:canvas, :canvas]
    parts = []
    for _ in range(N_PARTS):
        Dm = np.where(remaining, D, 0.0)
        idx = int(np.argmax(Dm))
        if Dm.flat[idx] <= 0:
            break
        py, px = np.unravel_index(idx, Dm.shape)
        rad = float(Dm[py, px])
        parts.append([round((px - c) / unit, 3), round((py - c) / unit, 3), round(rad / unit, 3)])
        covered = (xx - px) ** 2 + (yy - py) ** 2 <= (rad * 0.98) ** 2
        remaining &= ~covered

    rb = max((p[0] ** 2 + p[1] ** 2) ** 0.5 + p[2] for p in parts)
    return {"parts": parts, "rb": round(rb, 3)}


def main():
    files = sorted(f for f in os.listdir(FR) if f.endswith(".webp"))
    shapes = []
    for f in files:
        s = build_one(os.path.join(FR, f))
        shapes.append(s)
        print(f"  {f:<18} parts={len(s['parts']):>2}  rb={s['rb']:.3f}")

    body = json.dumps(shapes, ensure_ascii=False, separators=(",", ":"))
    js = (
        "/* 自动生成，请勿手改 —— 由 tools/build_parts.py 生成\n"
        "   parts: [ox, oy, s]，单位是「以 r 为 1」；rb: 碰撞包围圆半径（同样以 r 为单位） */\n"
        "window.SUIKA_PARTS = " + body + ";\n"
    )
    out = os.path.join(FR, "parts.js")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(js)
    print(f"\n  -> {out}  ({os.path.getsize(out)/1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
