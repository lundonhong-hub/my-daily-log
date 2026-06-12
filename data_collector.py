import yfinance as yf
import requests
from datetime import datetime
import json

def collect_market_data():
    data = {}
    today = datetime.now().strftime("%Y-%m-%d")

    print("📡 시장 데이터 수집 중...")

    # ── 1. yfinance ──────────────────────────────
    tickers = {
        "SP500":   "^GSPC",
        "NASDAQ":  "^NDX",
        "VIX":     "^VIX",
        "GOLD":    "GC=F",
        "WTI":     "CL=F",
        "KOSPI":   "^KS11",
        "USDKRW":  "KRW=X",
        "US10Y":   "^TNX",
    }

    for key, symbol in tickers.items():
        try:
            t = yf.Ticker(symbol)
            info = t.fast_info
            price = round(info["last_price"], 2)
            prev  = round(info["previous_close"], 2)
            chg   = round(price - prev, 2)
            chg_pct = round((chg / prev) * 100, 2)
            data[key] = {
                "price": price,
                "prev_close": prev,
                "change": chg,
                "change_pct": chg_pct,
                "direction": "up" if chg >= 0 else "down"
            }
            print(f"  ✅ {key}: {price} ({chg_pct:+.2f}%)")
        except Exception as e:
            print(f"  ❌ {key} 실패: {e}")
            data[key] = None

    # ── 2. 비트코인 (CoinGecko) ──────────────────
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/coins/bitcoin?localization=false"
            "&tickers=false&market_data=true&community_data=false&developer_data=false",
            timeout=10
        )
        btc = r.json()["market_data"]
        data["BTC"] = {
            "price_krw":    btc["current_price"]["krw"],
            "price_usd":    btc["current_price"]["usd"],
            "change_24h":   round(btc["price_change_percentage_24h"], 2),
            "change_30d":   round(btc["price_change_percentage_30d"], 2),
            "ath_krw":      btc["ath"]["krw"],
            "ath_usd":      btc["ath"]["usd"],
            "high_24h_krw": btc["high_24h"]["krw"],
            "low_24h_krw":  btc["low_24h"]["krw"],
            "direction":    "up" if btc["price_change_percentage_24h"] >= 0 else "down"
        }
        print(f"  ✅ BTC: ₩{data['BTC']['price_krw']:,} ({data['BTC']['change_24h']:+.2f}%)")
    except Exception as e:
        print(f"  ❌ BTC 실패: {e}")
        data["BTC"] = None

    # ── 3. 크립토 공포탐욕 (alternative.me) ──────
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
        fng = r.json()["data"][0]
        data["CRYPTO_FNG"] = {
            "value":       int(fng["value"]),
            "label":       fng["value_classification"],
            "direction":   "up" if int(fng["value"]) >= 50 else "down"
        }
        print(f"  ✅ 크립토 공포탐욕: {data['CRYPTO_FNG']['value']} ({data['CRYPTO_FNG']['label']})")
    except Exception as e:
        print(f"  ❌ 크립토 공포탐욕 실패: {e}")
        data["CRYPTO_FNG"] = None

    return data


def format_for_prompt(data):
    """수집된 데이터를 프롬프트 주입용 문자열로 변환"""
    lines = ["[사전 수집된 실제 시장 데이터 — 아래 수치를 그대로 사용할 것. 절대 검색으로 대체하지 말 것]\n"]

    def fmt(key, label):
        d = data.get(key)
        if not d:
            return f"{label}: 데이터 없음"
        sign = "▲" if d["direction"] == "up" else "▼"
        return f"{label}: {d['price']} ({sign} {d['change_pct']:+.2f}%, 전일 {d['prev_close']})"

    if data.get("SP500"):
        lines.append(fmt("SP500",  "S&P 500"))
    if data.get("NASDAQ"):
        lines.append(fmt("NASDAQ", "나스닥 100"))
    if data.get("VIX"):
        lines.append(fmt("VIX",    "VIX 공포지수"))
    if data.get("GOLD"):
        d = data["GOLD"]
        lines.append(f"금 (Gold): ${d['price']} ({'▲' if d['direction']=='up' else '▼'} {d['change_pct']:+.2f}%)")
    if data.get("WTI"):
        d = data["WTI"]
        lines.append(f"WTI 유가: ${d['price']} ({'▲' if d['direction']=='up' else '▼'} {d['change_pct']:+.2f}%)")
    if data.get("KOSPI"):
        lines.append(fmt("KOSPI",  "KOSPI"))
    if data.get("USDKRW"):
        d = data["USDKRW"]
        lines.append(f"USD/KRW: {d['price']}원 ({'▲' if d['direction']=='up' else '▼'} {d['change_pct']:+.2f}%)")
    if data.get("US10Y"):
        d = data["US10Y"]
        lines.append(f"미국 10년물 금리: {d['price']}%")
    if data.get("BTC"):
        b = data["BTC"]
        lines.append(f"비트코인(KRW): ₩{b['price_krw']:,} ({'▲' if b['direction']=='up' else '▼'} {b['change_24h']:+.2f}%)")
        lines.append(f"비트코인(USD): ${b['price_usd']:,}")
        lines.append(f"BTC 24h 고점: ₩{b['high_24h_krw']:,} / 저점: ₩{b['low_24h_krw']:,}")
        lines.append(f"BTC ATH(KRW): ₩{b['ath_krw']:,} / ATH(USD): ${b['ath_usd']:,}")
        lines.append(f"BTC 30일 변동: {b['change_30d']:+.2f}%")
    if data.get("CRYPTO_FNG"):
        c = data["CRYPTO_FNG"]
        lines.append(f"크립토 공포탐욕: {c['value']} ({c['label']})")

    return "\n".join(lines)


if __name__ == "__main__":
    data = collect_market_data()
    print("\n" + format_for_prompt(data))
