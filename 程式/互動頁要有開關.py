#!/usr/bin/env python3
"""互動頁要有開關（2026-11-16 老闆：「你以后有要做这种互动式的，你不如就把互动的开关直接做在里面，不然我还要一个一个打字回讯息」）
PreToolUse（Artifact 發布）：頁面文字叫 老闆「回編號／選／確認／定」，卻沒有互動功能（claude.use 的 db 或 artifact）→ 擋一次，
請把按鈕做進頁面（存進 db，之後用 ArtifactData 讀）。同一個檔擋過一次就放行；讀不懂一律放行。"""
import json, sys, os, re, hashlib
STATE = os.path.expanduser("~/.claude/hooks/角色機/.互動頁已擋.json")
ASK = re.compile(r"回編號|回哪幾|請你回|要你選|你選|待你填|待你確認|請你確認|你決定|要不要傳|選哪|圈出")
MSG = ("老闆 11/16 定：要他選、確認、填的頁面，把互動開關直接做在頁面裡（按鈕／勾選／開關），不要叫他打字回訊息。"
       "這個頁面文字有叫他回覆選擇的句子，卻沒有 claude.use('db') 的互動。做法：先載入 artifact-capabilities 技能，"
       "發布時帶 capabilities:{db:{}}，每個選項一顆大按鈕，點了寫進 db（每項一份文件），之後用 ArtifactData list 讀他的選擇；"
       "頁面上寫『選完不用回訊息，我會自己讀』。"
       "真的只是純看的頁面就原樣再發一次（這個檔只擋一次）。")
def main():
    try: d = json.load(sys.stdin)
    except Exception: return 0
    if d.get("tool_name") != "Artifact": return 0
    ti = d.get("tool_input") or {}
    if ti.get("action") not in (None, "publish") or ti.get("asset") or ti.get("type_url"): return 0
    fp = ti.get("file_path") or ""
    if not fp.endswith(".html") or not os.path.exists(fp): return 0
    t = open(fp, encoding="utf-8", errors="ignore").read()
    if "claude.use(" in t or not ASK.search(t): return 0
    try: st = json.load(open(STATE))
    except Exception: st = {}
    k = hashlib.md5(fp.encode()).hexdigest()
    if st.get(k): return 0
    st[k] = 1
    try: json.dump(st, open(STATE, "w"))
    except Exception: return 0
    sys.stderr.write(MSG); return 2
if __name__ == "__main__":
    try: sys.exit(main())
    except Exception: sys.exit(0)
