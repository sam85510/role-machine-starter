#!/usr/bin/env python3
# 收工檢查：視窗標題沒寫「任務名｜名字」就擋一次，叫它看團隊名單改標題。
# 只在 Claude 桌面 App 有效（終端機版沒有標題，這支自動略過）。每個視窗只擋一次；排程自動開、老闆沒進去講過話的視窗不擋。
# 標題有「總入口」的不擋（總入口是固定視窗）。
# 關掉：刪 ~/.claude/settings.json 裡指向這支的那一段。
import glob, json, os, sys

SESS = os.path.expanduser("~/Library/Application Support/Claude/claude-code-sessions")
HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "state", "標題")


def root():
    try:
        return json.load(open(os.path.expanduser("~/.claude/角色機設定.json"), encoding="utf-8")).get("root") or "~/Claude工作室"
    except Exception:
        return "~/Claude工作室"


def boss_talked(path):
    try:
        for l in open(path, encoding="utf-8"):
            try:
                d = json.loads(l)
            except Exception:
                continue
            if d.get("type") != "user" or d.get("isMeta") or d.get("isCompactSummary"):
                continue
            c = (d.get("message") or {}).get("content")
            if isinstance(c, list):
                c = next((x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text"), "")
            c = (c or "").strip()
            if c and not c.startswith("<") and not c.startswith("This session is being continued"):
                return True
    except Exception:
        pass
    return False


def lookup(cli):
    for f in glob.glob(os.path.join(SESS, "*", "*", "local_*.json")):
        try:
            t = open(f, encoding="utf-8").read()
            if cli not in t:
                continue
            d = json.loads(t)
        except Exception:
            continue
        if d.get("cliSessionId") == cli:
            return d
    return None


def main():
    try:
        inp = json.load(sys.stdin)
    except Exception:
        return
    if inp.get("stop_hook_active") or not inp.get("session_id"):
        return
    d = lookup(inp["session_id"])
    if not d:
        return
    lid, title = d.get("sessionId") or "", (d.get("title") or "").strip()
    if "總入口" in title or (d.get("scheduledTaskId") and not boss_talked(inp.get("transcript_path") or "")):
        return
    if "｜" in title and title.split("｜", 1)[1].strip():
        return
    sf = os.path.join(STATE, lid + ".done")
    if os.path.exists(sf):
        return
    os.makedirs(STATE, exist_ok=True)
    open(sf, "w").write(title)
    team = os.path.join(os.path.expanduser(root()), "角色", "團隊名單.md")
    print(json.dumps({"decision": "block", "reason":
        f"這個視窗標題是「{title or '（沒有標題）'}」，沒照規則寫「任務名｜名字」。"
        f"先讀 {team}，看這件事是誰的工作，標題寫他（可以好幾位，用 / 隔開）。"
        f"改法：ToolSearch select:mcp__ccd_session_mgmt__set_session_title，session_id 填 \"self\"，"
        f"title 寫「{(title.split('｜')[0] or '任務名')}｜<名字>」。改好在回覆補一句「這件帶 <名字>」。"
        f"改不了（手機開的視窗）就在回覆最後一行寫「這個視窗請改名：<任務名｜名字>」讓老闆手動改，寫過就結束。"}, ensure_ascii=False))


main()
