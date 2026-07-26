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
import time
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
# ──────────────────────────────────────────────────────────────
# 기준일 신선도 — 종목 간 asof 를 대조해 뒤처진 지표를 잡는다
#
# 2026-07-25 사고: KOSPI 만 7/23 에 멈춰 7,096.89(+4.40%) 로 나갔는데
# 뉴스는 7/24 의 6,690.62(-5.72%) 급락을 정확히 실었다. 지표가 낡은 게 원인이지
# 표현이 틀린 게 아니었다. 공휴일 달력 없이도 잡으려고 종목 간 상대 비교를 쓴다.
# ──────────────────────────────────────────────────────────────
FRESHNESS_GROUPS = {
    "한국 증시":   (["KOSPI", "KOSDAQ"], 0),
    "미국 증시":   (["SP500", "NASDAQ", "VIX"], 0),
    "환율":        (["USDKRW", "USDJPY"], 1),
    "원자재·금리": (["GOLD", "WTI", "TNX"], 1),
}


# ──────────────────────────────────────────────────────────────
# 슬롯별 검색 세트 — 하루 3회 실행이므로 시간대마다 다른 영역을 겨냥한다.
# 검색 1회당 $0.01 이 붙으므로 개수는 4건으로 고정하고 '무엇을 볼지'만 바꾼다.
# ──────────────────────────────────────────────────────────────
SEARCH_SETS = {
    "morning": {   # KST 07:00 — 미국장 마감 직후
        "label": "미국 마감 + 지정학",
        "queries": [
            "CNN fear and greed index today",
            "US stock market close [[TODAY_ISO]]",
            "geopolitical risk war conflict news [[TODAY_ISO]]",
            "economic calendar this week [[TODAY_ISO]]",
        ],
    },
    "midday": {    # KST 11:40 — 한국 장중
        "label": "한국 증시 + 정부정책·부동산",
        "queries": [
            "CNN fear and greed index today",
            "코스피 증시 뉴스 [[TODAY_ISO]]",
            "정부 정책 발표 부동산 대책 규제 [[TODAY_ISO]]",
            "economic calendar this week [[TODAY_ISO]]",
        ],
    },
    "evening": {   # KST 19:00 — 한국 마감 후, 유럽 장중
        "label": "중국·일본·유럽 + 무역",
        "queries": [
            "CNN fear and greed index today",
            "China Japan Europe economy news [[TODAY_ISO]]",
            "trade tariff export controls news [[TODAY_ISO]]",
            "economic calendar this week [[TODAY_ISO]]",
        ],
    },
}


def slot_of(now: datetime) -> str:
    """실행 시각(KST)으로 슬롯을 정한다.

    예약은 06:20 / 11:40 / 19:00 이지만 GitHub Actions 스케줄은 크게 밀린다.
    아침 예약분이 3시간 넘게 지연돼도 점심 검색어로 새지 않도록 경계를 넓게 잡는다.
    """
    h = now.hour
    if h < 11:
        return "morning"
    if h < 17:
        return "midday"
    return "evening"


# ──────────────────────────────────────────────────────────────
# 시사점 룰북 — (카테고리 × 압력) → 전달경로.
#
# Haiku 는 카테고리와 압력만 고른다(각각 고정 선택지). 서술은 전부 여기서 나온다.
# 교과서적 인과만 담아 환각 여지를 없앤다. 매수·매도 지시는 넣지 않는다
# (validate_html 의 FORBIDDEN 검사에 걸린다).
#
# pressure 는 '한국 투자자 자산 관점'에서의 방향이다 — 유리 / 불리 / 중립.
# ──────────────────────────────────────────────────────────────
NEWS_CATEGORIES = [
    "유가", "금리·중앙은행", "환율·달러", "지정학·전쟁", "반도체·AI",
    "중국경제", "미국경제", "한국정책·규제", "부동산·건설", "무역·관세",
    "일본·엔화", "유럽경제",
]
NEWS_PRESSURES = ["유리", "불리", "중립"]

