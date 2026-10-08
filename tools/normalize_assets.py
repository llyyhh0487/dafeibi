# -*- coding: utf-8 -*-
"""
合成大菲比 · 贴图归一化
========================
把任意来源的图（白底 JPG / 灰底 PNG / 带透明通道 PNG）统一处理成 game.js 需要的形式：

  1. 去背景  —— 透明通道图直接阈值；不透明图从四周边界做连通域 flood fill（保护主体内部的白色块）
  2. 去碎屑  —— 只保留主体连通域（丢掉水印、「豆包AI生成」等游离小碎块）
  3. 去水印  —— 底部带状区域内「比局部中位数亮且低饱和」的细笔画（抖音号那类半透明白字）
  4. 归一化  —— 按 alpha 轮廓紧裁 → 等比放到「主体占画布长边 fill 比例」→ 居中贴进正方形画布

输出：assets/fruits/*.webp（RGBA），以及 tools/asset_report.json（含主色，供更新 game.js 用）

依赖：numpy + Pillow（本机已有）
用法：python tools/normalize_assets.py
"""
import base64
import io
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "tmp")
OUT_DIR = os.path.join(ROOT, "assets", "fruits")
MANIFEST = os.path.join(HERE, "asset_manifest.json")

WORK_MAX = 900  # 掩膜计算的工作边长上限（最终画布 <=512，够用且快）


# ---------------------------------------------------------------- 基础工具
def _dilate(m):
    """4 邻域膨胀一格。"""
    n = m.copy()
    n[1:, :] |= m[:-1, :]
    n[:-1, :] |= m[1:, :]
    n[:, 1:] |= m[:, :-1]
    n[:, :-1] |= m[:, 1:]
    return n


def _flood_geodesic(seed, allowed):
    """在 allowed 内做测地膨胀：返回从 seed 能连通的全部像素。"""
    cur = seed & allowed
    while True:
        nxt = _dilate(cur) & allowed
        if np.array_equal(nxt, cur):
            return cur
        cur = nxt


def _components(mask):
    """连通域拆分（少量连通域时够快）。返回按面积降序的列表。"""
    remaining = mask.copy()
    comps = []
    while remaining.any():
        flat = int(np.argmax(remaining))          # 行优先第一个 True
        seed = np.zeros_like(remaining)
        seed.flat[flat] = True
        comp = _flood_geodesic(seed, remaining)
        comps.append(comp)
        remaining &= ~comp
    comps.sort(key=lambda c: -int(c.sum()))
    return comps


def _keep_main(mask, keep_ratio=0.03):
    """只保留主连通域 + 占比 >= keep_ratio 的次连通域，丢掉水印之类的碎块。"""
    comps = _components(mask)
    if not comps:
        return mask
    biggest = int(comps[0].sum())
    kept = np.zeros_like(mask)
    for c in comps:
        if c.sum() >= biggest * keep_ratio:
            kept |= c
    return kept


# ---------------------------------------------------------------- 去背景
def _dilate_n(m, n):
    for _ in range(n):
        m = _dilate(m)
    return m


def _fill_holes(mask):
    """把被 mask 完全包住、且不接触画面边界的区域并进 mask（补眼睛/头发缝等内部暗部）。"""
    out = mask.copy()
    for c in _components(~mask):
        if c[0, :].any() or c[-1, :].any() or c[:, 0].any() or c[:, -1].any():
            continue                      # 触边 = 外部背景，不是洞
        out |= c
    return out


