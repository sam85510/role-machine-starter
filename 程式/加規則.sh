#!/bin/sh
# 往那位的規格最後加一行，兩個視窗同時加也不會互蓋
# 用法：加規則.sh "<名字>" "<規則>" "<原因>"
ROOT=$(/usr/bin/env python3 -c 'import json,os;print(json.load(open(os.path.expanduser("~/.claude/角色機設定.json")))["root"])')
f="$ROOT/角色/$1/規格.md"
[ -f "$f" ] || { echo "找不到 $f"; exit 1; }
printf -- '- %s｜%s｜原因：%s\n' "$(date +%F)" "$2" "$3" >> "$f"
echo "已加進 $f"