IMPLICATION_RULES = {
    ("유가", "불리"):
        "항공·운송 원가 부담 확대. 헤드라인 물가 압력이 커지면 금리 인하 기대가 후퇴해 "
        "성장주 밸류에이션에 부담. 정유는 정제마진 개선으로 상대적 수혜.",
    ("유가", "유리"):
        "운송·항공·석유화학 원가 부담 완화. 물가 압력 둔화로 금리 인하 여지 확대 → "
        "성장주에 우호적. 산유국 재정 악화 시 중동 발주 둔화는 별도 관찰 필요.",
    ("금리·중앙은행", "불리"):
        "할인율 상승으로 성장주·장기채 부담. 은행은 예대마진 개선. "
        "한미 금리차 확대 시 원화 약세 압력과 외국인 수급 이탈 경로.",
    ("금리·중앙은행", "유리"):
        "할인율 하락으로 성장주·장기채 유리. 은행 예대마진은 축소. "
        "부동산·건설 금융비용 부담 완화.",
    ("환율·달러", "불리"):
        "원화 약세 → 수출주 환산 실적에는 우호적이나 외국인 자금 이탈 압력. "
        "원자재 수입 원가 상승으로 내수·항공·정유 부담.",
    ("환율·달러", "유리"):
        "원화 강세 → 외국인 수급에 우호적, 수입 원가 부담 완화. "
        "수출주 환산 실적에는 역풍.",
    ("지정학·전쟁", "불리"):
        "안전자산 선호로 금·달러 강세, 원화 등 신흥국 통화 약세. "
        "방산은 수주 기대. 유가·해상운임 경로로 원가 전가 발생 가능.",
    ("지정학·전쟁", "유리"):
        "위험선호 회복으로 신흥국 자금 유입 여건 개선. 안전자산 프리미엄 축소로 "
        "금·달러 강세 되돌림. 유가·운임 안정 시 운송·항공 원가 부담 완화.",
    ("반도체·AI", "불리"):
        "국내 지수 시총 비중이 큰 섹터라 지수 자체에 직접 타격. "
        "설비투자 축소 시 반도체 소재·부품·장비까지 후행 영향.",
    ("반도체·AI", "유리"):
        "국내 지수 시총 비중이 큰 섹터라 지수 상방에 직접 기여. "
        "설비투자 확대 시 소재·부품·장비로 온기 확산.",
    ("중국경제", "불리"):
        "대중 수출 비중 큰 화학·철강·기계·화장품 실적 하향 압력. "
        "위안 약세 시 원화 동반 약세 경향. 중국 증시와 코스피 동조 구간 주의.",
    ("중국경제", "유리"):
        "대중 수출 비중 큰 화학·철강·기계 업황 개선 기대. "
        "위안 강세는 원화에도 우호적. 원자재 수요 회복 시 소재주 수혜.",
    ("미국경제", "불리"):
        "미 증시 조정은 코스피에 익일 갭으로 전이되는 경향. "
        "경기 둔화 신호면 수출 중심 한국 기업 실적 전망에 하향 압력.",
    ("미국경제", "유리"):
        "미 증시 강세는 코스피 위험선호에 우호적. "
        "다만 지표 호조가 금리 인하 지연으로 해석되면 성장주엔 역풍일 수 있음.",
    ("한국정책·규제", "불리"):
        "해당 산업 규제 강도에 따라 밸류에이션 디스카운트. "
        "세제·배당 정책은 지주사·금융주 재평가 경로와 직결.",
    ("한국정책·규제", "유리"):
        "규제 완화·세제 지원은 해당 섹터 재평가 요인. "
        "밸류업·배당 확대 기조는 저PBR 금융·지주사에 우호적.",
    ("부동산·건설", "불리"):
        "건설·시멘트·가구 등 전방 수요 위축. PF 부실 확대 시 증권·저축은행 "
        "신용 리스크로 전이. 가계 자산효과 축소로 내수 소비에도 후행 영향.",
    ("부동산·건설", "유리"):
        "건설·시멘트·가구 등 전방 수요 개선. PF 리스크 완화 시 증권·건설 "
        "신용 스프레드 축소. 가계 자산효과로 내수 소비에 우호적.",
    ("무역·관세", "불리"):
        "관세·수출통제는 자동차·철강·반도체 등 대미·대중 수출주에 직접 타격. "
        "공급망 재편 비용 발생. 환율 방어 필요성 커지며 통화정책 제약.",
    ("무역·관세", "유리"):
        "관세 인하·협상 타결은 자동차·철강·반도체 수출주에 직접 수혜. "
        "공급망 불확실성 축소로 설비투자 재개 여건 개선.",
    ("일본·엔화", "불리"):
        "엔 약세는 자동차·철강·기계에서 한국 기업과 가격 경쟁 심화. "
        "엔 캐리 청산 국면이면 글로벌 위험자산 전반에 유동성 축소 압력.",
    ("일본·엔화", "유리"):
        "엔 강세는 일본과 경쟁하는 자동차·철강·기계의 상대 가격 경쟁력 개선. "
        "엔 캐리 확대 국면은 위험자산 유동성에 우호적.",
    ("유럽경제", "불리"):
        "대유럽 수출 비중 큰 자동차·배터리·조선 수요 둔화. "
        "ECB 정책 변화는 달러 지수를 통해 원화에 간접 영향.",
    ("유럽경제", "유리"):
        "대유럽 수출 비중 큰 자동차·배터리·조선 수요 개선. "
        "유로 강세는 달러 지수 하락으로 이어져 신흥국 통화에 우호적.",
}


def build_implication(category: str, pressure: str, market: dict) -> dict | None:
    """룰북 서술 + 시장 반영 여부를 붙인다. 반영 여부는 KOSPI 등락과 대조한다."""
    if pressure == "중립":
        return None
    rule = IMPLICATION_RULES.get((category, pressure))
    if not rule:
        return None

    reflected = None
    k = market.get("KOSPI", {})
    if k.get("ok") and k.get("change_pct") is not None:
        pct = k["change_pct"]
        if pct == 0:
            reflected = None
        elif (pressure == "유리") == (pct > 0):
            reflected = f"KOSPI {pct:+.2f}% · 방향 일치 (반영 중)"
        else:
            reflected = f"KOSPI {pct:+.2f}% · 방향 불일치 (아직 미반영)"

    return {"category": category, "pressure": pressure,
            "channel": rule, "reflected": reflected}


