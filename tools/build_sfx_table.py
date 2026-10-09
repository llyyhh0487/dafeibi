# -*- coding: utf-8 -*-
"""把 tools/sfx-cuts-final.json 固化成 assets/sfx/phoebe.js（切句表）。"""
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, "sfx-cuts-final.json")
OUT = os.path.join(ROOT, "assets", "sfx", "phoebe.js")

HEADER = (
    "/* 自动生成，请勿手改 —— 由 tools/make_sfx_marker.py 人工打点 + 自动精修后固化\n"
    "   每个 seg = [起始秒, 结束秒]。播放时用\n"
    "     src.start(0, seg[0], seg[1]-seg[0])\n"
    "   直接从原音频里切出一句，所以不必重新编码：音质无损，而且整段素材只有一个文件。 */\n"
)


def main():
    with io.open(SRC, encoding="utf-8") as f:
        d = json.load(f)

    # key 会写进切句表，游戏用它指定"这一下只用某条音轨"
    # （比如大招只放「哇！菲比」）。json 里还没有的轨道自动跳过。
    # order = 加载优先级：小的、常用的先拉，稀有的大招音轨最后拉，
    # 这样手机上普通合成能尽早出声。
    tracks = []
    for key, label, order in (("bibi", "菲比比", 0),
                              ("jubi", "菲比啾比", 1),
                              ("wow", "哇！菲比", 2)):
        v = d.get(key)
        if not v:
            continue
        tracks.append({
            "key": key,
            "name": label,
            "order": order,
            "file": "assets/sfx/phoebe-%s.mp4" % key,
            "duration": v["duration"],
            "segs": [[round(a, 3), round(b, 3)] for a, b in v["segments"]],
        })

    js = HEADER + "window.PHOEBE_VOICE = " + json.dumps(
        {"tracks": tracks}, ensure_ascii=False, separators=(",", ":")
    ) + ";\n"

    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(js)

    print("  -> %s  (%.1f KB)" % (OUT, os.path.getsize(OUT) / 1024.0))
    for t in tracks:
        print("     %-6s %2d 句  %.3fs" % (t["name"], len(t["segs"]), t["duration"]))
    print("     合计 %d 句" % sum(len(t["segs"]) for t in tracks))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
