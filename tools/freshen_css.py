# -*- coding: utf-8 -*-
"""把 CSS 里残留的暖色（奶油/棕）统一换成冷调蓝白，让整体更「清新」。

只做精确的字符串替换，改完打印命中次数，方便核对。
"""
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CSS = os.path.join(ROOT, "style.css")

# (原串, 新串)
RULES = [
    # 阴影：暖棕 -> 冷蓝灰
    ("rgba(140, 96, 56, .18)", "rgba(96, 128, 176, .18)"),
    ("rgba(140, 96, 56, .14)", "rgba(96, 128, 176, .16)"),
    ("rgba(140, 96, 56, .12)", "rgba(96, 128, 176, .14)"),
    ("rgba(140, 96, 56, .10)", "rgba(96, 128, 176, .12)"),
    ("rgba(140, 96, 56, .09)", "rgba(96, 128, 176, .11)"),
    # 描边
    ("rgba(214, 160, 96, .25)", "rgba(122, 164, 210, .30)"),
    ("rgba(214, 160, 96, .22)", "rgba(122, 164, 210, .26)"),
    ("rgba(214, 160, 96, .45)", "rgba(122, 164, 210, .45)"),
    # 面板底色
    ("rgba(255, 233, 190, .8)", "rgba(228, 241, 253, .82)"),
    ("rgba(255, 243, 224, .85)", "rgba(232, 243, 253, .88)"),
    ("rgba(255, 243, 224, .9)", "rgba(232, 243, 253, .92)"),
    # 棋盘兜底色 / 页面暖光晕
    ("#fff3df", "#eef7fe"),
    ("#ffe9bd", "#d8ecff"),
    # 排行榜第一名的底色
    ("linear-gradient(100deg, #fff6d8, #ffe9a8)",
     "linear-gradient(100deg, #e8f4ff, #d3e8ff)"),
]


def main():
    with io.open(CSS, encoding="utf-8") as f:
        s = f.read()
    total = 0
    for a, b in RULES:
        n = s.count(a)
        if n:
            s = s.replace(a, b)
            total += n
            print("  %-42s -> %-42s  x%d" % (a, b, n))
    with io.open(CSS, "w", encoding="utf-8", newline="\n") as f:
        f.write(s)
    print("  共替换 %d 处" % total)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