# ──────────────────────────────────────────────────────────────
# 확정 일정 — 몇 년 전 공표되고 바뀌지 않는 이벤트는 검색에 맡기지 않는다.
#
# 실측 사고: FOMC 날짜가 실행 3회에서 7/30 → 7/28 → 7/27 로 매번 달랐다.
# 실제 2026년 FOMC 는 7/28~29 회의, 결정 발표는 7/29 미 동부시간 14:00
# (= KST 7/30 03:00). 검색 결과에 의존하는 한 이 오류는 계속 재발한다.
#
# 갱신 주기: 연 1회. FOMC 는 federalreserve.gov, 금통위는 bok.or.kr 공표 기준.
# ──────────────────────────────────────────────────────────────
FIXED_EVENTS = [
    # (KST 날짜, KST 시각, 이벤트명, 중요도)
    # FOMC: 회의 2일차 미 동부시간 14:00 발표 → KST 익일 새벽
    #       (11월 첫 일요일 이전은 EDT라 03:00, 이후는 EST라 04:00)
    ("2026-07-30", "03:00", "미국 FOMC 정책금리 결정", 3),
    ("2026-09-17", "03:00", "미국 FOMC 정책금리 결정", 3),
    ("2026-10-29", "03:00", "미국 FOMC 정책금리 결정", 3),
    ("2026-12-10", "04:00", "미국 FOMC 정책금리 결정", 3),
    # 한국은행 금융통화위원회 통화정책방향 결정회의
    ("2026-08-27", "09:00", "한국은행 금통위 기준금리 결정", 3),
    ("2026-10-22", "09:00", "한국은행 금통위 기준금리 결정", 3),
    ("2026-11-26", "09:00", "한국은행 금통위 기준금리 결정", 3),
]

# 시스템이 직접 공급하므로 LLM 이 낸 같은 주제 항목은 버린다.
FIXED_EVENT_KEYWORDS = [
    "fomc", "연준", "연방준비", "fed ", "미국 금리", "미국 기준금리",
    "금통위", "한국은행", "한은 ", "기준금리",
]


def merge_calendar(llm_events: list, today: date, horizon_days: int = 8) -> list:
    """확정 일정을 주입하고, LLM 이 낸 중복 주제 항목을 걷어낸다."""
    kept = []
    for e in llm_events:
        text = f"{e.get('event','')}".lower()
        if any(k in text for k in FIXED_EVENT_KEYWORDS):
            print(f"  · 캘린더 교체(확정 일정 우선): {e.get('event')}")
            continue
        kept.append(e)

    hi = today + timedelta(days=horizon_days)
    for iso, hhmm, name, stars in FIXED_EVENTS:
        d = date.fromisoformat(iso)
        if today <= d <= hi:
            kept.append({
                "date_label": fmt_md_weekday(d),
                "date_iso": iso,
                "time_kst": hhmm,
                "event": name,
                "expected": "",
                "stars": stars,
            })

    kept.sort(key=lambda x: (x["date_iso"], x.get("time_kst") or ""))

    # 목록 소진 경고 — 연 1회 갱신을 놓치면 조용히 비어버린다.
    last = max(date.fromisoformat(i) for i, *_ in FIXED_EVENTS)
    if today > last - timedelta(days=30):
        print(f"  ⚠️ FIXED_EVENTS 갱신 필요: 마지막 등록 일정이 {last} 입니다")

    return kept


# ──────────────────────────────────────────────────────────────
# 지표 재진술 탐지 — 시스템이 이미 카드로 보여주는 값을 이슈로 다시 쓴 것.
#
# 실측: "한국 지수 약세 지속", "원/달러 환율 소폭 하락" 같은 항목이 계속 나온다.
# 프롬프트 X1 로 금지해도 안 지켜지고, 분류를 필수로 만들자 폐기를 피하려고
# 엉뚱한 카테고리를 갖다 붙였다("한국 지수 약세 지속" → 한국정책·규제).
#
# 판별: 제목에서 '우리가 이미 보여주는 자산명 + 방향어 + 정도부사'를 지운 뒤
#       남는 알맹이가 없으면 재진술로 본다.
# ──────────────────────────────────────────────────────────────
RESTATEMENT_ASSETS = [
    "코스피", "KOSPI", "코스닥", "KOSDAQ", "한국 지수", "국내 지수", "지수",
    "원/달러", "원달러", "환율", "S&P500", "S&P 500", "S&P", "나스닥", "NASDAQ",
    "NDX", "다우", "미국 증시", "뉴욕증시", "국제유가", "유가", "WTI", "금값",
    "비트코인", "BTC", "VIX", "국채금리", "미 국채",
]
RESTATEMENT_MOVES = [
    "상승", "하락", "급등", "급락", "폭등", "폭락", "강세", "약세", "반등",
    "조정", "보합", "혼조", "마감", "지속", "전환", "확대", "축소", "둔화",
]
RESTATEMENT_DEGREE = [
    "소폭", "대폭", "큰 폭", "큰폭", "일제히", "동반", "미세", "소규모",
    "장중", "전일", "오늘", "기타", "및", "속", "등",
]
RESTATEMENT_MIN_REMAIN = 3   # 남는 알맹이가 이 글자 수 이하면 재진술로 본다


