"""第 1 步 · 在家里的国内电脑上验证抓取

和之前 GitHub 上跑的那个探测是一回事，只是参数改成直接填在下面，
不用配环境变量。在家里那台电脑上：
    pip install requests beautifulsoup4
    python probe_local.py
把从头到尾的输出贴回来即可。
"""

# ============ 只需改这里 ============
WEIBO_UIDS = ["1216826604", "3962719063"]   # 你的微博 uid，可多个
WEIBO_COOKIE = ""                            # 先空着裸抓；不行再填

XUEQIU_UIDS = ["9742512811", "9887656769"]   # 你的雪球 uid，可多个
XUEQIU_COOKIE = "在这里粘贴雪球cookie整串"   # 雪球必须填（含 xq_a_token）
# ===================================

import time
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
    try:
        d = requests.get("https://ipinfo.io/json", timeout=TIMEOUT).json()
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
    is_json = r.text.lstrip().startswith("{")
    print(f"    返回是 JSON: {'是' if is_json else '否'}")
    if not is_json:
        print(f"    ==> 非 JSON，疑似被反爬/需登录。返回开头: {' '.join(r.text.split())[:160]}")
        return
    data = r.json()
    if data.get("ok") != 1:
        print(f"    ==> ok={data.get('ok')}，接口未正常返回（海外 IP 常见；国内 IP 若仍这样可试着填 cookie）")
        return
    cards = [c for c in data.get("data", {}).get("cards", []) if c.get("card_type") == 9]
    print(f"    抓到 {len(cards)} 条 \u2713")
    if cards:
        m = cards[0]["mblog"]
        print(f"    最新: {m.get('user',{}).get('screen_name')} | {m.get('created_at')} | {clean(m.get('text'))[:50]}")


def probe_xueqiu(uid, cookie):
    print(f"  账号 {uid}:")
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Referer": "https://xueqiu.com/",
                      "Accept": "application/json, text/plain, */*"})
    if cookie and cookie != "在这里粘贴雪球cookie整串":
        s.headers["Cookie"] = cookie
    else:
        print("    (没填有效 cookie，雪球几乎必然失败)")
    url = f"https://xueqiu.com/v4/statuses/user_timeline.json?user_id={uid}&page=1"
    try:
        r = s.get(url, timeout=TIMEOUT)
    except Exception as e:
        print(f"    请求异常: {e}")
        return
    print(f"    HTTP {r.status_code}")
    is_json = r.text.lstrip().startswith("{")
    print(f"    返回是 JSON: {'是' if is_json else '否'}")
    if not is_json:
        print(f"    ==> 非 JSON，被 WAF/反爬拦。返回开头: {' '.join(r.text.split())[:160]}")
        return
    data = r.json()
    if data.get("error_code") not in (None, 0, "0"):
        print(f"    ==> error_code={data.get('error_code')} {data.get('error_description','')}（cookie 无效/过期）")
        return
    sts = data.get("statuses", [])
    print(f"    抓到 {len(sts)} 条 \u2713")
    if sts:
        st = sts[0]
        t = time.strftime("%m-%d %H:%M", time.localtime((st.get("created_at") or 0) / 1000))
        print(f"    最新: {st.get('user',{}).get('screen_name')} | {t} | {clean(st.get('text') or st.get('description'))[:50]}")


def main():
    print("=" * 50)
    print("抓取可行性探测（国内电脑版）")
    print("=" * 50)
    show_exit_ip()

    print("=== 微博 ===")
    print(f"(cookie: {'已提供' if WEIBO_COOKIE else '未提供，先裸抓试试'})")
    for uid in WEIBO_UIDS:
        probe_weibo(uid, WEIBO_COOKIE)
        time.sleep(2)

    print("\n=== 雪球 ===")
    print(f"(cookie: {'已提供' if XUEQIU_COOKIE and XUEQIU_COOKIE != '在这里粘贴雪球cookie整串' else '未提供'})")
    for uid in XUEQIU_UIDS:
        probe_xueqiu(uid, XUEQIU_COOKIE)
        time.sleep(2)

    print("\n" + "=" * 50)
    print("探测结束。把上面从头到尾的输出贴回给我即可。")


if __name__ == "__main__":
    main()