def _border_background(a, tol=24, edges="LTRB"):
    """以四边颜色聚类为背景色，从边界做测地 flood fill。返回 outside（背景）掩膜。

    edges 控制从哪几条边取种子。主体被某条边切断、且切断处与底色同色时
    （典型：白帽子顶到画面顶边），把那条边排除掉就能避免白底顺切口漏进主体。
    """
    h, w, _ = a.shape
    seed = np.zeros((h, w), bool)
    if "T" in edges:
        seed[0, :] = True
    if "B" in edges:
        seed[-1, :] = True
    if "L" in edges:
        seed[:, 0] = True
    if "R" in edges:
        seed[:, -1] = True
    if not seed.any():
        seed[0, :] = seed[-1, :] = True
        seed[:, 0] = seed[:, -1] = True

    border = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]], axis=0)
    quant = (border // 24) * 24
    keys, counts = np.unique(quant, axis=0, return_counts=True)

    bgcand = np.zeros((h, w), bool)
    for key, cnt in zip(keys, counts):
        if cnt < max(4, 0.03 * len(border)):
            continue
        center = np.median(border[(quant == key).all(axis=1)], axis=0)
        bgcand |= np.abs(a - center).max(axis=2) <= tol

    outside = _flood_geodesic(seed, bgcand)
    if outside.mean() < 0.12:             # 聚类没抓到背景 → 换「亮且低饱和」
        lum = a.mean(axis=2)
        sat = a.max(axis=2) - a.min(axis=2)
        outside = _flood_geodesic(seed, (lum > 195) & (sat < 45))
    return outside


def _center_foreground(a, dark_thr=130):
    """从画面中心出发、穿过「非暗像素」求连通域 —— 贴纸有深色描边，
    因此即使主体被画面边缘切断，这个连通域也会被描边挡住，不会漏进背景。
    返回 (mask, ok)。"""
    lum = a.mean(axis=2)
    dark = lum < dark_thr
    free = ~dark
    h, w = lum.shape

    cy, cx = h // 2, w // 2
    seed = np.zeros((h, w), bool)
    seed[max(0, cy - 4):cy + 5, max(0, cx - 4):cx + 5] = True
    seed &= free
    if not seed.any():
        return None, False

    flood = _flood_geodesic(seed, free)
    if flood.mean() < 0.06 or flood.mean() > 0.94:
        return None, False                # 太碎 / 漏出去了
    subj = flood | (dark & _dilate_n(flood, 4))   # 把描边本身并进来
    return _fill_holes(subj), True


def _subject_mask_from_rgb(rgb, tol=24, mode="auto", edges="LTRB"):
    """不透明图去背景。

    背景可能是多峰的（外面一圈白边 + 里面一张浅灰圆角卡片）。
    mode:
      auto   —— 自动判断（默认）
      border —— 从画面四边 flood fill 取补集
      center —— 从中心穿过「非暗像素」求连通域（贴纸靠深色描边封口，
                因此主体即使被画面边缘切断也不会漏进背景）

    自动判断逻辑：边界法算出来的主体如果不含画面中心、或面积过小，
    说明白底顺着被切断的头发/帽子漏进去了，这时改用中心法。
    """
    a = rgb.astype(np.int16)
    h, w, _ = a.shape

    if mode == "border":
        return _fill_holes(~_border_background(a, tol, edges)), "border"
    if mode == "center":
        m, ok = _center_foreground(a)
        return (m, "center") if ok else (_fill_holes(~_border_background(a, tol, edges)), "border")
    if mode == "union":
        # 边界法的身体是对的，但脸可能被漏进去的白底吃掉；
        # 中心法的头部是对的、身体是缺的。两者取并集正好互补。
        bm = _fill_holes(~_border_background(a, tol, edges))
        cm, ok = _center_foreground(a)
        return (_fill_holes(cm | bm), "union") if ok else (bm, "border")

    border_mask = _fill_holes(~_border_background(a, tol, edges))

    cy, cx = h // 2, w // 2
    patch = border_mask[max(0, cy - 6):cy + 7, max(0, cx - 6):cx + 7]
    centered = patch.mean() > 0.5 if patch.size else False
    plausible = 0.25 <= border_mask.mean() <= 0.90

    if centered and plausible:
        return border_mask, "border"

    center_mask, ok = _center_foreground(a)
    if ok:
        return center_mask, "center"
    return border_mask, "border"

# ---------------------------------------------------------------- 去水印
def _remove_watermark(rgb, band=0.16, med=9, lum_thr=13, sat_thr=48):
    """抖音号那类水印：底部带状区里「局部中位数之上、低饱和」的细亮笔画。
    均匀区域（白衣服）的中位数 ≈ 自身，diff≈0，因此不会被误伤；
    黄色星星等高饱和元素被 sat_thr 排除。只替换命中像素，其余原样保留。"""
    h, w, _ = rgb.shape
    y0 = int(h * (1.0 - band))
    sub = rgb[y0:]
    median = np.asarray(
        Image.fromarray(sub).filter(ImageFilter.MedianFilter(size=med))
    ).astype(np.float32)
    cur = sub.astype(np.float32)

    diff = (cur - median).mean(axis=2)
    sat = cur.max(axis=2) - cur.min(axis=2)
    m = (diff > lum_thr) & (sat < sat_thr)
    if not m.any():
        return rgb, 0

    m = _dilate(_dilate(m))                       # 连上笔画外圈
    out = rgb.copy()
    out[y0:][m] = median[m].astype(np.uint8)      # 只回填命中像素
    return out, int(m.sum())


# ---------------------------------------------------------------- 主体流程
def process(entry, fill):
    src_path = os.path.join(SRC_DIR, entry["src"])
    im = Image.open(src_path)
    long_side = max(im.size)
    if long_side > WORK_MAX:
        k = WORK_MAX / long_side
        im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))),
                       Image.LANCZOS)

    rgba = im.convert("RGBA")
    arr = np.asarray(rgba)
    rgb = arr[:, :, :3].copy()
    alpha = arr[:, :, 3]

    # 1) 先去水印。必须排在算掩膜之前 —— 水印那种浅灰笔画会被当成
    #    「背景色」参与边界聚类，进而把主体里同色区域（皮肤/白衣服）一起吃掉。
    wm_px = 0
    if entry.get("wm"):
        rgb, wm_px = _remove_watermark(rgb)

    # 2) 掩膜：原本就带真透明的走 alpha，否则走边界/中心法
    if alpha.min() < 200 and (alpha < 128).mean() > 0.02:
        mask = alpha > 128
        mode = "alpha"
    else:
        mask, mode = _subject_mask_from_rgb(
            rgb, mode=entry.get("mode", "auto"), edges=entry.get("edges", "LTRB"))

    # 3) 去碎屑（游离小图块）
    before = int(mask.sum())
    mask = _keep_main(mask)
    dropped = before - int(mask.sum())

    # 4) alpha 羽化 + 轻微收缩，避免亮背景残留一圈白边
    a = (mask.astype(np.uint8) * 255)
    a = np.asarray(
        Image.fromarray(a).filter(ImageFilter.MinFilter(3)).filter(
            ImageFilter.GaussianBlur(0.7))
    ).astype(np.float32)
    a = np.clip((a - 26.0) * (255.0 / 205.0), 0, 255).astype(np.uint8)

    cut = np.dstack([rgb, a])
    img = Image.fromarray(cut, "RGBA")

    # 5) 按 alpha 轮廓紧裁 → 等比缩放到 fill*canvas → 居中贴进正方形画布
    bb = img.getchannel("A").getbbox()
    if bb:
        img = img.crop(bb)
    canvas = int(entry["canvas"])
    target = fill * canvas
    k = target / max(img.size)
    nw, nh = max(1, round(img.width * k)), max(1, round(img.height * k))
    # 分两步缩放，缩小比过大时更干净
    if max(img.size) / max(nw, nh) > 2.0:
        mid = (round(img.width * k * 1.6), round(img.height * k * 1.6))
        img = img.resize(mid, Image.LANCZOS)
    img = img.resize((nw, nh), Image.LANCZOS)

    canvas_img = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    canvas_img.paste(img, ((canvas - nw) // 2, (canvas - nh) // 2), img)

    out_path = os.path.join(OUT_DIR, entry["out"])
    canvas_img.save(out_path, "WEBP", quality=90, method=6)

    # 6) 主色（给 game.js 的 c1/c2/pc1/pc2/line 用）
    ca = np.asarray(canvas_img)
    op = ca[:, :, 3] > 200
    px = ca[:, :, :3][op].astype(float) if op.any() else np.zeros((0, 3))
    if px.size:
        lum = px.mean(axis=1)
        mean = px.mean(axis=0).astype(int)
        hi = px[lum >= np.percentile(lum, 78)].mean(axis=0).astype(int)
        lo = px[lum <= np.percentile(lum, 22)].mean(axis=0).astype(int)
    else:
        mean = hi = lo = np.array([200, 200, 200])
    return {
        "tier": entry["tier"],
        "name": entry["name"],
        "out": entry["out"],
        "canvas": canvas,
        "mode": mode,
        "dropped_px": dropped,
        "wm_px": wm_px,
        "subject": img.size,
        "bytes": os.path.getsize(out_path),
        "mean": [int(v) for v in mean],
        "hi": [int(v) for v in hi],
        "lo": [int(v) for v in lo],
    }


def main():
    with open(MANIFEST, encoding="utf-8") as f:
        man = json.load(f)
    fill = man["fill"]
    os.makedirs(OUT_DIR, exist_ok=True)

    report = []
    for e in sorted(man["entries"], key=lambda x: x["tier"]):
        r = process(e, fill)
        report.append(r)
        print(f'  tier{r["tier"]:>2} {r["out"]:<18} canvas={r["canvas"]:<4} '
              f'subject={str(r["subject"]):<11} {r["bytes"]/1024:6.1f}KB  '
              f'bg={r["mode"]:<5} wm={r["wm_px"]:>6}  mean={r["mean"]}')

    total = sum(r["bytes"] for r in report)
    print(f'\n  合计 {total/1024:.1f} KB / 12 张')
    with open(os.path.join(HERE, "asset_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("  报告 -> tools/asset_report.json")


if __name__ == "__main__":
    sys.exit(main())
