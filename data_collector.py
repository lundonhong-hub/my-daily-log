import yfinance as yf
import requests
from datetime import datetime
import json
import os

def collect_market_data():
    data = {"market": {}, "btc": {}, "fear_greed": {}}
    print("📡 시장 데이터 수집 중...")

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
            t          = yf.Ticker(symbol)
            info       = t.fast_info
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

    try:
        r  = requests.get(
            "https://api.coingecko.com/api/v3/coins/bitcoin"
            "?localization=false&tickers=false&market_data=true"
            "&community_data=false&developer_data=false",
            timeout=10
        )
        md      = r.json()["market_data"]
        krw     = md["current_price"]["krw"]
        usd     = md["current_price"]["usd"]
        ch      = round(md["price_change_percentage_24h"], 2)
        prev_krw = round(krw / (1 + ch / 100))
        try:
            hist   = yf.Ticker("BTC-KRW").history(period="7d")
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


def normalize_ticker(ticker_raw):
    """티커 정규화 — .ks/.KS 이미 붙은 경우 포함"""
    ticker = str(ticker_raw).strip()
    upper  = ticker.upper()
    # 이미 .KS / .KQ 붙어있으면 그대로
    if upper.endswith(".KS") or upper.endswith(".KQ"):
        return upper, "KRW"
    # 6자리 앞4자리 숫자 → 한국 종목 (476160, 0204D0 등)
    if len(ticker) == 6 and ticker[:4].isdigit():
        return upper + ".KS", "KRW"
    # 순수 숫자 → 한국 종목
    if ticker.isdigit():
        return ticker.zfill(6) + ".KS", "KRW"
    # 영문 → 미국 종목
    return upper, "USD"


def get_price_kr(code):
    """한국 종목 현재가 — pykrx 사용"""
    try:
        from pykrx import stock
        today = datetime.now().strftime("%Y%m%d")
        df = stock.get_market_ohlcv(today, ticker=code)
        if df is not None and not df.empty:
            return float(df["종가"].iloc[-1])
        # 오늘 데이터 없으면 최근 5일
        from datetime import timedelta
        start = (datetime.now() - timedelta(days=5)).strftime("%Y%m%d")
        df = stock.get_market_ohlcv(start, today, ticker=code)
        if df is not None and not df.empty:
            return float(df["종가"].iloc[-1])
    except Exception as e:
        print(f"    pykrx 실패 ({code}): {e}")
    return None


