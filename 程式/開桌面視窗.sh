#!/bin/sh
# 用手機遠端控制時，App 不讓 AI 直接開新視窗（start_session 會被擋）。這支在電腦上開一個桌面 App 視窗，手機看得到。
# 用法：sh ~/.claude/hooks/角色機/開桌面視窗.sh "<資料夾完整路徑>"
# 印出新視窗的 local_ 編號。接著依序：set_session_model（跟自己同模型）→ set_session_title → send_message（交代，貼老闆原話）→ set_remote_control 打開。
DIR="$1"; [ -d "$DIR" ] || { echo "資料夾不存在：$DIR"; exit 1; }
CL=$(command -v claude || ls "$HOME/.local/bin/claude" 2>/dev/null || ls "$HOME/.claude/local/claude" 2>/dev/null)
[ -n "$CL" ] || { echo "找不到 claude 指令：要先裝終端機版 Claude Code"; exit 1; }
U=$(uuidgen | tr A-Z a-z)
cd "$DIR" && "$CL" -p "這是新開的視窗，下一則才是交代。只回：收到" --session-id "$U" --model haiku >/dev/null 2>&1 || { echo "建立失敗"; exit 1; }
open -g "claude://resume?session=$U"
sleep 3
echo "local_$U"
