# -*- coding: utf-8 -*-
"""
generate_dashboard.py — 수집·생성·검증·발송 전 과정

파이프라인
  data_collector(수집·계산) → LLM(JSON 텍스트만) → 검증 → Jinja2 렌더
  → 산출물 검증 → 저장 → 텔레그램 발송

파일 구성 (레포 루트)
  data_collector.py         수집 + 파생지표 + 리스크 판정 + 알림
  generate_dashboard.py     이 파일
  dashboard_template.html   레이아웃 + CSS
  prompt.md                 LLM 프롬프트 (일요일 구간은 마커로 분기)
  .github/workflows/dashboard.yml

단독 검증:
    python generate_dashboard.py --validate index.html [data.json]
"""

from __future__ import annotations

import html as _html
import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from jinja2 import Environment, FileSystemLoader, select_autoescape

import data_collector as dc
from data_collector import THRESHOLDS, fmt_md_weekday

KST = ZoneInfo("Asia/Seoul")
MODEL = os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5")
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "4000"))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))



# ========================================================================
# 1. LLM 출력 검증 + Jinja2 렌더링
# ========================================================================

# -*- coding: utf-8 -*-
"""
render.py — LLM JSON 검증/정규화 + Jinja2 렌더링

LLM은 여기서 '문자열 몇 개'로만 취급된다.
길이 초과·개수 초과·날짜 오류는 전부 여기서 잘라내거나 버린다.
버린 자리는 템플릿의 fallback 문구가 채운다.
"""





BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 문자 수 상한 — 프롬프트에도 같은 숫자를 적어 넣는다(이중 방어)
LIMITS = {
    "headline":           70,
    "issue_title":        40,
    "issue_body":        130,
    "trend_signal":       40,
    "trend_body":        160,
    "trend_beneficiary":  40,
    "event":              34,
    "expected":           24,
    "source":            120,
}

COUNTS = {
    "issues_global": 3,
    "issues_korea":  2,
    "calendar":      5,
    "trend_radar":   3,
}


# ──────────────────────────────────────────────────────────────
# 표시 헬퍼
# ──────────────────────────────────────────────────────────────
def eok(v) -> str:
    """억원 표기. None이면 조회실패로 표시한다."""
    if v is None:
        return "—"
    if abs(v) >= 10000:
        return f"{v / 10000:+,.2f}조"
    return f"{v:+,}억"


