# -*- coding: utf-8 -*-
"""找出 style.css 里已经没人用的 class（HTML/JS 里都不再出现）。

只做检测和报告，不改文件 —— 由人确认后再删，避免误杀 JS 动态生成的类名。
"""
import io
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def read(p):
    with io.open(os.path.join(ROOT, p), encoding="utf-8") as f:
        return f.read()


def main():
    css = read("style.css")
    used_src = read("index.html") + "\n" + read("game.js")

    # 只看 class 选择器（.foo），忽略伪类后面的部分
    classes = set()
    for m in re.finditer(r"\.([A-Za-z][A-Za-z0-9_-]*)", css):
        classes.add(m.group(1))

    dead = []
    for c in sorted(classes):
        # 在 HTML/JS 里以独立词出现才算用到
        if not re.search(r"(?<![A-Za-z0-9_-])" + re.escape(c) + r"(?![A-Za-z0-9_-])", used_src):
            dead.append(c)

    print("  style.css 里共 %d 个 class" % len(classes))
    print("  疑似没人用的 %d 个：" % len(dead))
    for c in dead:
        print("    .%s" % c)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
