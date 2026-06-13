import yfinance as yf
import requests
from datetime import datetime, timedelta
import json

def collect_market_data():
    data = {"market": {}, "btc": {}, "fear_greed": {}}
    print("📡 시장 데이터 수집 중...")

    # ── 1. yfinance ──────────────────────────────────────────
    tickers = {
        "SP500":   "^GSPC",
        "NASDAQ":  "^NDX",
        "VIX":     "^VIX",
        "GOLD":    "GC=F",
        "WTI":     "CL=F",
        "KOSPI":   "^KS11",
        "KOSDAQ":  "^KQ11",
        "USDKRW":  "KRW=X",
        "USDJPY":  "JPY=X",
        "TNX":     "^TNX",
    }

    for key, symbol in tickers.items():
        try:
            t    = yf.Ticker(symbol)
            info = t.fast_info
            close      = round(info["last_price"], 2)
            prev_close = round(info["previous_close"], 2)
            change     = round(close - prev_close, 2)
            change_pct = round((change / prev_close) * 100, 2)
            data["market"][key] = {
                "close":      close,
                "prev_close": prev_close,
                "change":     change,
                "change_pct": change_pct,
                "direction":  "up" if change >= 0 else "down"
            }
            print(f"  ✅ {key}: {close} ({change_pct:+.2f}%)")
        except Exception as e:
            print(f"  ❌ {key} 실패: {e}")
            data["market"][key] = {"error": str(e)}

    # ── 2. 비트코인 (CoinGecko) ──────────────────────────────
    try:
        r   = requests.get(
            "https://api.coingecko.com/api/v3/coins/bitcoin"
            "?localization=false&tickers=false&market_data=true"
            "&community_data=false&developer_data=false",
            timeout=10
        )
        md  = r.json()["market_data"]
        krw = md["current_price"]["krw"]
        usd = md["current_price"]["usd"]
        ch  = round(md["price_change_percentage_24h"], 2)
        prev_krw = round(krw / (1 + ch / 100))

        # 7일 고점
        try:
            hist = yf.Ticker("BTC-KRW").history(period="7d")
            high_7d = int(hist["High"].max()) if not hist.empty else 0
        except:
            high_7d = 0

        data["btc"] = {
            "krw":          krw,
            "usd":          usd,
            "change_24h":   ch,
            "change_30d":   round(md["price_change_percentage_30d"], 2),
            "high_24h_krw": md["high_24h"]["krw"],
            "low_24h_krw":  md["low_24h"]["krw"],
            "high_7d_krw":  high_7d,
            "ath_krw":      md["ath"]["krw"],
            "ath_usd":      md["ath"]["usd"],
            "ath_change":   round(md["ath_change_percentage"]["krw"], 2),
            "prev_krw":     prev_krw,
            "direction":    "up" if ch >= 0 else "down"
        }
        print(f"  ✅ BTC: ₩{krw:,} ({ch:+.2f}%)")
    except Exception as e:
        print(f"  ❌ BTC 실패: {e}")
        data["btc"] = {"error": str(e)}

    # ── 3. 크립토 공포탐욕 (alternative.me) ──────────────────
    try:
        r   = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
        fng = r.json()["data"][0]
        data["fear_greed"]["crypto_value"] = int(fng["value"])
        data["fear_greed"]["crypto_label"] = fng["value_classification"]
        print(f"  ✅ 크립토 공포탐욕: {fng['value']} ({fng['value_classification']})")
    except Exception as e:
        print(f"  ❌ 크립토 공포탐욕 실패: {e}")
        data["fear_greed"]["crypto_value"] = None
        data["fear_greed"]["error"] = str(e)

    return data


if __name__ == "__main__":
    data = collect_market_data()
    print("\n" + json.dumps(data, ensure_ascii=False, indent=2))