def is_restatement(title: str) -> bool:
    s = title
    for w in sorted(RESTATEMENT_ASSETS + RESTATEMENT_MOVES + RESTATEMENT_DEGREE,
                    key=len, reverse=True):
        s = s.replace(w, " ")
    s = re.sub(r"[\s,·—\-~/()\[\]0-9.%]+", "", s)
    return len(s) <= RESTATEMENT_MIN_REMAIN


# ──────────────────────────────────────────────────────────────
# 중요도 정규화 — R9 를 코드로 강제한다.
# 실측: "미국 GDP 확정치"가 ★★★ 로 나왔으나 규칙상 ★★ 다.
# ──────────────────────────────────────────────────────────────
STARS_3 = ["정책금리", "기준금리", "fomc", "금통위", "고용", "실업", "비농업",
           "cpi", "pce", "소비자물가", "물가지수"]
STARS_2 = ["gdp", "국내총생산", "pmi", "소매판매", "무역수지", "ppi",
           "생산자물가", "소비자신뢰"]


def normalize_stars(event: str, fallback: int = 1) -> int:
    e = event.lower()
    if any(k in e for k in STARS_3):
        return 3
    if any(k in e for k in STARS_2):
        return 2
    return fallback


def _kr_nontrading(d: date) -> bool:
    """주말이거나 한국 공휴일이면 True. holidays 미설치 시 주말만 판정."""
    if d.weekday() >= 5:
        return True
    try:
        import holidays
        return d in holidays.KR(years=[d.year])
    except Exception:
        return False


def expected_last_kr_session(now: datetime) -> date:
    """KST 기준 지금 시점에서 '마지막으로 마감된' 한국 거래일.

    한국장 마감 15:30 + 데이터 반영 여유를 감안해 16시 이후에만 당일 종가를 기대한다.
    """
    d = now.date()
    if now.hour < 16:
        d -= timedelta(days=1)
    while _kr_nontrading(d):
        d -= timedelta(days=1)
    return d


def expected_last_us_session(now: datetime) -> date:
    """KST 기준 마지막으로 마감된 미국 거래일(미국 현지 날짜).

    미 정규장 마감은 KST 새벽 05~06시. 06시 전이면 아직 하루 더 앞선 세션이 최신이다.
    미국 공휴일은 반영하지 않는다(주말만) — 그래서 경고용으로만 쓴다.
    """
    d = now.date() - timedelta(days=1)
    if now.hour < 6:
        d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def sessions_behind(asof: str, expected: date) -> int:
    """asof 가 기대 거래일보다 몇 거래일 뒤처졌는지."""
    a = date.fromisoformat(asof)
    if a >= expected:
        return 0
    n, d = 0, a + timedelta(days=1)
    while d <= expected:
        if not _kr_nontrading(d):
            n += 1
        d += timedelta(days=1)
    return n


