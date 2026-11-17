#!/usr/bin/env python3
# Stop hook：這輪 AI 寫給老闆看的字裡，有整句英文就擋一次，叫它整則改用繁體中文重寫。
# 起因：規則第一行寫了要講中文，AI 還是常講英文（規則一長就漏），改用程式擋。
# 只看 AI 講的字（含中途短句），不看工具動作。程式碼區塊、`行內程式碼`、網址、檔案路徑、連結網址都先拿掉。
# 算英文句：一行裡連續 6 個以上英文單字，或一行英文單字 ≥4 個且中文字少於 3 個。產品名、指令、檔名這種短的不算。
# 同一則只擋一次（stop_hook_active）。自己出錯就放行。
# 關掉：刪 ~/.claude/settings.json hooks.Stop 裡指向這支的那段。
import json, re, sys

WORD = r"[A-Za-z][A-Za-z'’\-]*"
RUN = re.compile(r"(?:%s[ ,;:.!?()\"/]+){5,}%s" % (WORD, WORD))
CJK = re.compile(r"[㐀-鿿]")
STRIP = [
    re.compile(r"```.*?```", re.S),
    re.compile(r"`[^`\n]*`"),
    re.compile(r"\[[^\]\n]*\]\([^)]*\)"),
    re.compile(r"https?://\S+"),
    re.compile(r"(?:~|\.{0,2})?/[^\s，。、）)]+"),
    re.compile(r"\b[\w\-]+\.(?:py|sh|md|json|txt|html|js|css|mov|mp4|png|jpg|pdf|zip)\b"),
    re.compile(r"<[^>\n]+>"),
]


def text_of(c):
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "\n".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
    return ""


def real_user(r):
    if r.get("type") != "user" or r.get("isMeta"):
        return False
    c = (r.get("message") or {}).get("content")
    if isinstance(c, list) and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
        return False
    t = text_of(c)
    return bool(t.strip()) and not t.startswith("Stop hook feedback")


def said_this_turn(path):
    rows = []
    with open(path, encoding="utf-8", errors="ignore") as fh:
        for ln in fh:
            try:
                rows.append(json.loads(ln))
            except Exception:
                pass
    start = 0
    for i in range(len(rows) - 1, -1, -1):
        if real_user(rows[i]):
            start = i + 1
            break
    out = []
    for r in rows[start:]:
        c = (r.get("message") or {}).get("content")
        if r.get("type") == "assistant" and isinstance(c, list):
            for b in c:
                if isinstance(b, dict) and b.get("type") == "text" and b.get("text", "").strip():
                    out.append(b["text"])
    return out


def english_lines(text):
    for rx in STRIP:
        text = rx.sub(" ", text)
    bad = []
    for line in text.splitlines():
        s = line.strip(" \t-*>#|0123456789.、")
        if not s:
            continue
        words = re.findall(WORD, s)
        cjk = len(CJK.findall(s))
        if RUN.search(s) or (len(words) >= 4 and cjk < 3):
            bad.append(s[:100])
    return bad


def main():
    try:
        d = json.load(sys.stdin)
    except Exception:
        return
    if d.get("stop_hook_active") or not d.get("transcript_path"):
        return
    try:
        said = said_this_turn(d["transcript_path"])
    except Exception:
        return
    bad = []
    for t in said:
        bad += english_lines(t)
    if not bad:
        return
    print(json.dumps({"decision": "block", "reason":
        "【講中文】這輪寫給老闆看的字裡有英文句子，例如：「" + bad[0] + "」" + ("（共 " + str(len(bad)) + " 處）" if len(bad) > 1 else "") +
        "。規則第一條：給老闆看的字一律繁體中文，包括中途短句、表格、說明；只有程式碼、檔名、網址、產品名可以留英文；要給別的工具用的英文提示詞放進 ``` 程式碼區塊。"
        "請把整則改用繁體中文重寫，老闆只看你重寫的這一則，前一則的結論和要他做的事都要寫進來。"}, ensure_ascii=False))


main()
