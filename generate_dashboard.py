import anthropic
import os
import json
import requests
from datetime import datetime, timedelta
import time

# ─────────────────────────────────────────
# 환경변수
# ─────────────────────────────────────────
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
filename = os.environ["FILENAME"]
today = os.environ["TODAY"]
update_time = os.environ.get("UPDATE_TIME", "")

# ─────────────────────────────────────────
# 1. yfinance로 시장 데이터 수집 (무료, 무제한)
# ─────────────────────────────────────────
def fetch_market_data():
    try:
        import yfinance as yf
    except ImportError:
        print("yfinance 미설치 → pip install yfinance")
        return {}

    data = {}
    symbols = {
        "SP500":   "^GSPC",
        "NASDAQ":  "^NDX",
        "VIX":     "^VIX",
        "GOLD":    "GC=F",
        "WTI":     "CL=F",
        "KOSPI":   "^KS11",
        "USDKRW":  "KRW=X",
        "TNX":     "^TNX",   # 10년물 금리
    }

    print("📊 yfinance 시장 데이터 수집 중...")
    for name, sym in symbols.items():
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="5d", interval="1d")
            if hist.empty:
                data[name] = {"error": "데이터 없음"}
                continue
            latest = hist.iloc[-1]
            prev   = hist.iloc[-2] if len(hist) >= 2 else hist.iloc[-1]
            close  = round(float(latest["Close"]), 2)
            prev_close = round(float(prev["Close"]), 2)
            change_pct = round((close - prev_close) / prev_close * 100, 2)
            data[name] = {
                "close": close,
                "prev_close": prev_close,
                "change_pct": change_pct,
                "high": round(float(latest.get("High", close)), 2),
                "low":  round(float(latest.get("Low",  close)), 2),
            }
            print(f"  ✅ {name}: {close} ({change_pct:+.2f}%)")
            time.sleep(0.3)
        except Exception as e:
            print(f"  ⚠️ {name} 오류: {e}")
            data[name] = {"error": str(e)}

    return data


# ─────────────────────────────────────────
# 2. CoinGecko API로 BTC 데이터 수집 (무료, 키 불필요)
# ─────────────────────────────────────────
def fetch_btc_data(usdkrw_rate=1400):
    print("₿ CoinGecko BTC 데이터 수집 중...")
    btc = {}
    try:
        # 현재가 + ATH + 24h 고저
        url = "https://api.coingecko.com/api/v3/coins/bitcoin?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false"
        r = requests.get(url, timeout=10)
        d = r.json()["market_data"]

        btc["usd"]          = d["current_price"]["usd"]
        btc["krw"]          = d["current_price"]["krw"]
        btc["change_24h"]   = round(d["price_change_percentage_24h"], 2)
        btc["change_30d"]   = round(d.get("price_change_percentage_30d", 0), 2)
        btc["high_24h_krw"] = d["high_24h"]["krw"]
        btc["low_24h_krw"]  = d["low_24h"]["krw"]
        btc["ath_krw"]      = d["ath"]["krw"]
        btc["ath_change"]   = round(d["ath_change_percentage"]["krw"], 2)
        btc["prev_krw"]     = round(btc["krw"] / (1 + btc["change_24h"] / 100))

        # 7일 고점 (별도 호출)
        hist_url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=krw&days=7&interval=daily"
        r2 = requests.get(hist_url, timeout=10)
        prices_7d = [p[1] for p in r2.json().get("prices", [])]
        btc["high_7d_krw"] = int(max(prices_7d)) if prices_7d else btc["krw"]

        print(f"  ✅ BTC: ₩{btc['krw']:,} ({btc['change_24h']:+.2f}%)")
    except Exception as e:
        print(f"  ⚠️ BTC 오류: {e}")
        btc["error"] = str(e)

    return btc


# ─────────────────────────────────────────
# 3. 공포탐욕지수 수집 (Alternative.me — 무료)
# ─────────────────────────────────────────
def fetch_fear_greed():
    print("😨 공포탐욕지수 수집 중...")
    fg = {}
    try:
        # 크립토 공포탐욕 (Alternative.me)
        r = requests.get("https://api.alternative.me/fng/?limit=2", timeout=10)
        data = r.json()["data"]
        fg["crypto_value"]      = int(data[0]["value"])
        fg["crypto_label"]      = data[0]["value_classification"]
        fg["crypto_prev_value"] = int(data[1]["value"]) if len(data) > 1 else fg["crypto_value"]
        print(f"  ✅ 크립토 F&G: {fg['crypto_value']} ({fg['crypto_label']})")
    except Exception as e:
        print(f"  ⚠️ 크립토 F&G 오류: {e}")
        fg["crypto_error"] = str(e)

    # CNN 공포탐욕은 공식 무료 API 없음 → Claude 웹검색 1회로 처리
    fg["cnn_note"] = "CNN Fear&Greed: Claude 웹검색으로 수집"
    return fg