def check_freshness(data: dict, now: datetime | None = None) -> dict:
    """기준일이 어긋나는지 두 방향으로 본다.

    (1) 절대 기준 — 실행 시각으로 계산한 '마지막 마감 거래일'과 대조.
        전 자산군이 동시에 하루 뒤처지면 상대 비교로는 못 잡는다.
        2026-07-25 사고: 한국·미국 증시가 함께 7/23 에 멈췄는데
        서로 같다는 이유로 '이상 없음' 처리되어 그대로 발행됐다.
    (2) 상대 기준 — 같은 자산군(코스피/코스닥, S&P/나스닥/VIX)은 항상
        같은 날 거래되므로 여기서 어긋나면 확실한 수집 오류다.
        자산군을 넘어선 비교는 하지 않는다(환율은 주말에도 거래됨).
    """
    # (종목들, 허용 오차 일수) — 증시는 반드시 같은 날, 24시간 거래되는
    # 환율·원자재는 야후 반영 시점 차이로 하루까지 벌어질 수 있어 허용한다.
    market = data.get("market", {})
    asofs = {k: v["asof"] for k, v in market.items()
             if v.get("ok") and v.get("asof")}
    if not asofs:
        return {"ok": True, "latest": None, "stale": {}, "groups": {}}

    groups, problems = {}, {}
    print("  기준일:")
    for gname, (keys, tol) in FRESHNESS_GROUPS.items():
        got = {k: asofs[k] for k in keys if k in asofs}
        if not got:
            continue
        uniq = sorted(set(got.values()))
        groups[gname] = uniq[-1]
        spread = (date.fromisoformat(uniq[-1]) - date.fromisoformat(uniq[0])).days
        if spread > tol:
            problems.update({k: a for k, a in got.items() if a < uniq[-1]})
            print(f"    {gname}: {' / '.join(f'{k} {a}' for k, a in sorted(got.items()))}"
                  f"  ⚠️ 기준일 불일치")
        else:
            print(f"    {gname}: {uniq[-1]}")

    # ── 절대 기준: 실행 시각으로 계산한 기대 거래일과 대조 ──
    # 전 자산군이 함께 뒤처지는 경우는 상대 비교로 잡히지 않으므로 이쪽이 주 게이트다.
    if now is not None:
        exp_kr = expected_last_kr_session(now)
        exp_us = expected_last_us_session(now)
        print(f"    기대 거래일: 한국 {exp_kr} / 미국 {exp_us} (실행 {now:%Y-%m-%d %H:%M} KST)")

        kr_asof = groups.get("한국 증시")
        if kr_asof:
            behind = sessions_behind(kr_asof, exp_kr)
            if behind > 0:
                print(f"    ⚠️ 한국 증시 {kr_asof} — 기대 {exp_kr} 보다 {behind}거래일 뒤처짐")
                problems["_kr_stale"] = behind

        us_asof = groups.get("미국 증시")
        if us_asof and date.fromisoformat(us_asof) < exp_us:
            # 미국 공휴일을 반영하지 않으므로 경고만 남기고 게이트로 쓰지 않는다.
            print(f"    · 미국 증시 {us_asof} — 기대 {exp_us} 보다 이전 (미 휴장일 가능성)")

    # 한국 증시가 미국 증시보다 뒤처지면 수집 지연이다.
    # 단, 그 사이가 전부 한국 휴장일이면 정상이므로 경고하지 않는다.
    kr, us = groups.get("한국 증시"), groups.get("미국 증시")
    if kr and us and kr < us:
        kd, ud = date.fromisoformat(kr), date.fromisoformat(us)
        gap_days = [kd + timedelta(days=i) for i in range(1, (ud - kd).days + 1)]
        unexplained = [d for d in gap_days if not _kr_nontrading(d)]
        if unexplained:
            print(f"    ⚠️ 한국 증시가 미국 증시보다 {(ud - kd).days}일 뒤처짐 — 수집 지연 의심"
                  f" (휴장일로 설명 안 되는 날: {', '.join(d.isoformat() for d in unexplained)})")
            problems["_kr_lag"] = (ud - kd).days
        else:
            print(f"    한국 증시 {kr} / 미국 증시 {us} — 한국 휴장일로 설명됨 (정상)")

    if not problems:
        print("    → 이상 없음")

    return {"ok": not problems, "latest": max(asofs.values()),
            "stale": problems, "groups": groups, "asofs": asofs}


# ──────────────────────────────────────────────────────────────
# 방향성 사전 제약 — 수집된 실제 수치를 프롬프트 최상단에 못박는다
# ──────────────────────────────────────────────────────────────
CONSTRAINT_ASSETS = [
    ("KOSPI", "코스피"), ("KOSDAQ", "코스닥"), ("SP500", "S&P500"),
    ("NASDAQ", "나스닥100"), ("WTI", "WTI 유가"), ("USDKRW", "원/달러 환율"),
    ("VIX", "VIX"), ("GOLD", "금"),
]


def build_directional_constraints(data: dict) -> str:
    m = data.get("market", {})
    rows = []
    for key, name in CONSTRAINT_ASSETS:
        rec = m.get(key, {})
        if not rec.get("ok"):
            continue
        pct = rec["change_pct"]
        state = "상승" if pct > 0 else ("하락" if pct < 0 else "보합")
        rows.append(f"- {name}: {rec['close']:,.2f} ({pct:+.2f}%) = {state} "
                    f"[기준일 {rec.get('asof', '?')}]")

    return (
        "======================================================================\n"
        "[최우선 사실 — 아래 수치와 방향을 반드시 따른다]\n"
        f"{chr(10).join(rows)}\n"
        "\n"
        "R-A. 위 수치와 방향은 확정된 사실이다. 검색 기사와 다르면 위 수치를 따른다.\n"
        "R-B. 상승인 자산을 하락/급락으로, 하락인 자산을 상승/급등으로 쓰지 않는다.\n"
        "     headline 뿐 아니라 issues_global · issues_korea 의 title 과 body 에도\n"
        "     똑같이 적용된다. 어긴 항목은 시스템이 폐기한다.\n"
        "R-C. 기사에 나온 장중 급등락과 위 표의 방향이 다르면 위 표를 따른다.\n"
        "     (예: 장중 유가가 급등했어도 위 표가 하락이면 '유가 하락'으로 쓴다)\n"
        "R-D. 위 목록에 있는 자산의 등락률 숫자를 headline 에 직접 쓰지 않는다.\n"
        "     (시스템이 카드로 따로 표시한다)\n"
        "======================================================================\n"
    )


