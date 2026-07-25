# -*- coding: utf-8 -*-
"""
data_collector.py  (재작성판)

설계 원칙
  1) 판단과 계산은 전부 여기서 한다. LLM에는 '계산이 끝난 값'만 넘긴다.
  2) 조회 실패 시 절대 대체값을 쓰지 않는다. None을 유지해서 화면에 '조회실패'로 노출한다.
     (구 버전은 시세 실패 시 매수평균가를 넣어 수익률 0.0%로 위장했다)
  3) 모든 임계값은 THRESHOLDS 한 곳에 모은다. 튜닝은 여기만 고친다.
  4) 시각은 전부 KST 명시. datetime.now() 맨몸 호출 금지.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, date
from zoneinfo import ZoneInfo

import requests

KST = ZoneInfo("Asia/Seoul")

# ──────────────────────────────────────────────────────────────
# 임계값 — 리스크 판정·알림 생성의 모든 기준. Haiku는 이 판단에 관여하지 않는다.
# ──────────────────────────────────────────────────────────────
THRESHOLDS = {
    # 변동성
    "vix_red":               30.0,   # 이상이면 위험
    "vix_yellow":            20.0,   # 이상이면 경계
    # 심리
    "fng_extreme_fear":      25,     # 이하 극도공포
    "fng_fear":              45,     # 이하 공포
    "fng_greed":             75,     # 이상 탐욕(과열)
    # 지수 일간 등락
    "idx_drop_red":          -2.0,
    "idx_drop_yellow":       -1.0,
    "idx_surge_yellow":       2.0,
    # 20일 이격도
    "disparity_low":         95.0,   # 이하 = 단기 과매도
    "disparity_high":       105.0,   # 이상 = 단기 과열
    # 환율
    "usdkrw_red":          1450.0,
    "usdkrw_yellow":       1400.0,
    # 미 10년물
    "tnx_red":                5.0,
    "tnx_yellow":             4.5,
    # 유가
    "wti_red":               95.0,
    "wti_yellow":            85.0,
    # 외국인 수급 임계값은 pykrx 인증 문제로 제외 (아래 3절 참고)
    # BTC
    "btc_ath_gap_yellow":   -40.0,
    # 52주 위치(%)
    "w52_low_zone":          20.0,
    "w52_high_zone":         95.0,
    # 카드에 한 줄 코멘트를 붙일 최소 변동폭
    "move_report_pct":        1.5,
}

TICKERS = {
    "SP500":  "^GSPC",
    "NASDAQ": "^NDX",
    "VIX":    "^VIX",
    "GOLD":   "GC=F",
    "WTI":    "CL=F",
    "KOSPI":  "^KS11",
    "KOSDAQ": "^KQ11",
    "USDKRW": "KRW=X",
    "USDJPY": "JPY=X",
    "TNX":    "^TNX",
}

WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]


# ──────────────────────────────────────────────────────────────
# 공용 헬퍼
# ──────────────────────────────────────────────────────────────
def now_kst() -> datetime:
    return datetime.now(KST)


def fmt_date_label(d: date) -> str:
    """2026년 7월 27일 (월) — 요일을 파이썬이 계산한다. LLM에게 절대 맡기지 않는다."""
    return f"{d.year}년 {d.month}월 {d.day}일 ({WEEKDAY_KR[d.weekday()]})"


def fmt_md_weekday(d: date) -> str:
    """7월 28일 (화)"""
    return f"{d.month}월 {d.day}일 ({WEEKDAY_KR[d.weekday()]})"


def direction_of(pct):
    """등락률 → 방향/CSS클래스/화살표. 렌더러가 이 값을 그대로 쓴다."""
    if pct is None:
        return {"direction": "na", "cls": "neutral", "arrow": "—"}
    if pct > 0:
        return {"direction": "up", "cls": "up", "arrow": "▲"}
    if pct < 0:
        return {"direction": "down", "cls": "down", "arrow": "▼"}
    return {"direction": "flat", "cls": "neutral", "arrow": "—"}


def _r(v, n=2):
    return None if v is None else round(float(v), n)


# ──────────────────────────────────────────────────────────────
# 1. 시장 지표 — 52주 위치·20일 이격도까지 여기서 계산
# ──────────────────────────────────────────────────────────────
def _fetch_hist(symbol):
    """1y(파생지표용) + 5d(최신성 확보용)를 병합한다.

    period='1y' 단독 호출은 야후가 최근 세션을 아직 채우지 않은 경우가 있어
    하루 뒤처진 종가를 그대로 쓰게 된다(2026-07-25 실행에서 KOSPI가 7/23에 멈춘 사고).
    짧은 구간은 갱신이 빠르므로 둘을 합치고 같은 날짜는 5d 쪽을 우선한다.
    """
    import pandas as pd
    import yfinance as yf

    t = yf.Ticker(symbol)
    frames = []
    for period in ("1y", "5d"):
        try:
            h = t.history(period=period, auto_adjust=False)
            if h is not None and not h.empty:
                frames.append(h)
        except Exception:
            pass
    if not frames:
        return None
    hist = pd.concat(frames).sort_index()
    hist = hist[~hist.index.duplicated(keep="last")]   # 같은 날짜는 5d(뒤) 우선
    return hist


def collect_market() -> dict:
    out = {}
    print("시장 데이터 수집")
    for key, symbol in TICKERS.items():
        try:
            hist = _fetch_hist(symbol)
            if hist is None or hist.empty or len(hist) < 2:
                raise ValueError("빈 시계열")

            closes = hist["Close"].dropna()
            close = float(closes.iloc[-1])
            prev = float(closes.iloc[-2])
            change = close - prev
            change_pct = (change / prev * 100) if prev else None

            w52_high = float(hist["High"].max())
            w52_low = float(hist["Low"].min())
            span = w52_high - w52_low
            w52_pos = ((close - w52_low) / span * 100) if span else None

            ma20 = float(closes.tail(20).mean()) if len(closes) >= 20 else None
            ma60 = float(closes.tail(60).mean()) if len(closes) >= 60 else None
            disparity20 = (close / ma20 * 100) if ma20 else None

            rec = {
                "close":       _r(close),
                "prev_close":  _r(prev),
                "change":      _r(change),
                "change_pct":  _r(change_pct),
                "w52_high":    _r(w52_high),
                "w52_low":     _r(w52_low),
                "w52_pos_pct": _r(w52_pos, 1),
                "ma20":        _r(ma20),
                "ma60":        _r(ma60),
                "disparity20": _r(disparity20, 1),
                "asof":        closes.index[-1].strftime("%Y-%m-%d"),
                "prev_asof":   closes.index[-2].strftime("%Y-%m-%d"),
                "ok":          True,
            }
            rec.update(direction_of(rec["change_pct"]))
            out[key] = rec
            print(f"  OK  {key}: {rec['close']} ({rec['change_pct']:+.2f}%) [{rec['asof']}]")
        except Exception as e:
            out[key] = {"ok": False, "error": str(e), **direction_of(None)}
            print(f"  FAIL {key}: {e}")
    return out


# ──────────────────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────
# 2. 비트코인
# ──────────────────────────────────────────────────────────────
def collect_btc() -> dict:
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/coins/bitcoin"
            "?localization=false&tickers=false&market_data=true"
            "&community_data=false&developer_data=false",
            timeout=15,
        )
        r.raise_for_status()
        md = r.json()["market_data"]
        krw = md["current_price"]["krw"]
        ch24 = round(float(md["price_change_percentage_24h"]), 2)
        rec = {
            "ok":           True,
            "krw":          int(krw),
            "usd":          int(md["current_price"]["usd"]),
            "change_24h":   ch24,
            "change_30d":   _r(md.get("price_change_percentage_30d")),
            "high_24h_krw": int(md["high_24h"]["krw"]),
            "low_24h_krw":  int(md["low_24h"]["krw"]),
            "ath_krw":      int(md["ath"]["krw"]),
            "ath_change":   _r(md["ath_change_percentage"]["krw"]),
            "prev_krw":     int(krw / (1 + ch24 / 100)),
        }
        rec.update(direction_of(ch24))
        print(f"  OK  BTC: {rec['krw']:,}원 ({ch24:+.2f}%)")
        return rec
    except Exception as e:
        print(f"  FAIL BTC: {e}")
        return {"ok": False, "error": str(e), **direction_of(None)}


def collect_crypto_fng() -> dict:
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
        r.raise_for_status()
        d = r.json()["data"][0]
        v = int(d["value"])
        return {"ok": True, "value": v, "label": d["value_classification"],
                "cls": "down" if v <= THRESHOLDS["fng_fear"]
                       else ("up" if v >= THRESHOLDS["fng_greed"] else "neutral")}
    except Exception as e:
        print(f"  FAIL 크립토 공포탐욕: {e}")
        return {"ok": False, "error": str(e)}


# ──────────────────────────────────────────────────────────────
# 3. 차트 — S&P500 / 나스닥100 / KOSPI / USD-KRW / WTI 최근 1개월
# ──────────────────────────────────────────────────────────────
CHART_KEYS = ["SP500", "NASDAQ", "KOSPI", "USDKRW", "WTI"]
CHART_LABELS = {"SP500": "S&P 500", "NASDAQ": "나스닥 100", "KOSPI": "KOSPI",
                "USDKRW": "USD/KRW", "WTI": "WTI 원유"}


def collect_chart_series(period: str = "1mo") -> dict:
    """차트용 종가 시계열. 실패한 지표는 ok=False 로 두어 프런트에서 숨긴다."""
    import yfinance as yf

    out = {}
    for key in CHART_KEYS:
        symbol = TICKERS[key]
        try:
            hist = yf.Ticker(symbol).history(period=period, auto_adjust=False)
            closes = hist["Close"].dropna()
            if closes.empty:
                raise ValueError("빈 시계열")
            out[key] = {
                "ok": True,
                "label": CHART_LABELS[key],
                "dates": [d.strftime("%m/%d") for d in closes.index],
                "values": [round(float(v), 2) for v in closes],
            }
            print(f"  OK  차트 {key}: {len(closes)}개 포인트")
        except Exception as e:
            out[key] = {"ok": False, "label": CHART_LABELS[key], "error": str(e)}
            print(f"  FAIL 차트 {key}: {e}")
    return out


# ──────────────────────────────────────────────────────────────
# 4. 리스크 플래그 — 전부 조건문. 서술은 포맷 문자열로 고정.
# ──────────────────────────────────────────────────────────────
def build_risk_flags(market: dict, btc: dict, fng: dict) -> dict:
    T = THRESHOLDS
    flags = []

    def add(level, label, desc):
        flags.append({"level": level, "label": label, "desc": desc})

    def g(key, field="close"):
        rec = market.get(key, {})
        return rec.get(field) if rec.get("ok") else None

    # VIX
    v = g("VIX")
    if v is not None:
        if v >= T["vix_red"]:
            add("red", "변동성 위험구간", f"VIX {v} · {T['vix_red']} 이상 = 패닉 구간")
        elif v >= T["vix_yellow"]:
            add("yellow", "변동성 경계", f"VIX {v} · {T['vix_yellow']}~{T['vix_red']} 경계 밴드")
        else:
            add("green", "변동성 안정", f"VIX {v} · {T['vix_yellow']} 미만 정상범주")

    # 크립토 심리
    if fng.get("ok"):
        v = fng["value"]
        if v <= T["fng_extreme_fear"]:
            add("red", "크립토 극도공포", f"공포탐욕 {v} · {T['fng_extreme_fear']} 이하")
        elif v >= T["fng_greed"]:
            add("yellow", "크립토 과열", f"공포탐욕 {v} · {T['fng_greed']} 이상")
        else:
            add("green", "크립토 심리 중립", f"공포탐욕 {v}")

    # 지수 일간 급락
    for key, name in (("SP500", "S&P500"), ("KOSPI", "KOSPI")):
        p = g(key, "change_pct")
        if p is None:
            continue
        if p <= T["idx_drop_red"]:
            add("red", f"{name} 급락", f"{p:+.2f}% · {T['idx_drop_red']}% 이하 급락")
        elif p <= T["idx_drop_yellow"]:
            add("yellow", f"{name} 약세", f"{p:+.2f}%")
        elif p >= T["idx_surge_yellow"]:
            add("yellow", f"{name} 급등", f"{p:+.2f}% · 단기 과열 확인 필요")

    # KOSPI 이격도
    d = g("KOSPI", "disparity20")
    if d is not None:
        if d <= T["disparity_low"]:
            add("yellow", "KOSPI 단기 과매도", f"20일 이격도 {d} · {T['disparity_low']} 이하")
        elif d >= T["disparity_high"]:
            add("yellow", "KOSPI 단기 과열", f"20일 이격도 {d} · {T['disparity_high']} 이상")
        else:
            add("green", "KOSPI 이격도 정상", f"20일 이격도 {d}")

    # 환율
    fx = g("USDKRW")
    if fx is not None:
        if fx >= T["usdkrw_red"]:
            add("red", "원화 약세 위험", f"USD/KRW {fx:,.2f} · {T['usdkrw_red']:,.0f} 이상")
        elif fx >= T["usdkrw_yellow"]:
            add("yellow", "원화 약세 경계", f"USD/KRW {fx:,.2f}")
        else:
            add("green", "환율 안정", f"USD/KRW {fx:,.2f}")

    # 미 10년물
    t = g("TNX")
    if t is not None:
        if t >= T["tnx_red"]:
            add("red", "장기금리 급등", f"US 10Y {t}% · {T['tnx_red']}% 이상")
        elif t >= T["tnx_yellow"]:
            add("yellow", "장기금리 부담", f"US 10Y {t}%")
        else:
            add("green", "장기금리 안정", f"US 10Y {t}%")

    # 유가
    w = g("WTI")
    if w is not None:
        if w >= T["wti_red"]:
            add("red", "유가 충격", f"WTI ${w} · ${T['wti_red']} 이상")
        elif w >= T["wti_yellow"]:
            add("yellow", "유가 상승 부담", f"WTI ${w}")
        else:
            add("green", "유가 안정", f"WTI ${w}")

    # BTC
    if btc.get("ok") and btc.get("ath_change") is not None:
        a = btc["ath_change"]
        if a <= T["btc_ath_gap_yellow"]:
            add("yellow", "BTC 고점 대비 낙폭", f"ATH 대비 {a}%")

    # 52주 위치
    p = g("KOSPI", "w52_pos_pct")
    if p is not None:
        if p <= T["w52_low_zone"]:
            add("yellow", "KOSPI 52주 저점권", f"52주 위치 {p}%")
        elif p >= T["w52_high_zone"]:
            add("yellow", "KOSPI 52주 고점권", f"52주 위치 {p}%")

    reds = sum(1 for f in flags if f["level"] == "red")
    yellows = sum(1 for f in flags if f["level"] == "yellow")
    total = len(flags) or 1
    score = round((reds + yellows * 0.5) / total * 10, 1)

    if score >= 6.0:
        phase, phase_cls = "고경계", "down"
    elif score >= 4.0:
        phase, phase_cls = "경계", "warn"
    elif score >= 2.0:
        phase, phase_cls = "주의", "warn"
    else:
        phase, phase_cls = "안정", "up"

    return {
        "flags": flags, "red": reds, "yellow": yellows, "total": total,
        "score": score, "phase": phase, "phase_cls": phase_cls,
        "formula": "(적색 + 황색×0.5) ÷ 전체 × 10",
    }


# ──────────────────────────────────────────────────────────────
# 5. 액션 알림 — 규칙 기반. 매수/매도 지시가 아니라 '점검 트리거'다.
# ──────────────────────────────────────────────────────────────
def build_alerts(market: dict, risk: dict) -> list:
    T = THRESHOLDS
    alerts = []

    def g(key, field="close"):
        rec = market.get(key, {})
        return rec.get(field) if rec.get("ok") else None

    k = g("KOSPI")
    kd = g("KOSPI", "disparity20")
    kma = g("KOSPI", "ma20")
    if k is not None and kma is not None:
        if kd is not None and kd <= T["disparity_low"]:
            alerts.append(f"KOSPI {k:,.2f} · 20일선({kma:,.0f}) 이격도 {kd} — "
                          f"{T['disparity_low']} 이하 과매도 구간 진입, 분할 접근 여부 점검")
        elif kd is not None and kd >= T["disparity_high"]:
            alerts.append(f"KOSPI {k:,.2f} · 20일선({kma:,.0f}) 이격도 {kd} — "
                          f"{T['disparity_high']} 이상 과열, 비중 점검")

    v = g("VIX")
    if v is not None and v >= T["vix_red"]:
        alerts.append(f"VIX {v} — {T['vix_red']} 돌파. 신규 진입 보류 기준 점검")

    fx = g("USDKRW")
    if fx is not None and fx >= T["usdkrw_red"]:
        alerts.append(f"USD/KRW {fx:,.2f} — {T['usdkrw_red']:,.0f} 돌파. "
                      f"달러자산 환헤지 여부 점검")

    w = g("WTI")
    if w is not None and w >= T["wti_red"]:
        alerts.append(f"WTI ${w} — ${T['wti_red']} 돌파. 에너지·항공 비중 점검")

    p = g("KOSPI", "w52_pos_pct")
    if p is not None and p <= T["w52_low_zone"]:
        alerts.append(f"KOSPI 52주 위치 {p}% — 저점권. 적립식 증액 룰 점검")

    if not alerts:
        alerts.append("임계값을 넘긴 지표 없음 — 기존 계획 유지")
    return alerts


# ──────────────────────────────────────────────────────────────
# 6. 통합
# ──────────────────────────────────────────────────────────────
def market_digest(data: dict) -> str:
    """프롬프트에 넣는 한 줄 시세 요약. 입력 토큰 최소화용 (구 버전은 전체 JSON을 넣었다)."""
    m = data["market"]
    bits = []
    for key, name in (("KOSPI", "KOSPI"), ("SP500", "S&P500"), ("NASDAQ", "NDX"),
                      ("VIX", "VIX"), ("USDKRW", "USDKRW"), ("WTI", "WTI")):
        r = m.get(key, {})
        if r.get("ok"):
            bits.append(f"{name} {r['close']:,.2f}({r['change_pct']:+.2f}%)")
    if data["btc"].get("ok"):
        bits.append(f"BTC {data['btc']['change_24h']:+.2f}%")
    return " / ".join(bits) or "시세 수집 실패"


def collect_all(asof_kst: datetime | None = None) -> dict:
    now = asof_kst or now_kst()
    today = now.date()

    market = collect_market()
    btc = collect_btc()
    fng = collect_crypto_fng()
    risk = build_risk_flags(market, btc, fng)
    alerts = build_alerts(market, risk)
    charts = collect_chart_series()

    # 종목별로 기준일이 다를 수 있다. 가장 최신 기준일을 대표값으로 쓴다.
    asofs = [v["asof"] for v in market.values() if v.get("ok") and v.get("asof")]
    data_asof = max(asofs) if asofs else None

    return {
        "meta": {
            "generated_at": now.strftime("%Y-%m-%d %H:%M:%S KST"),
            "date_iso":     today.isoformat(),
            "date_label":   fmt_date_label(today),
            "weekday_idx":  today.weekday(),
            "is_sunday":    today.weekday() == 6,
            "is_weekend":   today.weekday() >= 5,
            "data_asof":    data_asof or today.isoformat(),
        },
        "market":   market,
        "btc":      btc,
        "fng":      fng,
        "risk":     risk,
        "alerts":   alerts,
        "charts":   charts,
        "thresholds": THRESHOLDS,
    }


if __name__ == "__main__":
    d = collect_all()
    json.dump(d, sys.stdout, ensure_ascii=False, indent=2)
    print()
