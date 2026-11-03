#!/usr/bin/env python3
# 幫專長取人名：把一項或好幾項專長併進同一個名字
# 用法：取名.py "<名字>" "<專長>" ["<專長>" ...]
#       取名.py --完成    （開張做完，之後更新不再補回預設的 5 項）
import json, os, shutil, sys

RULE = "## 規則（日期｜規則｜原因）"
FLAG = ".已開張"


def split(text):
    """切成：專長內容、規則列"""
    head, _, rules = text.partition(RULE)
    return head.strip(), [l for l in rules.splitlines() if l.strip()]


def section(skill, body):
    """把一份專長規格變成名字底下的一段"""
    out = [f"## 專長：{skill}"]
    for line in body.splitlines():
        if line.startswith("# "):
            continue
        out.append("#" + line if line.startswith("## ") else line)
    return "\n".join(out).strip()


def update_table(path, name, skills):
    """名單表格：拿掉已併進來的專長列，名字那列換成最新的"""
    rows = open(path, encoding="utf-8").read().splitlines()
    cells = lambda l: [c.strip() for c in l.strip().strip("|").split("|")]
    is_row = lambda l: l.startswith("|") and not l.startswith("|---")
    keep, at, old = [], None, []
    for l in rows:
        if is_row(l) and cells(l)[0] != "名字" and cells(l)[0] in skills + [name]:
            if at is None:
                at = len(keep)
            if cells(l)[0] == name:
                old = [s.strip() for s in cells(l)[1].split("、")]
            continue
        keep.append(l)
    if at is None:
        at = max(i for i, l in enumerate(keep) if l.startswith("|")) + 1
    all_skills = old + [s for s in skills if s not in old]
    keep.insert(at, f"| {name} | {'、'.join(all_skills)} | {name}/規格.md |")
    open(path, "w", encoding="utf-8").write("\n".join(keep).rstrip() + "\n")
    return all_skills


def main():
    cfg = json.load(open(os.path.expanduser("~/.claude/角色機設定.json"), encoding="utf-8"))
    base = os.path.join(cfg["root"], "角色")
    args = sys.argv[1:]
    if args == ["--完成"]:
        open(os.path.join(base, FLAG), "w").close()
        print("開張完成")
        return
    if len(args) < 2:
        sys.exit('用法：取名.py "<名字>" "<專長>" ["<專長>" ...]')
    name, skills = args[0], args[1:]
    if any(c in name for c in "/|") or name.startswith((".", "_")):
        sys.exit("名字不能有 / 或 |，也不能用 . 或 _ 開頭")
    target = os.path.join(base, name, "規格.md")
    template = open(os.path.join(base, "_範本", "規格.md"), encoding="utf-8").read()

    # 名字已經有規格就接在後面，不蓋掉長出來的規則
    if os.path.isfile(target) and not (name in skills and len(open(target, encoding="utf-8").read().split("## 專長：")) == 1):
        head, rules = split(open(target, encoding="utf-8").read())
        parts = [head]
    else:
        head, rules = f"# {name}｜規格", []
        parts = [head]

    moved = []
    for skill in skills:
        src = os.path.join(base, skill, "規格.md")
        if f"## 專長：{skill}" in parts[0]:
            continue
        if os.path.isfile(src):
            body, more = split(open(src, encoding="utf-8").read())
            rules += [r for r in more if r not in rules]
            moved.append(skill)
        else:
            body = split(template)[0]
        parts.append(section(skill, body))

    os.makedirs(os.path.dirname(target), exist_ok=True)
    text = "\n\n".join(parts) + f"\n\n{RULE}\n" + "\n".join(rules) + ("\n" if rules else "")
    open(target, "w", encoding="utf-8").write(text)
    for skill in moved:
        if skill != name:
            shutil.rmtree(os.path.join(base, skill))
    done = update_table(os.path.join(base, "團隊名單.md"), name, skills)
    print(f"{name} 會：{'、'.join(done)}")


if __name__ == "__main__":
    main()
