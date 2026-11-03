#!/bin/sh
# 共用進度日誌：寫一行
# 用法：記進度.sh "<視窗名>" "<主線>" "<做了什麼>" "<下一步或卡在哪>"
ROOT=$(/usr/bin/env python3 -c 'import json,os;print(json.load(open(os.path.expanduser("~/.claude/角色機設定.json")))["root"])')
DIR="$ROOT/進度日誌"
mkdir -p "$DIR"
[ $# -lt 3 ] && { echo "用法：記進度.sh \"視窗名\" \"主線\" \"做了什麼\" \"下一步（可省略）\""; exit 1; }
F="$DIR/$(date +%F).md"
[ -f "$F" ] || printf '# 進度日誌 %s\n\n格式：時間｜視窗｜主線｜做了什麼｜下一步\n\n' "$(date +%F)" > "$F"
NEXT="${4:-}"
# 一行一筆：把換行和直線符號換掉，避免一筆拆成好幾行
clean() { printf '%s' "$1" | tr '\n' ' ' | sed 's/｜/／/g'; }
printf -- '- %s｜%s｜%s｜%s｜%s\n' "$(date +%H:%M)" "$(clean "$1")" "$(clean "$2")" "$(clean "$3")" "$(clean "$NEXT")" >> "$F"
echo "已記進 $F"
