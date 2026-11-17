#!/usr/bin/env python3
# Stop hook：這輪去查的動作「打不開、被擋、逾時」，之後卻沒再換方法查成功，就擋一次，叫視窗換方法。
# 起因 11/16 老闆：「你跟我說沒找到什麼，但也許再努力一下就看得到了；我要怎樣讓這件事自動完成，而不是我又要再傳訊息跟你說方法？」
# 11/17 第 4 版（架構師考試 1.1／2.2／5.3）：不再掃 AI 回覆裡的「找不到」字眼（11/16 一天誤擋 3 次），改看工具動作：
#   - 打不開、被擋、逾時（連線錯誤、401/403/429/5xx、逾時）＝還沒查成 → 要換方法，沒換就擋。
#   - 查過確實沒有（檔案不存在、404、搜尋 0 筆）＝已經查到答案是「沒有」 → 不擋，直接講「沒有」並附查了哪裡。
#   - 被 老闆 或權限系統拒絕 → 不擋（規則是不硬試、交給 老闆）。
# 舊版字眼檢查見 檢查.py.bak-2026-11-17-改看動作。同一則只擋一次（stop_hook_active）。
# 關掉：刪 settings.json hooks.Stop 裡指向這支的那段。
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import 這輪 as T


def main():
    try:
        d = json.load(sys.stdin)
    except Exception:
        return
    if d.get("stop_hook_active"):
        return
    p = d.get("transcript_path")
    if not p:
        return
    tw = T.turn(T.load(p))
    tools = tw["tools"]
    fails = [i for i, t in enumerate(tools) if T.access_fail(t)]
    if not fails:
        return
    last = fails[-1]
    # 失敗之後有任何一次去查成功（不管同一招重試成功或換招），就算有換方法
    if any(T.is_look(t["name"], t["input"]) and not t["error"] and not T.access_fail(t) for t in tools[last + 1:]):
        return
    t = tools[last]
    what = t["name"]
    target = t["input"].get("url") or t["input"].get("file_path") or t["input"].get("command") or t["input"].get("query") or ""
    err = " ".join(t["result"].split())[:120]
    print(json.dumps({"decision": "block", "reason":
        "【沒找到要再試】你這輪最後一次去查沒查成（打不開、被擋或逾時）：" + what + "「" + str(target)[:80] + "」→「" + err + "」。"
        "這代表還沒查到，不代表沒有。老闆 11/16：不要等他傳訊息教方法，先自己換方法。"
        "請換一種還沒用過的方法再查，例如：換內建瀏覽器或 Chrome、換另一個 Chrome 帳號、看畫面截圖、"
        "讀 App 紀錄 ~/Library/Logs/Claude、讀資料庫實際欄位、在程式文字裡搜關鍵字、上網查官方說明、開子助手找。"
        "查到就照常回。被權限擋、要登入、要花錢、要打密碼的不要硬試，回覆加一行「試過：<方法和結果>」交給 老闆。"
        "老闆 只看你重回的這一則：上一則的結論、全文、要 老闆 做的事全部重寫進來。"}, ensure_ascii=False))


main()
