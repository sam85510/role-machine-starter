#!/bin/bash
# 角色機入門包：第一次安裝和之後更新都跑這支
# 用法：bash 安裝.sh --稱呼 "你要 AI 怎麼叫你" [--資料夾 "工作資料夾路徑"]
# 會動到的只有：~/.claude/CLAUDE.md 裡標記的那一段、~/.claude/settings.json 加掛檢查、工作資料夾裡缺的檔案
# 不會動：你原本的規則、原本的設定、已經長出規則的規格、筆記本、日誌
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
BOSS=""; ROOT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --稱呼) BOSS="$2"; shift 2 ;;
    --資料夾) ROOT="$2"; shift 2 ;;
    *) echo "看不懂的參數：$1"; exit 1 ;;
  esac
done
CFG="$HOME/.claude/角色機設定.json"
PY=$(command -v python3 || true)
[ -n "$PY" ] || { echo "這台電腦沒有 python3，先裝好再跑"; exit 1; }
mkdir -p "$HOME/.claude/hooks/角色機" "$HOME/.claude/commands"

# 更新時沿用上次的設定
if [ -f "$CFG" ]; then
  [ -n "$BOSS" ] || BOSS=$("$PY" -c 'import json,sys;print(json.load(open(sys.argv[1])).get("boss",""))' "$CFG")
  [ -n "$ROOT" ] || ROOT=$("$PY" -c 'import json,sys;print(json.load(open(sys.argv[1])).get("root",""))' "$CFG")
fi
[ -n "$BOSS" ] || { echo "第一次裝要說怎麼稱呼你：bash 安裝.sh --稱呼 \"小明\""; exit 1; }
[ -n "$ROOT" ] || ROOT="$HOME/Claude工作室"

# 倉庫有連線就先抓最新版
if [ -d "$HERE/.git" ] && git -C "$HERE" remote get-url origin >/dev/null 2>&1; then
  git -C "$HERE" pull -q --ff-only || echo "抓最新版失敗，先用手上這版繼續裝"
fi

# 1. 程式：有變才換，舊的留備份
D=$(date +%Y-%m-%d); n=0
for f in 開工.py 收工.py 記進度.sh 加規則.sh 取名.py; do
  dst="$HOME/.claude/hooks/角色機/$f"
  if [ ! -f "$dst" ] || ! cmp -s "$HERE/程式/$f" "$dst"; then
    [ -f "$dst" ] && cp "$dst" "$dst.bak-$D"
    cp "$HERE/程式/$f" "$dst"; chmod +x "$dst"; n=$((n+1)); echo "更新：$f"
  fi
done
for f in 收工.md 新專長.md 開張.md; do
  dst="$HOME/.claude/commands/$f"
  if [ ! -f "$dst" ] || ! cmp -s "$HERE/程式/$f" "$dst"; then
    cp "$HERE/程式/$f" "$dst"; n=$((n+1)); echo "更新：指令 $f"
  fi
done

# 2. 工作資料夾：只補缺的，不蓋已經存在的檔案
mkdir -p "$ROOT/進度日誌"
(cd "$HERE/工作資料夾範本" && find . -type f) | while IFS= read -r f; do
  dst="$ROOT/${f#./}"
  # 開張後預設專長已併進名字，不再補回來
  if [ -f "$ROOT/角色/.已開張" ]; then
    case "$f" in ./角色/總入口/*|./角色/審核/*|./角色/工程/*|./角色/研究/*|./角色/企劃/*) continue ;; esac
  fi
  case "$f" in
    */_範本/*) mkdir -p "$(dirname "$dst")"; cp "$HERE/工作資料夾範本/$f" "$dst" ;;
    *) [ -f "$dst" ] || { mkdir -p "$(dirname "$dst")"; cp "$HERE/工作資料夾範本/$f" "$dst"; } ;;
  esac
done
cp "$HERE/彎路清單.md" "$ROOT/彎路清單.md"

# 3. 設定和全域規則：改之前先備份
"$PY" - "$HOME" "$PY" "$HERE" "$BOSS" "$ROOT" <<'PY'
import datetime, json, os, shutil, sys
home, py, here, boss, root = sys.argv[1:]
day = datetime.date.today().isoformat()
json.dump({"boss": boss, "root": root}, open(f"{home}/.claude/角色機設定.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

p = f"{home}/.claude/settings.json"
s = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
add = 0
for ev, name, sec in (("SessionStart", "開工.py", 15), ("Stop", "收工.py", 15)):
    cmd = f'"{py}" "{home}/.claude/hooks/角色機/{name}"'
    items = s.setdefault("hooks", {}).setdefault(ev, [])
    if not any(h.get("command") == cmd for it in items for h in it.get("hooks", [])):
        items.append({"hooks": [{"type": "command", "command": cmd, "timeout": sec}]}); add += 1
if add:
    if os.path.exists(p):
        shutil.copy(p, f"{p}.bak-{day}")
    json.dump(s, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

A, B = "<!-- 角色機規則開始：這段由安裝程式更新，要加自己的規則請寫在這段外面 -->", "<!-- 角色機規則結束 -->"
rule = open(f"{here}/規則範本.md", encoding="utf-8").read().replace("老闆", boss).strip()
rule += f"\n\n> 規格和指令裡寫的「老闆」，就是{boss}。"
block = f"{A}\n{rule}\n{B}"
p = f"{home}/.claude/CLAUDE.md"
old = open(p, encoding="utf-8").read() if os.path.exists(p) else ""
if A in old and B in old:
    new = old[:old.index(A)] + block + old[old.index(B) + len(B):]
else:
    new = (old.rstrip() + "\n\n" if old.strip() else "") + block + "\n"
if new != old:
    if old:
        shutil.copy(p, f"{p}.bak-{day}")
    open(p, "w", encoding="utf-8").write(new)
    print("全域規則已更新")
print(f"檢查新掛上 {add} 支")
PY

echo "完成。程式和指令更新 $n 項。工作資料夾：$ROOT"
echo "重開 Claude 或開新視窗後生效。"