# ──────────────────────────────────────────────────────────────
# 헤드라인 방향 검사 — 헤드라인에만 적용한다
#
# 이슈 본문에는 적용하지 않는다. 뉴스는 원래 자산 간 인과를 서술하므로
# ("유가 급등 → 항공주 약세") 단어만 세면 맞는 문장이 대량으로 폐기된다.
# 헤드라인은 한 문장·단문이라 오탐 위험이 낮고, 폴백 대체재도 있다.
# ──────────────────────────────────────────────────────────────
DIRECTION_KEYWORDS = [
    ("KOSPI",  ["코스피", "KOSPI"]),
    ("KOSDAQ", ["코스닥", "KOSDAQ"]),
    ("SP500",  ["S&P500", "S&P 500", "S&P"]),
    ("NASDAQ", ["나스닥", "NASDAQ"]),
    ("WTI",    ["유가", "WTI", "원유"]),
    # 환율은 제외한다. "환율 하락 = 원화 강세" 처럼 표현마다 의미가 뒤집혀
    # 단어만으로는 판정이 안 된다. 잘못 잡으면 맞는 헤드라인을 버리게 된다.
]
UP_WORDS = ["상승", "급등", "폭등", "강세", "반등", "오르", "올라", "올랐", "상향"]
DOWN_WORDS = ["하락", "급락", "폭락", "약세", "내리", "내려", "떨어", "하향", "붕괴"]

# 절 구분자 — 한 절 안에는 보통 자산 하나와 방향 하나만 들어간다.
# 창(window) 방식은 "유가 상승, S&P500 하락" 에서 옆 절의 단어까지 삼켜 오판했다.
CLAUSE_SPLIT = re.compile(
    r"[,，·;、]|\s+및\s+|\s+반면\s+|\s+그러나\s+|\s+하지만\s+|\s+속\s+|\s+가운데\s+|\s+와중\s+"
)


def check_headline_direction(text: str, data: dict) -> list[str]:
    """절 단위로 자산과 방향 단어를 짝지어 모순만 잡는다."""
    warns = []
    m = data.get("market", {})
    if not text:
        return warns

    clauses = [c for c in CLAUSE_SPLIT.split(text) if c and c.strip()]

    for key, keywords in DIRECTION_KEYWORDS:
        rec = m.get(key, {})
        if not rec.get("ok") or not rec.get("change_pct"):
            continue
        pct = rec["change_pct"]
        agree = UP_WORDS if pct > 0 else DOWN_WORDS
        clash = DOWN_WORDS if pct > 0 else UP_WORDS

        for clause in clauses:
            if not any(kw in clause for kw in keywords):
                continue
            if any(w in clause for w in agree):
                continue                      # 같은 방향 단어가 있으면 정상
            hit = next((w for w in clash if w in clause), None)
            if hit:
                warns.append(
                    f"{key} {pct:+.2f}%({'상승' if pct > 0 else '하락'})인데 "
                    f"'{clause.strip()}' 로 서술"
                )
                break
    return warns