# ─────────────────────────────────────────
# 메인 실행
# ─────────────────────────────────────────
print(f"🚀 대시보드 생성 시작: {today}")

market = fetch_market_data()
btc    = fetch_btc_data(
    usdkrw_rate=market.get("USDKRW", {}).get("close", 1400)
)
fg     = fetch_fear_greed()

# ─────────────────────────────────────────
# 4. 수집 데이터를 JSON으로 정리해서 Claude에게 전달
# ─────────────────────────────────────────
market_json = json.dumps({
    "date": today,
    "market": market,
    "btc": btc,
    "fear_greed": fg
}, ensure_ascii=False, indent=2)

print(f"\n📦 수집 완료. Claude API 호출 중...")

# ─────────────────────────────────────────
# 5. prompt_template.md 로드 + SPLIT 분리
# ─────────────────────────────────────────
with open("prompt_template.md", "r", encoding="utf-8") as f:
    full_prompt = f.read()

if "[SPLIT]" in full_prompt:
    parts = full_prompt.split("[SPLIT]", 1)
    system_content = parts[0].strip()
    user_template  = parts[1].strip()
else:
    system_content = None
    user_template  = full_prompt

# user 파트: 날짜 치환 + 수집 데이터 삽입
user_content = user_template.replace("[[TODAY]]", today)
user_content = user_content.replace(
    "[[MARKET_DATA_JSON]]",
    f"```json\n{market_json}\n```"
)

# ─────────────────────────────────────────
# 6. Claude API 호출 (캐싱 적용, 웹검색 1회만 허용)
# ─────────────────────────────────────────
system_param = None
if system_content:
    system_param = [
        {
            "type": "text",
            "text": system_content,
            "cache_control": {"type": "ephemeral"}
        }
    ]

messages = [{"role": "user", "content": user_content}]

max_turns = 6   # 웹검색은 CNN F&G + 뉴스 + 경제캘린더 최대 3회
search_count = 0
turn = 0

while turn < max_turns:
    turn += 1

    kwargs = dict(
        model="claude-sonnet-4-6",
        max_tokens=16000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=messages
    )
    if system_param:
        kwargs["system"] = system_param

    response = client.messages.create(**kwargs)

    usage     = response.usage
    cache_hit = getattr(usage, "cache_read_input_tokens", 0)
    print(f"  턴 {turn} | stop: {response.stop_reason} | input: {usage.input_tokens} | output: {usage.output_tokens} | 캐시hit: {cache_hit}")

    messages.append({"role": "assistant", "content": response.content})

    if response.stop_reason == "end_turn":
        break

    if response.stop_reason == "tool_use":
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                search_count += 1
                print(f"  🔍 검색 #{search_count}: {getattr(block, 'input', {}).get('query', '')}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": "검색 완료"
                })
        if tool_results:
            messages.append({"role": "user", "content": tool_results})
        continue

    break

print(f"\n✅ 총 웹검색 {search_count}회 사용")

# ─────────────────────────────────────────
# 7. HTML 추출
# ─────────────────────────────────────────
html = ""
for block in response.content:
    if hasattr(block, "text") and block.text:
        html += block.text

if len(html) < 500:
    print("경고: HTML 짧음. 전체 메시지 재탐색...")
    for msg in reversed(messages):
        if msg["role"] == "assistant":
            content = msg["content"]
            if isinstance(content, list):
                for block in content:
                    if hasattr(block, "text") and block.text and len(block.text) > 500:
                        html = block.text
                        break
            if len(html) > 500:
                break

# 마크다운 코드블록 제거
html = html.strip()
if html.startswith("```"):
    html = html[html.find("\n")+1:]
if html.endswith("```"):
    html = html[:html.rfind("```")]

if "<!DOCTYPE" in html:
    html = html[html.index("<!DOCTYPE"):]
elif "<!doctype" in html.lower():
    html = html[html.lower().index("<!doctype"):]

if "</html>" in html:
    html = html[:html.index("</html>") + 7]

# 업데이트 타임스탬프 삽입
timestamp_html = (
    f'<div style="text-align:right; color:#8b949e; padding:6px 20px 0; '
    f'font-size:0.75rem;">⏱ 최종 업데이트: {update_time} KST</div>'
)
if "<body>" in html:
    html = html.replace("<body>", f"<body>\n{timestamp_html}", 1)

with open(filename, "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ 완료: {filename} ({len(html)}자)")
