# -*- coding: utf-8 -*-
"""部署前自检：确认 html / js 里引用的本地文件都存在。"""
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
missing = []


def check(ref):
    if ref.startswith(("http", "//", "data:", "mailto:", "#")):
        return
    p = os.path.join(ROOT, ref.replace("/", os.sep))
    if not os.path.exists(p):
        missing.append(ref)


# index.html 的 src / href
html = io.open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
for ref in re.findall(r"""(?:src|href)\s*=\s*["']([^"']+)["']""", html):
    check(ref)

# game.js 里的贴图
js = io.open(os.path.join(ROOT, "game.js"), encoding="utf-8").read()
for ref in re.findall(r"""file:\s*'([^']+)'""", js):
    check(ref)

# 语音切句表里的音频
sfx = io.open(os.path.join(ROOT, "assets", "sfx", "phoebe.js"), encoding="utf-8").read()
for ref in re.findall(r'"(assets/sfx/[^"]+)"', sfx):
    check(ref)

# 语音表里每个 seg 是否落在音频时长内（防止切点越界）
import json
m = re.search(r"window\.PHOEBE_VOICE\s*=\s*(\{.*\});", sfx, re.S)
if m:
    data = json.loads(m.group(1))
    for t in data["tracks"]:
        for i, (a, b) in enumerate(t["segs"]):
            if not (0 <= a < b <= t["duration"] + 1e-6):
                missing.append("%s seg#%d 越界: %s" % (t["name"], i, (a, b)))
        print("  %-6s %2d 句  时长 %.3fs   OK" % (t["name"], len(t["segs"]), t["duration"]))

print()
if missing:
    print("  [缺失] 以下引用找不到：")
    for m2 in missing:
        print("    " + m2)
    raise SystemExit(1)
print("  全部就位，可以部署")
