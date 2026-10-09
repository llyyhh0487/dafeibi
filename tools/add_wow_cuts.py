# -*- coding: utf-8 -*-
"""把「哇！菲比」的打点结果并进 tools/sfx-cuts-final.json。

jubi / bibi 的既有结果原样保留，只新增 wow。
段表由上游（浏览器里算的能量谷底精修）给出，这里直接固化。
"""
import io
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "sfx-cuts-final.json")

DURATION = 36.455

# 上游精修后的 35 句（切点已吸到能量谷底，去掉了末尾 0.015s 碎段）
SEGMENTS = [
    [0, 0.39], [0.39, 1.63], [1.63, 2.51], [2.51, 3.96], [3.96, 5.17],
    [5.17, 6.27], [6.27, 7.52], [7.52, 7.95], [7.95, 8.6], [8.6, 9.31],
    [9.31, 10.27], [10.27, 11.16], [11.16, 12.12], [12.12, 14.24],
    [14.24, 15.67], [15.67, 17.37], [17.37, 17.83], [17.83, 18.65],
    [18.65, 19.59], [19.59, 20.89], [20.89, 21.49], [21.49, 22.66],
    [22.66, 23.99], [23.99, 24.68], [24.68, 25.74], [25.74, 26.92],
    [26.92, 27.88], [27.88, 28.77], [28.77, 29.65], [29.65, 30.91],
    [30.91, 31.94], [31.94, 33.24], [33.24, 34.26], [34.26, 34.95],
    [34.95, 36.455],
]


def main():
    with io.open(SRC, encoding="utf-8") as f:
        d = json.load(f)

    if "wow" in d:
        print("  wow 已存在，先备份再覆盖")
    shutil.copyfile(SRC, SRC + ".bak")

    d["wow"] = {
        "file": "哇！菲比（番外）_音频.mp4",
        "duration": DURATION,
        "marks": [s[0] for s in SEGMENTS[1:]],
        "segments": SEGMENTS,
    }

    with io.open(SRC, "w", encoding="utf-8", newline="\n") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)

    for k in ("jubi", "bibi", "wow"):
        v = d.get(k)
        if not v:
            continue
        segs = v["segments"]
        lens = sorted(b - a for a, b in segs)
        print("  %-5s %2d 句  中位 %.2fs  最短 %.2fs  最长 %.2fs"
              % (k, len(segs), lens[len(lens) // 2], lens[0], lens[-1]))
    print("  -> %s" % SRC)
    os.remove(SRC + ".bak")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
