#!/usr/bin/env python3
# 收工檢查共用：讀對話紀錄，整理「這一輪」（老闆 最後一句真的話之後）AI 做了哪些工具動作、講了什麼。
# 11/17 起（照架構師考試 1.1／1.4）：檢查程式看「有沒有真的去查」這種動作，不靠掃 AI 用字決定擋不擋。
import json, re

# 算「去查」的工具：讀檔、搜尋、跑指令、上網、開瀏覽器、讀頁面資料庫、派子助手
LOOK_TOOLS = {"Read", "Grep", "Glob", "Bash", "WebFetch", "WebSearch", "Agent", "Task",
              "ArtifactData", "ArtifactComments", "NotebookRead", "ReadMcpResourceTool"}
NOT_LOOK = {"ToolSearch", "TodoWrite", "Skill", "SendMessage", "AskUserQuestion", "Edit", "Write",
            "NotebookEdit", "ScheduleWakeup", "ExitPlanMode", "EnterPlanMode"}

# 打不開、被擋、逾時（＝沒查成，要換方法）；不含「檔案不存在／404」那種＝查過確實沒有
ACCESS_FAIL = re.compile(
    r"timed? ?out|(?-i:\b(ETIMEDOUT|ECONNREFUSED|ECONNRESET|ENOTFOUND)\b)|Unable to connect|Failed to connect|"
    r"Could not resolve host|net::ERR|Forbidden|Unauthorized|rate.?limit|Too Many Requests|"
    r"Service Unavailable|Bad Gateway|Operation not permitted|Permission denied|not connected|"
    r"HTTPError|URLError|ConnectionError|TimeoutError|TimeoutExpired|"
    r"HTTP[/ 0-9.]*(Error )?(401|403|407|429|5\d\d)\b|status( code)?[ :=]+(401|403|429|5\d\d)\b|"
    r"無法連接|連不上|逾時|超時|拒絕存取", re.I)
# 被 老闆 或權限系統拒絕：規則是不硬試、交給 老闆，不算要再試的失敗
USER_DENY = re.compile(r"doesn't want to proceed|was rejected|denied by|has been denied|"
                       r"user declined|auto mode classifier|blocked by (a )?hook|hook.*block", re.I)
# 指令自己寫錯（指令不存在、語法錯）＝不是被擋，是要改指令，不算
SELF_ERR = re.compile(r"command not found|syntax error|SyntaxError|unrecognized option|usage:", re.I)


def is_look(name, inp=None):
    if name in NOT_LOOK:
        return False
    if name == "Artifact":
        return (inp or {}).get("action") in ("read", "list")
    return name in LOOK_TOOLS or name.startswith("mcp__")


def _text(c):
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        out = []
        for b in c:
            if isinstance(b, dict):
                if b.get("type") == "text":
                    out.append(b.get("text", ""))
                elif b.get("type") == "tool_result":
                    out.append(_text(b.get("content")))
        return "\n".join(out)
    return ""


def _real_user(r):
    if r.get("type") != "user" or r.get("isMeta"):
        return False
    c = (r.get("message") or {}).get("content")
    if isinstance(c, str):
        return not c.startswith("Stop hook feedback")
    if isinstance(c, list):
        has_text = any(isinstance(b, dict) and b.get("type") == "text" for b in c)
        has_res = any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c)
        if has_text and not has_res:
            t = _text(c)
            return not t.startswith("Stop hook feedback")
    return False


def load(path):
    rows = []
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            for ln in fh:
                try:
                    rows.append(json.loads(ln))
                except Exception:
                    pass
    except Exception:
        pass
    return rows


def turn(rows):
    """回傳 dict：said（這輪 AI 講的字，依序）、last（最後一則有字的回覆）、tools（[{name,input,error,result}]）、fb（這輪收到的收工檢查回饋）"""
    start = 0
    for i in range(len(rows) - 1, -1, -1):
        if _real_user(rows[i]):
            start = i + 1
            break
    said, tools, fb, by_id = [], [], [], {}
    for r in rows[start:]:
        m = r.get("message") or {}
        c = m.get("content")
        if r.get("type") == "assistant" and isinstance(c, list):
            for b in c:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "text" and b.get("text", "").strip():
                    said.append(b["text"])
                elif b.get("type") == "tool_use":
                    t = {"name": b.get("name", ""), "input": b.get("input") or {}, "error": False, "result": ""}
                    tools.append(t)
                    by_id[b.get("id")] = t
        elif r.get("type") == "user":
            if isinstance(c, str) and c.startswith("Stop hook feedback"):
                fb.append(c)
                continue
            if isinstance(c, list):
                for b in c:
                    if isinstance(b, dict) and b.get("type") == "tool_result":
                        t = by_id.get(b.get("tool_use_id"))
                        if t is not None:
                            t["error"] = bool(b.get("is_error"))
                            t["result"] = _text(b.get("content"))[:2000]
                    elif isinstance(b, dict) and b.get("type") == "text" and b.get("text", "").startswith("Stop hook feedback"):
                        fb.append(b["text"])
    return {"said": said, "last": said[-1] if said else "", "tools": tools, "fb": fb}


def looks(tools):
    return [t for t in tools if is_look(t["name"], t["input"])]


def access_fail(t):
    """這個工具動作是不是「打不開、被擋、逾時」。被 老闆／權限擋的不算（規則是交給 老闆）。"""
    if not is_look(t["name"], t["input"]):
        return False
    r = t["result"][:600]
    if USER_DENY.search(r) or SELF_ERR.search(r):
        return False
    if t["error"] and ACCESS_FAIL.search(r):
        return True
    # 網頁類工具：沒標錯但內容開頭就是連線錯誤
    if (t["name"] in ("WebFetch",) or "navigate" in t["name"] or "get_page_text" in t["name"]) and ACCESS_FAIL.search(r[:200]):
        return True
    return False


def edited_notes(tools):
    for t in tools:
        if t["name"] in ("Edit", "Write", "MultiEdit"):
            p = str(t["input"].get("file_path", ""))
            if "筆記" in p or "/角色/" in p:
                return True
        if t["name"] == "Bash" and "筆記" in str(t["input"].get("command", "")) and re.search(r">>|tee|sed -i|python", str(t["input"].get("command", ""))):
            return True
    return False
