# -*- coding: utf-8 -*-
"""删除 style.css 里「整条规则都由死类构成」的规则。

保守策略：
  - 只有当一条规则的**所有** class 都在死类名单里时才删；
  - @media / @supports 递归处理，里面被删空就整块去掉；
  - @keyframes / @font-face 原样保留；
  - 运行前自动备份成 style.css.bak。
"""
import io
import os
import re
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CSS = os.path.join(ROOT, "style.css")

GROUP = ("@media", "@supports", "@layer", "@container")
KEEP_AT = ("@keyframes", "@font-face", "@charset", "@import")

DEAD = {
    "board-empty", "board-list", "board-name", "board-note", "board-rank",
    "board-row", "board-score", "btn-wide", "icon-btn", "is-bad", "is-good",
    "is-mine", "link-btn", "modal", "modal-card", "modal-foot", "modal-head",
    "my-name", "name-input", "nick-input", "nick-label", "nick-row",
    "r1", "r2", "r3", "submit-box", "submit-msg",
}


def classes_of(sel):
    return set(re.findall(r"\.([A-Za-z][A-Za-z0-9_-]*)", sel))


def process(text):
    res = []
    i = 0
    n = len(text)
    while i < n:
        b = text.find("{", i)
        if b < 0:
            res.append(text[i:])
            break
        sel = text[i:b]
        d = 1
        j = b + 1
        while j < n and d:
            if text[j] == "{":
                d += 1
            elif text[j] == "}":
                d -= 1
            j += 1
        body = text[b + 1:j - 1]
        s = sel.strip()
        if s.startswith(GROUP):
            new_body = process(body)
            if new_body.strip():
                res.append(sel + "{" + new_body + "}")
        elif s.startswith(KEEP_AT):
            res.append(sel + "{" + body + "}")
        else:
            cls = classes_of(sel)
            if cls and cls <= DEAD:
                pass                      # 整条都是死类 -> 丢掉
            else:
                res.append(sel + "{" + body + "}")
        i = j
    return "".join(res)


def main():
    with io.open(CSS, encoding="utf-8") as f:
        src = f.read()
    shutil.copyfile(CSS, CSS + ".bak")

    out = process(src)
    out = re.sub(r"\n{3,}", "\n\n", out)        # 收掉多余空行

    with io.open(CSS, "w", encoding="utf-8", newline="\n") as f:
        f.write(out)

    print("  %d 字节 -> %d 字节（省 %.0f%%）"
          % (len(src), len(out), (1 - len(out) / float(len(src))) * 100))
    print("  大括号平衡: %s" % ("OK" if out.count("{") == out.count("}") else "不平衡！"))
    left = sorted(c for c in DEAD if re.search(r"\." + re.escape(c) + r"(?![A-Za-z0-9_-])", out))
    print("  仍残留的死类: %s" % (left if left else "无"))
    print("  备份: style.css.bak")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
