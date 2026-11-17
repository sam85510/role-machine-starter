#!/usr/bin/env python3
# 主線符號（手機、網頁版沒有電腦版的縮排，要靠名字認出主線和子視窗）
# 視窗標題格式：主視窗「🛒3 任務｜專長」，老闆打了 ★△● 就「🛒★ 任務｜專長」（記號取代號碼）、子視窗「🛒3↳子任務｜專長」（子視窗用爸爸的符號和號碼）。
# 兩種用法：
#   python3 主線符號.py 下一號 <主線或資料夾名>   → 印出新主視窗該用的開頭，例「🛒9 」
#   （Stop hook，stdin 是 hook JSON）            → 自己標題沒照格式就擋一次，告訴它該改成什麼
# 不擋：總入口、排程（標題【開頭或有 scheduledTaskId）、還沒照「任務｜名字」寫的（歸 標題檢查.py）。
# 關掉：刪 settings.json 裡 hooks.Stop 指向這支的那段。狀態在同資料夾 state_sym/。
import glob, json, os, re, sys

def _talked(inp):  # 排程開的視窗，老闆後來進去講過話沒
    try:
        for l in open(inp.get("transcript_path") or "", encoding="utf-8"):
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

SESS = os.path.expanduser("~/Library/Application Support/Claude/claude-code-sessions")
STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state_sym")
SYM = {}  # 沒有 分區符號.txt 就什麼都不做
SKIP = set()
try:  # 分區和符號：同資料夾放 分區符號.txt，一行「資料夾名 符號」（安裝時 Claude 會帶你設定）
    _f = os.path.join(os.path.dirname(os.path.abspath(__file__)), "分區符號.txt")
    _x = [l.split("#")[0].split() for l in open(_f, encoding="utf-8")]
    _x = {a[0]: a[1] for a in _x if len(a) >= 2}
    if _x: SYM = _x
except FileNotFoundError:
    pass
if not SYM:
    if len(sys.argv) > 1 and sys.argv[1] == "下一號":
        print("還沒設定分區符號：請 Claude 照角色機 README「選裝引導」幫你設定")
    sys.exit(0)
ROOT = "~/Claude工作室"
try:
    ROOT = json.load(open(os.path.expanduser("~/.claude/角色機設定.json"), encoding="utf-8")).get("root") or ROOT
except Exception:
    pass
PRE = re.compile("^(" + "|".join(re.escape(v.rstrip("\ufe0f")) + "\ufe0f?" for v in SYM.values()) + r")(\d+|[★△●]+)(↳| ?)")
MARK = "★△●"  # 老闆自己打的記號：只能取代數字編號→「🛒★ 任務」，有記號就不放號碼

def parse(t):
    """拆成（符號, 號碼, 是不是子視窗, 老闆的記號, 剩下的字）。記號不管 老闆打在哪都收進來。"""
    t = (t or "").strip()
    marks, sym, num, child = "", None, None, False
    m = re.match(r"^([★△●]+)\s*", t)
    if m:
        marks += m.group(1); t = t[m.end():]
    m = PRE.match(t)
    if m:
        sym, x, child = m.group(1), m.group(2), m.group(3) == "↳"
        t = t[m.end():]
        if x[0] in MARK:
            marks += x
        else:
            num = x
    m = re.match(r"^\s*([★△●]+)\s*", t)
    if m and not child:
        marks += m.group(1); t = t[m.end():]
    return sym, num, child, marks, t.strip()

def load():
    out = {}
    for f in glob.glob(os.path.join(SESS, "*", "*", "local_*.json")):
        try:
            d = json.load(open(f, encoding="utf-8"))
            out[d["sessionId"]] = d
        except Exception:
            pass
    return out

def line_of(name):
    for k, v in SYM.items():
        if name and (k in name or name == v):
            return k, v
    for k, v in SYM.items():  # 「上架產品」這種沒編號的寫法
        if name and k.lstrip("0123456789") in name:
            return k, v
    return None, None

def next_no(sym, allx):
    used = set()
    for d in allx.values():
        if d.get("isArchived"):
            continue
        m = PRE.match(d.get("title") or "")
        if m and m.group(2).isdigit() and m.group(1).rstrip("️") == sym.rstrip("️"):
            used.add(int(m.group(2)))
    n = 1
    while n in used:
        n += 1
    return n

def cli():
    k, v = line_of(sys.argv[2] if len(sys.argv) > 2 else "")
    if not v:
        print("對不到主線，請寫：" + "、".join(SYM))
        return
    print(f"{v}{next_no(v, load())} ")

def hook():
    try:
        inp = json.load(sys.stdin)
    except Exception:
        return
    if inp.get("stop_hook_active"):
        return
    allx = load()
    me = next((d for d in allx.values() if d.get("cliSessionId") == inp.get("session_id")), None)
    if not me:
        return
    sid, title = me.get("sessionId"), (me.get("title") or "").strip()
    if "總入口" in title or (me.get("scheduledTaskId") and not _talked(inp)) or (title.startswith("【") and not _talked(inp)) or "｜" not in title:
        return
    sym, num, child, marks, rest = parse(title)
    par = allx.get((me.get("spawnedFrom") or {}).get("sessionId") or "")
    want = None
    if par and par.get("sessionId") not in SKIP and not par.get("isArchived") and PRE.match(par.get("title") or ""):
        ps, pn, _, pm_, _ = parse(par.get("title"))
        code = f"{ps}{pm_ or pn}↳"
        want = f"{code}{marks}{rest}" if not child else f"{code}{rest}"
        why = f"你是「{par.get('title')}」開的子視窗"
    else:
        if sym:
            want = f"{sym}{marks or num} {rest}" if (marks or num) else None
            why = "老闆的記號（★△●）要放在號碼的位置，不放號碼"
        else:
            top = os.path.relpath(me.get("cwd") or "", os.path.expanduser(ROOT)).split(os.sep)[0]
            k, v = line_of(top)
            if v:
                want = f"{v}{marks or next_no(v, allx)} {rest}"
                why = f"你開在「{k}」資料夾"
            else:
                want = "<主線符號><號碼或 老闆的記號> " + rest
                why = "對不到主線，看側邊欄你在哪個分區，用 python3 ~/.claude/hooks/角色機/主線符號.py 下一號 <分區名> 拿開頭"
    if want == title:
        want = None
    if not want:
        return
    os.makedirs(STATE, exist_ok=True)
    st = os.path.join(STATE, sid)
    if os.path.exists(st) and open(st).read() == title:
        return  # 同一個標題只擋一次
    open(st, "w").write(title)
    print(json.dumps({"decision": "block", "reason":
        f"標題要加主線符號：{why}。"
        f"用 mcp__ccd_session_mgmt__set_session_title（session_id \"self\"）改成「{want}」，"
        "老闆打的 ★△● 放在號碼的位置（例「🛒★ 任務」），不要再加號碼。分區不對就照分區的符號改。改完不用跟 老闆提。"}, ensure_ascii=False))

if len(sys.argv) > 1 and sys.argv[1] == "下一號":
    cli()
else:
    hook()