def get_price_us(ticker):
    """미국 종목 현재가 — yfinance 사용"""
    try:
        price = yf.Ticker(ticker).fast_info["last_price"]
        if price and price > 0:
            return float(price)
    except Exception:
        pass
    try:
        hist = yf.Ticker(ticker).history(period="2d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return None


def collect_portfolio_data(sheet_id):
    """구글 시트에서 포트폴리오 읽어서 현재가·수익률 계산"""
    print("📋 포트폴리오 데이터 수집 중...")

    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    try:
        r = requests.get(url, timeout=15)
        r.encoding = "utf-8"
        lines   = r.text.strip().split("\n")
        headers = [h.strip() for h in lines[0].split(",")]
        rows    = []
        for line in lines[1:]:
            vals = [v.strip() for v in line.split(",")]
            if len(vals) >= 5 and vals[0]:
                rows.append(dict(zip(headers, vals)))
        print(f"  ✅ 시트 로드: {len(rows)}개 종목")
    except Exception as e:
        print(f"  ❌ 시트 로드 실패: {e}")
        return {"error": str(e)}

    # USD/KRW 환율
    try:
        usdkrw = float(yf.Ticker("KRW=X").fast_info["last_price"])
    except:
        usdkrw = 1380.0

    holdings        = []
    account_summary = {}
    total_value_krw = 0
    total_cost_krw  = 0

    for row in rows:
        try:
            account    = row.get("계좌", "")
            name       = row.get("종목명", "")
            ticker_raw = row.get("티커", "")
            shares     = int(str(row.get("수량", 0)).replace(",", ""))
            avg_price  = float(str(row.get("매수평균가", 0)).replace(",", ""))

            ticker, currency = normalize_ticker(ticker_raw)

            # 통화별 시세 조회
            if currency == "KRW":
                kr_code = ticker.replace(".KS", "").replace(".KQ", "")
                price   = get_price_kr(kr_code)
                if price is None:
                    price = avg_price
                    print(f"  ⚠️ {name} pykrx 실패 → 매수평균가 사용")
                else:
                    print(f"  ✅ {name}: ₩{price:,.0f}")
            else:
                price = get_price_us(ticker)
                if price is None:
                    price = avg_price
                    print(f"  ⚠️ {name} yfinance 실패 → 매수평균가 사용")
                else:
                    print(f"  ✅ {name}: ${price:,.2f}")

            # 원화 환산
            if currency == "USD":
                value_krw = round(price * shares * usdkrw)
                cost_krw  = round(avg_price * shares * usdkrw)
                price_krw = round(price * usdkrw)
            else:
                value_krw = round(price * shares)
                cost_krw  = round(avg_price * shares)
                price_krw = round(price)

            gain_krw  = value_krw - cost_krw
            gain_pct  = round((gain_krw / cost_krw) * 100, 2) if cost_krw > 0 else 0
            direction = "up" if gain_pct >= 0 else "down"

            holding = {
                "account":   account,
                "name":      name,
                "ticker":    ticker,
                "currency":  currency,
                "shares":    shares,
                "avg_price": avg_price,
                "cur_price": round(price, 2),
                "price_krw": price_krw,
                "value_krw": value_krw,
                "cost_krw":  cost_krw,
                "gain_krw":  gain_krw,
                "gain_pct":  gain_pct,
                "direction": direction,
            }
            holdings.append(holding)

            if account not in account_summary:
                account_summary[account] = {"value_krw": 0, "cost_krw": 0, "holdings": []}
            account_summary[account]["value_krw"] += value_krw
            account_summary[account]["cost_krw"]  += cost_krw
            account_summary[account]["holdings"].append(name)

            total_value_krw += value_krw
            total_cost_krw  += cost_krw

        except Exception as e:
            print(f"  ❌ {row.get('종목명','?')} 실패: {e}")
            holdings.append({"name": row.get("종목명", "?"), "error": str(e)})

    for acc in account_summary:
        v = account_summary[acc]["value_krw"]
        c = account_summary[acc]["cost_krw"]
        account_summary[acc]["gain_krw"] = v - c
        account_summary[acc]["gain_pct"] = round(((v - c) / c) * 100, 2) if c > 0 else 0

    total_gain_krw = total_value_krw - total_cost_krw
    total_gain_pct = round((total_gain_krw / total_cost_krw) * 100, 2) if total_cost_krw > 0 else 0

    loss_positions  = [h for h in holdings if "gain_pct" in h and h["gain_pct"] < -5]
    watch_positions = [h for h in holdings if "gain_pct" in h and h["gain_pct"] > 50]

    return {
        "holdings":        holdings,
        "account_summary": account_summary,
        "total_value_krw": total_value_krw,
        "total_cost_krw":  total_cost_krw,
        "total_gain_krw":  total_gain_krw,
        "total_gain_pct":  total_gain_pct,
        "loss_positions":  loss_positions,
        "watch_positions": watch_positions,
        "usdkrw":          round(usdkrw, 2),
        "updated_at":      datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


if __name__ == "__main__":
    data = collect_market_data()
    print("\n" + json.dumps(data, ensure_ascii=False, indent=2))
    sheet_id = os.environ.get("PORTFOLIO_SHEET_ID", "")
    if sheet_id:
        portfolio = collect_portfolio_data(sheet_id)
        print("\n" + json.dumps(portfolio, ensure_ascii=False, indent=2))
