#!/usr/bin/env python3
# 收工自動跑，三項檢查，每項最多擋一次：
# 1. 筆記本太長 2. 老闆做了決定卻沒寫下來 3. 有產出卻沒記日誌
# 排程自動跑的視窗不擋。關掉：刪 ~/.claude/settings.json 裡指向這支的那一段
import datetime, glob, json, os, re, sys

HOOKS = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HOOKS, "state")
LIMIT = 10000  # 筆記本超過這個字數，新視窗就可能讀不完
WORK_MIN = 3   # 上次記日誌之後，幾次有產出的動作才擋

DECIDE = re.compile(r"(?<![一確])定|決定|就這樣|以後|不要|別再|改成|改用|換成|規則|記得|一律|都要|不用|用這個|選[A-Za-z0-9一二三四五]|照這樣|取消")
SHORT_OK = re.compile(r"^(好|好的|好啊|可以|OK|ok|對|同意|就這個|[A-Da-d1-5])[。！!～~ ]*$")
ASK = re.compile(r"[？?]\s*$|嗎|是不是|會不會|對不對|要不要|呢")
LOGGED = re.compile(r"記進度\.sh[\"']?\s+[\"']")
WRITE_TOOLS = {"Edit", "Write", "NotebookEdit", "Artifact", "SendMessage"}

def block(reason):
    print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
    sys.exit(0)

def once(key, value):
    """同一件事只擋一次：value 跟上次一樣就回 False"""
    os.makedirs(STATE, exist_ok=True)
    f = os.path.join(STATE, re.sub(r"[^0-9A-Za-z_-]", "_", key))
    if os.path.exists(f) and open(f, encoding="utf-8").read() == value:
        return False
    open(f, "w", encoding="utf-8").write(value)
    return True

def notebooks(root):
    return glob.glob(os.path.join(root, "*", "筆記", "*.md")) + glob.glob(os.path.join(root, "角色", "*", "規格.md"))

def read_turns(path):
    """回傳（是不是排程、老闆最後一句、上次記日誌後的產出次數）"""
    last, work, sched, first = None, 0, False, True
    with open(path, encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except Exception:
                continue
            c = d.get("message", {}).get("content") if isinstance(d.get("message"), dict) else None
            if d.get("type") == "user" and not d.get("isMeta"):
                if isinstance(c, list):  # 有的版本把打字內容包成清單；工具結果不算老闆講的話
                    c = "".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text") or None
                if isinstance(c, str):
                    if first and "<scheduled-task" in c[:200]:
                        sched = True
                    first = False
                    if not c.lstrip().startswith("<"):
                        last = (d.get("uuid") or "", d.get("timestamp") or "", c.strip())
            elif d.get("type") == "assistant" and isinstance(c, list):
                for b in c:
                    if not isinstance(b, dict) or b.get("type") != "tool_use":
                        continue
                    if b.get("name") == "Bash" and LOGGED.search(str((b.get("input") or {}).get("command", ""))):
                        work = 0
                    elif b.get("name") in WRITE_TOOLS:
                        work += 1
    return sched, last, work

def main():
    try:
        inp = json.load(sys.stdin)
        cfg = json.load(open(os.path.expanduser("~/.claude/角色機設定.json"), encoding="utf-8"))
    except Exception:
        return
    if inp.get("stop_hook_active"):
        return
    path, sid = inp.get("transcript_path") or "", inp.get("session_id") or "x"
    if not os.path.exists(path):
        return
    root, boss = cfg["root"], cfg.get("boss") or "老闆"
    sched, last, work = read_turns(path)
    if sched:
        return
    files = notebooks(root)

    for f in glob.glob(os.path.join(root, "*", "筆記", "*.md")):
        if os.path.basename(f) == "歷史.md":
            continue
        size = len(open(f, encoding="utf-8").read())
        if size > LIMIT and once(f"long-{f}", str(size // 1500)):
            block(f"{f} 已經 {size} 字，超過 1 萬字，新視窗可能讀不完。"
                  f"請現在整理：做完的事和舊決定搬到同資料夾的 歷史.md（不刪），筆記本只留手上的事和最近的決定，壓到 8000 字內。"
                  f"整理完直接結束，不用跟 {boss} 提這個檢查。")

    if last:
        uid, ts, text = last
        if not ASK.search(text) and (DECIDE.search(text) or SHORT_OK.match(text)):
            try:
                t = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
            except Exception:
                t = None
            newest = max([os.path.getmtime(f) for f in files] or [0])
            if t and newest < t and once(f"decide-{sid}", uid):
                short = text if len(text) <= 40 else text[:40] + "…"
                block(f"{boss} 這次說「{short}」，像是一個決定或同意。寫進這件任務筆記本的「試行中」（附日期），不用問 {boss} 要不要建規則。"
                      f"事情做完 {boss} 收下、或同一個修正兩件事都出現，才用 加規則.sh 升進那位的規格，收尾講一句「已加規則：…」。"
                      f"不是決定的話直接結束，不用跟 {boss} 提這個檢查。")

    if work >= WORK_MIN and once(f"log-{sid}", str(work)):
        helper = os.path.join(HOOKS, "記進度.sh")
        block(f"收工前先記一行進度日誌（上次記錄後做了 {work} 次有產出的動作）。記完照原本的方式回覆，不用提這件事：\n"
              f"sh \"{helper}\" \"<視窗名>\" \"<主線>\" \"<做了什麼，一句話>\" \"<下一步或卡在哪>\"")

main()
