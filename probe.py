"""第 0 步 · 抓取可行性探测

唯一目的：确认当前这台机器（尤其是 GitHub Actions 的服务器）到底能不能
抓到微博 / 雪球的数据。它不存储、不展示，只抓一次并打印详细诊断。

从环境变量读取参数（在 GitHub Actions 里由 workflow / Secrets 注入）：
    WEIBO_UIDS    逗号分隔的微博 uid，如 "1234567890,222"
    WEIBO_COOKIE  可选，微博 cookie 整串
    XUEQIU_UIDS   逗号分隔的雪球 uid
    XUEQIU_COOKIE 雪球 cookie 整串（雪球接口必须带）

看输出时重点看每个账号的三行：HTTP 状态、返回是不是 JSON、抓到几条。
只要有一个平台能稳定抓到条数，这条路就走得通。
"""

import os
import time
import calendar
import requests
from bs4 import BeautifulSoup

UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148")
TIMEOUT = 15


def clean(html):
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for img in soup.find_all("img"):
        img.replace_with(img.get("alt") or "")
    return " ".join(soup.get_text().split())


def show_exit_ip():
    """打印这台机器的出口 IP 和归属国家 —— 判断是不是海外 IP 的关键。"""
    try:
        r = requests.get("https://ipinfo.io/json", timeout=TIMEOUT)
        d = r.json()
        print(f"出口 IP: {d.get('ip')}  归属: {d.get('country')} {d.get('region','')} {d.get('org','')}")
    except Exception as e:
        print(f"出口 IP: 查询失败（{e}）")
    print()


def probe_weibo(uid, cookie):
    print(f"  账号 {uid}:")
    url = ("https://m.weibo.cn/api/container/getIndex"
           f"?type=uid&value={uid}&containerid=107603{uid}")
    headers = {"User-Agent": UA, "Referer": f"https://m.weibo.cn/u/{uid}",
               "X-Requested-With": "XMLHttpRequest"}
    if cookie:
        headers["Cookie"] = cookie
    try:
        r = requests.get(url, headers=headers, timeout=TIMEOUT)
    except Exception as e:
        print(f"    请求异常: {e}")
        return
    print(f"    HTTP {r.status_code}")
    body = r.text.lstrip()
    is_json = body.startswith("{")
    print(f"    返回是 JSON: {'是' if is_json else '否'}")
    if not is_json:
        print(f"    ==> 非 JSON，疑似被反爬/需登录。返回开头: {' '.join(r.text.split())[:160]}")
        return
    data = r.json()
    if data.get("ok") != 1:
        print(f"    ==> ok={data.get('ok')}，接口未正常返回（常见于海外 IP 需 cookie）。"
              f" msg: {str(data.get('msg'))[:80]}")
        return
    cards = [c for c in data.get("data", {}).get("cards", []) if c.get("card_type") == 9]
    print(f"    抓到 {len(cards)} 条 ✓")
    if cards:
        m = cards[0]["mblog"]
        print(f"    最新: {m.get('user',{}).get('screen_name')} | "
              f"{m.get('created_at')} | {clean(m.get('text'))[:50]}")


def probe_xueqiu(uid, cookie):
    print(f"  账号 {uid}:")
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Referer": "https://xueqiu.com/",
                      "Accept": "application/json, text/plain, */*"})
    if cookie:
        s.headers["Cookie"] = cookie
    else:
        print("    (未提供 cookie，雪球接口几乎必然失败)")
        try:
            s.get("https://xueqiu.com/", timeout=TIMEOUT)
        except Exception:
            pass
    url = f"https://xueqiu.com/v4/statuses/user_timeline.json?user_id={uid}&page=1"
    try:
        r = s.get(url, timeout=TIMEOUT)
    except Exception as e:
        print(f"    请求异常: {e}")
        return
    print(f"    HTTP {r.status_code}")
    body = r.text.lstrip()
    is_json = body.startswith("{")
    print(f"    返回是 JSON: {'是' if is_json else '否'}")
    if not is_json:
        print(f"    ==> 非 JSON，疑似被反爬（acw_sc）。返回开头: {' '.join(r.text.split())[:160]}")
        return
    data = r.json()
    if data.get("error_code") not in (None, 0, "0"):
        print(f"    ==> error_code={data.get('error_code')} {data.get('error_description','')}"
              f"（cookie 无效/过期）")
        return
    sts = data.get("statuses", [])
    print(f"    抓到 {len(sts)} 条 ✓")
    if sts:
        st = sts[0]
        t = time.strftime("%m-%d %H:%M", time.localtime((st.get("created_at") or 0) / 1000))
        print(f"    最新: {st.get('user',{}).get('screen_name')} | {t} | "
              f"{clean(st.get('text') or st.get('description'))[:50]}")


def main():
    print("=" * 50)
    print("抓取可行性探测")
    print("=" * 50)
    show_exit_ip()

    print("=== 微博 ===")
    wcookie = os.environ.get("WEIBO_COOKIE", "")
    print(f"(cookie: {'已提供' if wcookie else '未提供，先裸抓试试'})")
    wuids = [u.strip() for u in os.environ.get("WEIBO_UIDS", "").split(",") if u.strip()]
    if not wuids:
        print("  未配置 WEIBO_UIDS")
    for uid in wuids:
        probe_weibo(uid, wcookie)
        time.sleep(2)

    print("\n=== 雪球 ===")
    xcookie = os.environ.get("XUEQIU_COOKIE", "")
    print(f"(cookie: {'已提供' if xcookie else '未提供'})")
    xuids = [u.strip() for u in os.environ.get("XUEQIU_UIDS", "").split(",") if u.strip()]
    if not xuids:
        print("  未配置 XUEQIU_UIDS")
    for uid in xuids:
        probe_xueqiu(uid, xcookie)
        time.sleep(2)

    print("\n" + "=" * 50)
    print("探测结束。把上面从头到尾的输出贴回给我即可。")


if __name__ == "__main__":
    main()