def _issue(d, data: dict | None = None) -> dict | None:
    if not isinstance(d, dict):
        return None
    t = _clip(d.get("title"), LIMITS["issue_title"])
    b = _clip(d.get("body"), LIMITS["issue_body"])
    if not t or not b:
        return None
    if not any(c.isdigit() for c in b):        # 프롬프트 R4의 코드측 강제
        return None

    # 지표 재진술 폐기 — 시스템이 카드로 이미 보여주는 내용이다.
    if is_restatement(t):
        print(f"  ⚠️ 이슈 폐기(지표 재진술): {t}")
        return None

    # 절 단위 방향 검사 — 제목·본문 각각. 창(window) 방식과 달리 옆 절의
    # 방향 단어를 삼키지 않으므로 "유가 급등에 항공주 약세" 같은 정상 문장은 통과한다.
    if data:
        for part, where in ((t, "제목"), (b, "본문")):
            w = check_headline_direction(part, data)
            if w:
                print(f"  ⚠️ 이슈 폐기({where}): {w[0]}")
                return None

    out = {"title": t, "body": b, "source": _clip(d.get("source"), LIMITS["source"])}

    # 카테고리·압력은 고정 선택지에서만 받는다.
    # 분류가 안 되는 이슈는 폐기한다 — 실측상 분류 실패 항목은
    # "S&P500 미세 상승·기타 지수 약세"(지수 재진술, R14 위반),
    # "Fed 금리 결정 임박"(캘린더 중복)처럼 정보가치가 없는 것들이었다.
    cat = str(d.get("category") or "").strip()
    pre = str(d.get("pressure") or "").strip()
    if not data:
        return out
    if cat not in NEWS_CATEGORIES or pre not in NEWS_PRESSURES:
        print(f"  ⚠️ 이슈 폐기(분류 불가): {t[:30]} · category={cat!r} pressure={pre!r}")
        return None

    imp = build_implication(cat, pre, data.get("market", {}))
    if imp:
        out["implication"] = imp
    return out


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
    stars = normalize_stars(ev, fallback=min(3, max(1, stars)))
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

    headline = _clip(raw.get("headline"), LIMITS["headline"])
    if not headline:
        headline = _fallback_headline(data)
    else:
        hw = check_headline_direction(headline, data)
        if hw:
            for w in hw:
                print(f"  ⚠️ 헤드라인 방향 모순: {w}")
            print("  → 안전 폴백 헤드라인으로 교체")
            rejected.append("headline(방향모순)")
            headline = _fallback_headline(data)

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

    issues_g = take("issues_global", lambda d: _issue(d, data), COUNTS["issues_global"])
    issues_k = take("issues_korea",  lambda d: _issue(d, data), COUNTS["issues_korea"])

    # 같은 (카테고리, 압력) 조합의 시사점은 문구가 완전히 동일하다.
    # 같은 사건의 앞뒤가 이슈 두 건으로 들어오면 같은 문단이 반복되므로
    # 첫 건에만 남기고 이후는 뗀다. 제목은 정보가 있으니 그대로 둔다.
    seen_imp = set()
    for it in issues_g + issues_k:
        imp = it.get("implication")
        if not imp:
            continue
        key = (imp["category"], imp["pressure"])
        if key in seen_imp:
            it["implication_dup"] = imp     # 태그 표시용으로만 남긴다
            del it["implication"]
        else:
            seen_imp.add(key)

    return {
        "headline":       headline,
        "cnn_fear_greed": fg,
        "issues_global":  issues_g,
        "issues_korea":   issues_k,
        "calendar":       merge_calendar(
                              take("calendar", lambda d: _event(d, today), COUNTS["calendar"]),
                              today),
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
        freshness_warning=data.get("freshness_warning"),
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


def _issue_title_line(issue: dict) -> str:
    """제목을 원문 링크로 감싼다. source 가 http(s) URL 이 아니면 그냥 텍스트만 낸다."""
    title = _esc(issue.get("title", ""))
    src = str(issue.get("source") or "").strip()
    if src.startswith(("http://", "https://")) and " " not in src:
        # 텔레그램은 href 안에서 " 와 & 를 각각 이스케이프해야 링크가 안 깨진다.
        safe_url = src.replace("&", "&amp;").replace('"', "%22")
        return f'<a href="{safe_url}">{title}</a>'
    return title


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
    ]

    fw = data.get("freshness_warning")
    if fw:
        out.append(f"⚠️ <b>{_esc(fw)}</b>")

    out += [
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
        dot = "▲" if btc["change_24h"] > 0 else ("▼" if btc["change_24h"] < 0 else "⚪")
        out.append(f"· BTC: <b>₩{btc['krw']:,}</b> {dot} {btc['change_24h']:+.2f}% "
                   f"(ATH 대비 {btc['ath_change']}%)")

    issues = (llm.get("issues_global") or []) + (llm.get("issues_korea") or [])
    if issues:
        out += ["", "<b>핵심 이슈</b>"]
        for i in issues:
            out.append(f"· {_issue_title_line(i)}")
            imp = i.get("implication")
            if imp:
                tag = "🔺유리" if imp["pressure"] == "유리" else "🔻불리"
                out.append(f"   <i>[{_esc(imp['category'])} · {tag}]</i>")
                out.append(f"   ↳ {_esc(imp['channel'])}")
                if imp.get("reflected"):
                    out.append(f"   ↳ <i>{_esc(imp['reflected'])}</i>")
            elif i.get("implication_dup"):
                dup = i["implication_dup"]
                tag = "🔺유리" if dup["pressure"] == "유리" else "🔻불리"
                out.append(f"   <i>[{_esc(dup['category'])} · {tag}] (위와 같은 영향 경로)</i>")

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

def load_prompt(is_sunday: bool, data: dict, now: datetime | None = None) -> str:
    """prompt.md 로드. [[IF_SUNDAY]]...[[END_SUNDAY]] 구간을 요일에 따라 남기거나 지운다."""
    with open(os.path.join(BASE_DIR, "prompt.md"), encoding="utf-8") as f:
        p = f.read()

    if is_sunday:
        p = p.replace("[[IF_SUNDAY]]", "").replace("[[END_SUNDAY]]", "")
    else:
        p = re.sub(r"\[\[IF_SUNDAY\]\][\s\S]*?\[\[END_SUNDAY\]\]", "", p)

    meta = data["meta"]
    max_date = (date.fromisoformat(meta["date_iso"]) + timedelta(days=8)).isoformat()

    # 슬롯별 검색어 — 검색 개수는 4건 고정, 겨냥하는 영역만 바꾼다.
    slot = slot_of(now or datetime.now(KST))
    sset = SEARCH_SETS[slot]
    block = "\n".join(f"{i}. {q}" for i, q in enumerate(sset["queries"], 1))
    print(f"  검색 슬롯: {slot} ({sset['label']})")

    constraints = build_directional_constraints(data)
    print("\n── 프롬프트 주입 제약 ──")
    print(constraints.strip())
    print("──────────────────────\n")

    p = constraints + "\n" + p
    return (p.replace("[[SEARCH_QUERIES]]", block)
             .replace("[[SLOT_LABEL]]", sset["label"])
             .replace("[[TODAY_ISO]]", meta["date_iso"])
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

SNAPSHOT_PATH = os.path.join(BASE_DIR, "market_snapshot.json")


def load_snapshot() -> dict:
    """직전 실행에서 저장해둔 시세. 없으면 빈 dict."""
    try:
        with open(SNAPSHOT_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_snapshot(market: dict) -> None:
    """조회 성공한 종목만 저장한다. 실패분으로 기존 기록을 덮어쓰지 않는다."""
    keep = {k: v for k, v in market.items() if v.get("ok") and v.get("asof")}
    if not keep:
        return
    try:
        with open(SNAPSHOT_PATH, "w", encoding="utf-8") as f:
            json.dump(keep, f, ensure_ascii=False, indent=1)
    except Exception as e:
        print(f"  · 스냅샷 저장 실패(무시): {e}")


def apply_snapshot(market: dict, snap: dict) -> list:
    """수집값이 저장본보다 오래됐으면 저장본을 쓴다 — 데이터 역행 방지.

    야후는 이미 제공했던 세션을 다시 감추는 경우가 있다(2026-07-25 에 7/24 종가를
    정상 수신했는데 7/26·7/27 실행에서 7/23 으로 후퇴). 없는 미래를 만들어내는 게
    아니라 '전에 실제로 받았던 더 최신 기록'을 되살리는 것이므로 안전하다.
    """
    restored = []
    for k, cur in market.items():
        old = snap.get(k)
        if not (cur.get("ok") and cur.get("asof")):
            continue
        if not (isinstance(old, dict) and old.get("ok") and old.get("asof")):
            continue
        if old["asof"] > cur["asof"]:
            market[k] = old
            restored.append(f"{k} {cur['asof']}→{old['asof']}")
    return restored


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

    # 야후가 전에 줬던 세션을 다시 감추는 경우가 있어, 직전 실행분보다
    # 오래된 값이 오면 저장본으로 되돌린다. 재시도 판정 전에 먼저 적용한다.
    snap = load_snapshot()
    restored = apply_snapshot(data["market"], snap)
    if restored:
        print(f"  스냅샷 복원(야후 역행 감지): {', '.join(restored)}")

    fresh = check_freshness(data, now)

    # 뒤처진 지표가 있으면 재수집한다. 야후가 최근 세션을 늦게 채우는 경우가 있어
    # 잠시 뒤 재요청이면 해결되는 일이 실제로 있었다.
    # 부분 갱신이 아니라 전 종목을 다시 받는다 — 2026-07-25 사고는 한국·미국이
    # 함께 뒤처진 케이스라 한국만 재수집하면 못 고친다.
    # 재시도 간격을 늘린다(20/40/60초 → 30/60/90초). 야후 지연이 짧으면 여기서 잡힌다.
    for attempt in range(1, 4):
        if fresh["ok"] or "_kr_stale" not in fresh["stale"]:
            break
        wait = 30 * attempt
        print(f"  기준일 지연 감지 → {wait}초 대기 후 재수집 ({attempt}/3)")
        time.sleep(wait)
        retry_market = dc.collect_market()
        for k, v in retry_market.items():
            if v.get("ok"):
                data["market"][k] = v
        apply_snapshot(data["market"], snap)
        fresh = check_freshness(data, now)

    # 이번 회차에서 확보한 가장 최신 시세를 저장한다(다음 회차 역행 방지용).
    save_snapshot(data["market"])

    data["freshness"] = fresh
    rep = fresh["groups"].get("한국 증시") or fresh["groups"].get("미국 증시")
    if rep and data["meta"].get("data_asof") != rep:
        print(f"  data_asof 보정: {data['meta'].get('data_asof')} → {rep} (증시 기준)")
        data["meta"]["data_asof"] = rep

    # 재시도 5분으로도 안 풀리면 발행은 하되 경고를 아주 눈에 띄게 붙인다.
    # 이전엔 여기서 완전히 중단시켰는데, 실전에서 야후 지연이 재시도 시간보다
    # 길게 가는 경우가 있어 '아예 안 오는 것'이 '오래된 수치로 오는 것'보다
    # 오히려 더 불편했다(2026-07-26 실측). 하루 3회 중 다음 회차가 곧 있으므로
    # 완전 차단 대신 강한 경고로 낮춘다.
    if "_kr_stale" in fresh["stale"]:
        behind = fresh["stale"]["_kr_stale"]
        exp = expected_last_kr_session(now)
        got = fresh["groups"].get("한국 증시")
        print(f"  ⚠️ 한국 증시 데이터가 {behind}거래일 뒤처짐 (수집 {got} / 기대 {exp}) "
              f"— 경고와 함께 발행합니다")
        data["freshness_warning"] = (
            f"⚠️ 한국 증시 수치가 {exp} 종가가 아니라 {got} 종가입니다 "
            f"({behind}거래일 지연 · 야후 데이터 지연 추정, 다음 회차에 정상화 예상)"
        )
    elif not fresh["ok"]:
        # 그 밖의 불일치(자산군 내 어긋남 등)도 경고만 남기고 발행한다.
        print(f"  ⚠️ 기준일 불일치가 재시도 후에도 남음: {list(fresh['stale'])}")
        data["freshness_warning"] = (
            "일부 지표가 최신 종가를 반영하지 못했을 수 있습니다 "
            f"(불일치: {', '.join(k for k in fresh['stale'] if not k.startswith('_')) or '한국 증시'})"
        )

    print(f"프롬프트: {'일요일(트렌드 레이더 포함)' if is_sunday else '평일'}")

    try:
        llm_raw = call_llm(load_prompt(is_sunday, data, now))
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