def _clip(s, n) -> str:
    s = " ".join(str(s or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"


# ──────────────────────────────────────────────────────────────
# 카드 하단 코멘트 — 파이썬이 만든다 (구 버전에선 여기가 환각 진원지였다)
# ──────────────────────────────────────────────────────────────
def build_card_subs(market: dict) -> None:
    T = THRESHOLDS
    for key, rec in market.items():
        if not rec.get("ok"):
            continue
        parts = []
        if rec.get("w52_pos_pct") is not None:
            p = rec["w52_pos_pct"]
            zone = ("52주 저점권" if p <= T["w52_low_zone"]
                    else "52주 고점권" if p >= T["w52_high_zone"] else "52주 중립대")
            parts.append(f"52주 위치 {p}% ({zone})")
        if key in ("KOSPI", "KOSDAQ", "SP500", "NASDAQ") and rec.get("disparity20") is not None:
            d = rec["disparity20"]
            state = ("과매도" if d <= T["disparity_low"]
                     else "과열" if d >= T["disparity_high"] else "정상")
            parts.append(f"20일 이격도 {d} ({state})")
        if key == "VIX":
            v = rec["close"]
            band = ("위험" if v >= T["vix_red"]
                    else "경계" if v >= T["vix_yellow"] else "안정")
            parts = [f"{band} 구간 · 기준 {T['vix_yellow']}/{T['vix_red']}"]
        rec["sub"] = " · ".join(parts) if parts else ""


# ──────────────────────────────────────────────────────────────
# LLM 출력 검증
# ──────────────────────────────────────────────────────────────
def _issue(d) -> dict | None:
    if not isinstance(d, dict):
        return None
    t = _clip(d.get("title"), LIMITS["issue_title"])
    b = _clip(d.get("body"), LIMITS["issue_body"])
    if not t or not b:
        return None
    if not any(c.isdigit() for c in b):        # 프롬프트 R4의 코드측 강제
        return None
    return {"title": t, "body": b, "source": _clip(d.get("source"), LIMITS["source"])}


def _event(d, today: date) -> dict | None:
    if not isinstance(d, dict):
        return None
    try:
        ev_date = date.fromisoformat(str(d.get("date"))[:10])
    except Exception:
        return None
    # 과거 이벤트, 8일 초과 미래는 버린다
    if not (today - timedelta(days=1) <= ev_date <= today + timedelta(days=8)):
        return None
    ev = _clip(d.get("event"), LIMITS["event"])
    if not ev:
        return None
    try:
        stars = int(d.get("stars", 2))
    except Exception:
        stars = 2
    stars = min(3, max(1, stars))
    t = str(d.get("time_kst") or "").strip()
    if t and not (len(t) == 5 and t[2] == ":"):
        t = ""
    return {
        "date_label": fmt_md_weekday(ev_date),   # 요일은 파이썬이 계산
        "date_iso":   ev_date.isoformat(),
        "time_kst":   t,
        "event":      ev,
        "expected":   _clip(d.get("expected"), LIMITS["expected"]),
        "stars":      stars,
    }


def _trend(d) -> dict | None:
    if not isinstance(d, dict):
        return None
    s = _clip(d.get("signal"), LIMITS["trend_signal"])
    b = _clip(d.get("body"), LIMITS["trend_body"])
    if not s or not b:
        return None
    if not any(c.isdigit() for c in b):        # 프롬프트 T3의 코드측 강제
        return None
    h = str(d.get("horizon") or "중기").strip()
    if h not in ("단기", "중기", "장기"):
        h = "중기"
    return {
        "signal": s, "body": b, "horizon": h,
        "beneficiary": _clip(d.get("beneficiary"), LIMITS["trend_beneficiary"]) or "—",
        "source": _clip(d.get("source"), LIMITS["source"]),
    }


def _fallback_headline(data: dict) -> str:
    k = data["market"].get("KOSPI", {})
    v = data["market"].get("VIX", {})
    bits = []
    if k.get("ok"):
        bits.append(f"KOSPI {k['close']:,.2f} ({k['change_pct']:+.2f}%)")
    if v.get("ok"):
        bits.append(f"VIX {v['close']}")
    bits.append(f"리스크 {data['risk']['score']} ({data['risk']['phase']})")
    return " · ".join(bits)


def normalize_llm(raw: dict, data: dict) -> dict:
    """LLM 출력을 스키마에 맞게 강제 정규화. 부적합 항목은 조용히 버린다."""
    raw = raw if isinstance(raw, dict) else {}
    today = date.fromisoformat(data["meta"]["date_iso"])
    rejected = []

    headline = _clip(raw.get("headline"), LIMITS["headline"]) or _fallback_headline(data)

    fg = None
    try:
        v = int(raw["cnn_fear_greed"]["value"])
        if 0 <= v <= 100:
            lbl = str(raw["cnn_fear_greed"].get("label") or "").strip()[:20]
            fg = {"value": v, "label": lbl or "—",
                  "cls": "down" if v <= THRESHOLDS["fng_fear"]
                         else "up" if v >= THRESHOLDS["fng_greed"] else "neutral"}
    except Exception:
        rejected.append("cnn_fear_greed")

    def take(key, fn, n, *a):
        src = raw.get(key) or []
        if not isinstance(src, list):
            return []
        out = [x for x in (fn(i, *a) for i in src) if x][:n]
        if len(out) < len(src[:n]):
            rejected.append(f"{key}({len(src[:n]) - len(out)}건 폐기)")
        return out

    return {
        "headline":       headline,
        "cnn_fear_greed": fg,
        "issues_global":  take("issues_global", lambda d: _issue(d), COUNTS["issues_global"]),
        "issues_korea":   take("issues_korea",  lambda d: _issue(d), COUNTS["issues_korea"]),
        "calendar":       take("calendar", lambda d: _event(d, today), COUNTS["calendar"]),
        "trend_radar":    take("trend_radar", lambda d: _trend(d), COUNTS["trend_radar"]),
        "_rejected":      rejected,
    }


# ──────────────────────────────────────────────────────────────
# 렌더링
# ──────────────────────────────────────────────────────────────
def render_dashboard(data: dict, llm_raw: dict) -> tuple[str, dict]:
    """returns (html, normalized_llm)"""
    build_card_subs(data["market"])
    llm = normalize_llm(llm_raw, data)
    if llm["_rejected"]:
        print(f"  LLM 출력 일부 폐기: {', '.join(llm['_rejected'])}")

    env = Environment(
        loader=FileSystemLoader(BASE_DIR),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.globals["eok"] = eok

    tpl = env.get_template("dashboard_template.html")
    html = tpl.render(
        meta=data["meta"],
        market=data["market"],
        btc=data["btc"],
        fng=data["fng"],
        charts=data["charts"],
        risk=data["risk"],
        alerts=data["alerts"],
        llm=llm,
        is_sunday=data["meta"]["is_sunday"],
    )
    return html, llm

# ========================================================================
# 2. 산출물 자동 검증 — 실패 시 저장·발송 중단
# ========================================================================

# -*- coding: utf-8 -*-
"""
validate_output.py — 생성된 HTML이 만족해야 할 조건을 기계적으로 검사한다.

generate_dashboard.py 가 저장 직전에 호출한다.
하나라도 걸리면 파일을 쓰지 않고 워크플로를 실패시킨다 → 깨진 대시보드가
커밋되거나 텔레그램으로 나가는 일을 원천 차단.

단독 실행:
    python validate_output.py index.html            # 구조 검사만
    python validate_output.py index.html data.json  # 수치 대조까지
"""



WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]

MIN_LEN = 3000
MAX_LEN = 400000   # Chart.js(~205KB)를 인라인 내장하므로 상향. 잘림 검출은 닫는 태그 검사가 담당.
MAX_HEADLINE = 70

# 투자 지시로 읽힐 수 있는 표현 — 규칙 기반 알림으로 바꾼 뒤엔 나오면 안 된다
FORBIDDEN = ["매도 권고", "매수 권고", "매도 권장", "매수 권장",
             "손절 권고", "전량 매도", "비중 축소 권고", "차감 권고"]

# 렌더링 실패 흔적
GARBAGE = ["[[", "]]", "{{", "{%", "None", "NaN", "undefined", "nan%"]


def _strip_tags(h: str) -> str:
    h = re.sub(r"<style.*?</style>", " ", h, flags=re.S)
    h = re.sub(r"<script.*?</script>", " ", h, flags=re.S)
    return re.sub(r"<[^>]+>", "\n", h)


def validate_html(html: str, data: dict | None = None) -> list[str]:
    p: list[str] = []
    text = _strip_tags(html)

    # ── 1. 구조 완결성 ──────────────────────────────────────
    if not html.lstrip().lower().startswith("<!doctype html>"):
        p.append("DOCTYPE 선언 없음")
    for tag in ("</head>", "</body>", "</html>"):
        if tag not in html:
            p.append(f"닫는 태그 누락: {tag}  ← 응답이 잘렸을 가능성")
    if html.rstrip()[-7:].lower() != "</html>":
        p.append("파일이 </html> 로 끝나지 않음")
    o, c = html.count("<div"), html.count("</div>")
    if o != c:
        p.append(f"div 태그 불균형: 여는 {o} / 닫는 {c}")

    # ── 2. 분량 ────────────────────────────────────────────
    if len(html) < MIN_LEN:
        p.append(f"산출물이 너무 짧음: {len(html)}자 (<{MIN_LEN})")
    if len(html) > MAX_LEN:
        p.append(f"산출물이 너무 김: {len(html)}자 (>{MAX_LEN})")

    # ── 3. 미치환 슬롯 / 렌더 실패 흔적 ─────────────────────
    for g in GARBAGE:
        if g in text:
            p.append(f"렌더 실패 흔적 발견: '{g}'")

    # ── 4. 투자 지시 표현 ───────────────────────────────────
    for f in FORBIDDEN:
        if f in text:
            p.append(f"투자 지시 표현 발견: '{f}'")

    # ── 5. 요일 정합성 (구 버전 전수 오답 지점) ─────────────
    #      "2026년 7월 27일 (월)" 과 "7월 28일 (화)" 두 형식을 모두 본다
    base = None
    if data and data.get("meta", {}).get("date_iso"):
        base = date.fromisoformat(data["meta"]["date_iso"])

    seen = set()
    for y, m, d, w in re.findall(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일\s*\((.)\)", text):
        seen.add((int(m), int(d)))
        p += _check_weekday(int(y), int(m), int(d), w)

    for m, d, w in re.findall(r"(?<!년\s)(\d{1,2})월\s*(\d{1,2})일\s*\((.)\)", text):
        m, d = int(m), int(d)
        if (m, d) in seen:
            continue
        if base is None:
            continue
        # 연말연시 경계: 표기 월이 기준월보다 6개월 이상 과거면 내년으로 본다
        y = base.year + 1 if m < base.month - 6 else base.year
        p += _check_weekday(y, m, d, w)

    # ── 6. 강세/약세 부호 (구 버전에서 강세 칸에 음수가 들어갔다) ──
    for label, want in (("강세 업종", "+"), ("약세 업종", "-")):
        blk = _section_after(text, label, stop_labels=["강세 업종", "약세 업종", "핵심 이슈"])
        for v in re.findall(r"([+-]\d+\.\d+)%", blk):
            if want == "+" and float(v) <= 0:
                p.append(f"'{label}' 칸에 비양수 값: {v}%")
            if want == "-" and float(v) >= 0:
                p.append(f"'{label}' 칸에 비음수 값: {v}%")

    # ── 7. 데이터 대조 ─────────────────────────────────────
    if data:
        p += _cross_check(html, text, data)

    return p


def _check_weekday(y: int, m: int, d: int, w: str) -> list[str]:
    try:
        real = WEEKDAY_KR[date(y, m, d).weekday()]
    except ValueError:
        return [f"존재하지 않는 날짜: {y}-{m}-{d}"]
    if real != w:
        return [f"요일 불일치: {y}-{m:02d}-{d:02d} 는 {real}요일인데 ({w}) 로 표기"]
    return []


def _section_after(text: str, label: str, stop_labels: list[str]) -> str:
    i = text.find(label)
    if i < 0:
        return ""
    rest = text[i + len(label):]
    ends = [rest.find(s) for s in stop_labels if rest.find(s) > 0]
    return rest[: min(ends)] if ends else rest[:600]


def _cross_check(html: str, text: str, data: dict) -> list[str]:
    p: list[str] = []
    meta = data.get("meta", {})

    if meta.get("date_label") and meta["date_label"] not in text:
        p.append(f"헤더 날짜 라벨 불일치: '{meta['date_label']}' 없음")

    # 주요 지수 종가가 문서에 실제로 등장하는지
    for key in ("KOSPI", "SP500", "USDKRW"):
        rec = data.get("market", {}).get(key, {})
        if not rec.get("ok"):
            continue
        s = f"{rec['close']:,.2f}"
        if s not in text:
            p.append(f"{key} 종가 {s} 가 문서에 없음 (수집값과 표시값 불일치)")

    # 같은 지표가 서로 다른 값으로 두 번 나오면 안 된다
    # (종가 문자열 바로 뒤 30자 이내만 본다 — "KOSPI" 뒤 80자는 다음 카드까지 걸려 오탐났었다)
    rec = data.get("market", {}).get("KOSPI", {})
    if rec.get("ok"):
        close_s = re.escape(f"{rec['close']:,.2f}")
        pcts = set(re.findall(close_s + r"[^\n]{0,30}?([+-]\d+\.\d+)%", text))
        want = f"{rec['change_pct']:+.2f}"
        bad = [v for v in pcts if v != want]
        if bad:
            p.append(f"KOSPI 등락률 표기 충돌: 수집값 {want}% vs 문서 {bad}")

    # 헤드라인 길이
    m = re.search(r"⚡\s*([^\n]+)", text)
    if m and len(m.group(1).strip()) > MAX_HEADLINE:
        p.append(f"헤드라인 {len(m.group(1).strip())}자 (상한 {MAX_HEADLINE})")

    return p


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python validate_output.py <html> [data.json]")
        return 2
    html = open(sys.argv[1], encoding="utf-8").read()
    data = json.load(open(sys.argv[2], encoding="utf-8")) if len(sys.argv) > 2 else None
    problems = validate_html(html, data)
    if problems:
        print(f"FAIL ({len(problems)}건)")
        for x in problems:
            print("  -", x)
        return 1
    print("PASS")
    return 0

# ========================================================================
# 3. 텔레그램 발송 (구 메일 발송 대체)
# ========================================================================

# -*- coding: utf-8 -*-
"""
notify_telegram.py — 메일 대체. 텔레그램으로 발송한다.

두 건을 보낸다.
  1) 요약 메시지 (parse_mode=HTML, 4096자 제한 준수)
     — 파이썬이 같은 data 딕셔너리로 조립하므로 LLM 토큰이 추가로 들지 않는다.
  2) index.html 파일 첨부 (sendDocument)

필요 시크릿
  TELEGRAM_BOT_TOKEN : @BotFather 에서 발급
  TELEGRAM_CHAT_ID   : 봇에게 아무 메시지나 보낸 뒤
                       https://api.telegram.org/bot<TOKEN>/getUpdates 에서 확인
선택 환경변수
  DASHBOARD_URL      : GitHub Pages 등 공개 URL. 설정하면 요약 하단에 링크를 붙인다.
"""




API = "https://api.telegram.org/bot{token}/{method}"
TG_LIMIT = 4096


def _esc(s) -> str:
    return _html.escape(str(s), quote=False)


def _line_market(label: str, rec: dict, unit: str = "") -> str | None:
    if not rec.get("ok"):
        return f"{_esc(label)}: <i>조회실패</i>"
    dot = "▲" if rec["change_pct"] > 0 else ("▼" if rec["change_pct"] < 0 else "⚪")
    return (f"{_esc(label)}: <b>{unit}{rec['close']:,.2f}</b> "
            f"{dot} {rec['change_pct']:+.2f}%")


def build_summary(data: dict, llm: dict) -> str:
    m = data["market"]
    meta = data["meta"]
    risk = data["risk"]

    out = [
        f"📊 <b>시장 대시보드</b> · {_esc(meta['date_label'])}",
        f"<i>데이터 기준 {_esc(meta['data_asof'])}</i>",
        "",
        f"⚡ {_esc(llm.get('headline', ''))}",
        "",
        f"<b>리스크 {risk['score']} · {_esc(risk['phase'])}</b> "
        f"(적색 {risk['red']} / 황색 {risk['yellow']} / 전체 {risk['total']})",
        "",
        "<b>주요 지표</b>",
    ]

    for label, key, unit in (
        ("KOSPI", "KOSPI", ""), ("KOSDAQ", "KOSDAQ", ""),
        ("S&P500", "SP500", ""), ("나스닥100", "NASDAQ", ""),
        ("VIX", "VIX", ""), ("USD/KRW", "USDKRW", ""),
        ("금", "GOLD", "$"), ("WTI", "WTI", "$"), ("US 10Y", "TNX", ""),
    ):
        ln = _line_market(label, m.get(key, {}), unit)
        if ln:
            out.append("· " + ln)

    btc = data["btc"]
    if btc.get("ok"):
        dot = "🔴" if btc["change_24h"] > 0 else ("🔵" if btc["change_24h"] < 0 else "⚪")
        out.append(f"· BTC: <b>₩{btc['krw']:,}</b> {dot} {btc['change_24h']:+.2f}% "
                   f"(ATH 대비 {btc['ath_change']}%)")

    issues = (llm.get("issues_global") or []) + (llm.get("issues_korea") or [])
    if issues:
        out += ["", "<b>핵심 이슈</b>"]
        out += [f"· {_esc(i['title'])}" for i in issues]

    cal = llm.get("calendar") or []
    if cal:
        out += ["", "<b>다가오는 일정</b>"]
        out += [f"· {_esc(e['date_label'])} {_esc(e['event'])} {'★' * e['stars']}"
                for e in cal[:4]]

    out += ["", "<b>🔔 점검 트리거</b>"]
    out += [f"· {_esc(a)}" for a in data["alerts"]]

    url = os.environ.get("DASHBOARD_URL", "").strip()
    if url:
        out += ["", f'<a href="{_esc(url)}">전체 대시보드 열기</a>']

    text = "\n".join(out)
    if len(text) > TG_LIMIT:
        text = text[: TG_LIMIT - 20].rstrip() + "\n…(생략)"
    return text


def _post(token: str, method: str, **kw):
    r = requests.post(API.format(token=token, method=method), timeout=30, **kw)
    body = {}
    try:
        body = r.json()
    except Exception:
        pass
    if not body.get("ok"):
        raise RuntimeError(f"텔레그램 {method} 실패 [{r.status_code}]: {body or r.text[:300]}")
    return body


def send_telegram(data: dict, llm: dict, html_path: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 시크릿이 없습니다")

    text = build_summary(data, llm)
    _post(token, "sendMessage", data={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    })
    print(f"  텔레그램 요약 발송 완료 ({len(text)}자)")

    fname = f"dashboard_{data['meta']['date_iso'].replace('-', '')}.html"
    with open(html_path, "rb") as f:
        _post(token, "sendDocument",
              data={"chat_id": chat_id,
                    "caption": f"{data['meta']['date_label']} 대시보드"},
              files={"document": (fname, f, "text/html")})
    print(f"  텔레그램 파일 발송 완료 ({fname})")

# ========================================================================
# 4. LLM 호출
# ========================================================================

def load_prompt(is_sunday: bool, data: dict) -> str:
    """prompt.md 로드. [[IF_SUNDAY]]...[[END_SUNDAY]] 구간을 요일에 따라 남기거나 지운다."""
    with open(os.path.join(BASE_DIR, "prompt.md"), encoding="utf-8") as f:
        p = f.read()

    if is_sunday:
        p = p.replace("[[IF_SUNDAY]]", "").replace("[[END_SUNDAY]]", "")
    else:
        p = re.sub(r"\[\[IF_SUNDAY\]\][\s\S]*?\[\[END_SUNDAY\]\]", "", p)

    meta = data["meta"]
    max_date = (date.fromisoformat(meta["date_iso"]) + timedelta(days=8)).isoformat()
    return (p.replace("[[TODAY_ISO]]", meta["date_iso"])
             .replace("[[TODAY_LABEL]]", meta["date_label"])
             .replace("[[DATA_ASOF]]", meta["data_asof"])
             .replace("[[MARKET_DIGEST]]", dc.market_digest(data))
             .replace("[[MAX_DATE]]", max_date))


def extract_json(text: str) -> dict:
    """LLM 응답에서 JSON 객체만 뽑는다. 코드펜스·앞뒤 설명 제거."""
    t = re.sub(r"\s*```$", "", re.sub(r"^```(?:json)?\s*", "", text.strip()))
    i, j = t.find("{"), t.rfind("}")
    if i == -1 or j <= i:
        raise ValueError("응답에서 JSON 객체를 찾지 못함")
    return json.loads(t[i:j + 1])


def call_llm(prompt: str) -> dict:
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    messages = [{"role": "user", "content": prompt}]
    tools = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 6}]

    for hop in range(6):
        resp = client.messages.create(
            model=MODEL, max_tokens=MAX_TOKENS, tools=tools, messages=messages
        )
        print(f"  LLM hop {hop + 1}: stop_reason={resp.stop_reason} "
              f"(in {resp.usage.input_tokens} / out {resp.usage.output_tokens})")

        # 서버측 웹검색은 pause_turn 으로 되돌아온다. 그대로 이어 붙여 재요청한다.
        # (구 버전은 이 자리에 "검색 완료" 문자열을 넣어 검색 결과를 통째로 버렸다)
        if resp.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": resp.content})
            continue

        if resp.stop_reason == "max_tokens":
            raise RuntimeError(f"max_tokens({MAX_TOKENS}) 초과로 응답이 잘렸습니다")
        if resp.stop_reason != "end_turn":
            raise RuntimeError(f"예상치 못한 stop_reason: {resp.stop_reason}")

        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        if not text.strip():
            raise RuntimeError("LLM이 텍스트를 반환하지 않았습니다")
        return extract_json(text)

    raise RuntimeError("검색 hop 상한 초과")


# ========================================================================
# 5. 메인
# ========================================================================

def main() -> int:
    # 단독 검증 모드: python generate_dashboard.py --validate index.html [data.json]
    if "--validate" in sys.argv:
        i = sys.argv.index("--validate")
        html = open(sys.argv[i + 1], encoding="utf-8").read()
        d = json.load(open(sys.argv[i + 2], encoding="utf-8")) if len(sys.argv) > i + 2 else None
        problems = validate_html(html, d)
        if problems:
            print(f"FAIL ({len(problems)}건)")
            for x in problems:
                print("  -", x)
            return 1
        print("PASS")
        return 0

    now = datetime.now(KST)                     # ★ KST 고정
    print(f"실행 시각(KST): {now:%Y-%m-%d %H:%M:%S} ({dc.WEEKDAY_KR[now.weekday()]}요일)")

    data = dc.collect_all(now)
    is_sunday = data["meta"]["is_sunday"]
    print(f"프롬프트: {'일요일(트렌드 레이더 포함)' if is_sunday else '평일'}")

    try:
        llm_raw = call_llm(load_prompt(is_sunday, data))
    except Exception as e:
        # 뉴스 섹션만 비우고 나머지는 정상 발행한다. 전체 중단은 과잉이다.
        print(f"  LLM 실패 → 뉴스/일정 섹션 없이 발행: {e}")
        llm_raw = {}

    html, llm = render_dashboard(data, llm_raw)

    problems = validate_html(html, data)
    if problems:
        print("산출물 검증 실패 — 저장·발송 중단:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"산출물 검증 통과 ({len(html):,}자)")

    out = os.environ.get("FILENAME", "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"저장: {out}")

    if os.environ.get("TELEGRAM_BOT_TOKEN"):
        send_telegram(data, llm, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
