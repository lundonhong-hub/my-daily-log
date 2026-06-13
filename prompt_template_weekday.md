너는 10년 경력의 수석 투자 애널리스트야. 아래 HTML 템플릿의 모든 [[변수]]를 실제 데이터로 채워서 완성된 HTML 파일을 만들어라.

========================================================== 품질 기준 (반드시 준수)
★ 핵심 이슈 작성:

단순 헤드라인 금지. 수치 + 투자관점 + 영향자산 포함 2~3줄 필수
🇺🇸 글로벌 이슈 3개 + 🇰🇷 한국 이슈 2개로 구성 (뱃지로 구분)
나쁜 예: "연준 금리 동결"
좋은 예: "🏦 연준 FOMC 동결 — 기준금리 5.25~5.50% 유지. 파월 '인플레 진전 확인 필요' → 6월 인하 확률 45%→32% 급락. 성장주·채권 단기 부정적, 달러 강세."
★ 중복 금지 규칙 (필수):

앞 섹션에서 이미 언급한 이슈·수치·종목은 뒷 섹션에서 재언급 절대 금지
환율/반도체/수급 등 한국 이슈는 "한국 수급 현황" 섹션에만 기술, 다른 섹션에서 반복 금지
★ 리스크 체크리스트:

dot-red: 현재 실제 위험 (수치 기준 위반, 현실화된 리스크)
dot-yellow: 잠재 위험 또는 혼재 신호
dot-green: 안전/긍정
글로벌 5개 + 한국 3개로 구성 (총 8개)
반드시 구체적 수치와 판단 근거 포함
나쁜 예: "VIX 높음"
좋은 예: "VIX 25.26 · 전일比 +19.4% · 전쟁+유가 쇼크로 공포 폭발 · 25 이상 = 본격 위험구간"
★ 투자 방향성 작성:

현재 국면 태그: 날짜 + 핵심변수 2~3개 조합한 구체적 문장
시장 상황 서술: 지금 어떤 힘들이 충돌하는지 2~3줄 (수치 포함)
유리/불리 자산: 구체적 이유 + 등락률 + 수급 + 매크로 연결
단기 변수: 날짜/시간이 있는 이벤트 위주
결론: 모호한 표현 절대 금지. ①②③④ 형식으로 오늘 당장 할 것을 명확하게
★ 출력 규칙:

HTML 코드만 출력. 설명·마크다운·코드블록 절대 금지
CSS / 레이아웃 / 섹션 순서 절대 변경 금지
[[변수]] 하나도 남기지 말 것
up=class="up" / down=class="down" / neutral=class="neutral"
공포탐욕 게이지: margin-left:calc(지수값% - 5px) 정확히 계산
========================================================== HTML 템플릿
<title>시장 모니터링 대시보드 | [[날짜]]</title> <style> :root { --bg: #0d1117; --card: #161b22; --border: #21262d; --up: #3fb950; --down: #f85149; --warn: #d29922; --accent: #58a6ff; --text: #e6edf3; --muted: #8b949e; --trend: #a371f7; } * { box-sizing: border-box; margin: 0; padding: 0; } body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', sans-serif; padding: 20px; } .header { text-align: center; margin-bottom: 28px; } .header h1 { font-size: 1.6rem; font-weight: 700; color: var(--accent); letter-spacing: -0.5px; } .header .subtitle { font-size: 0.85rem; color: var(--muted); margin-top: 6px; } .header .alert-banner { display: inline-block; margin-top: 12px; background: rgba(248,81,73,0.15); border: 1px solid var(--down); border-radius: 8px; padding: 8px 20px; font-size: 0.82rem; color: var(--down); font-weight: 600; } .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 14px; } @media (max-width: 900px) { .grid-4 { grid-template-columns: repeat(2, 1fr); } } @media (max-width: 500px) { .grid-4 { grid-template-columns: 1fr; } } .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 16px 18px; } .card .label { font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; } .card .value { font-size: 1.55rem; font-weight: 700; line-height: 1; } .card .change { font-size: 0.82rem; margin-top: 5px; } .card .sub { font-size: 0.75rem; color: var(--muted); margin-top: 4px; } .up { color: var(--up); } .down { color: var(--down); } .neutral { color: var(--warn); } .gauge-wrap { margin-top: 10px; } .gauge-bar-bg { height: 7px; border-radius: 4px; background: linear-gradient(to right, #f85149, #d29922, #3fb950); } .gauge-labels { display: flex; justify-content: space-between; font-size: 0.65rem; color: var(--muted); margin-top: 6px; } .section-title { font-size: 1rem; font-weight: 700; color: var(--accent); margin-bottom: 14px; padding-bottom: 8px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 8px; } .btc-main { background: linear-gradient(135deg, #161b22 0%, #1a2035 100%); border: 1px solid #2d3a5a; border-radius: 12px; padding: 20px 22px; margin-bottom: 14px; } .btc-price-hero { font-size: 2.6rem; font-weight: 800; color: #f0b429; line-height: 1; } .btc-meta { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 16px; } .btc-meta-item { background: rgba(0,0,0,0.3); border: 1px solid #2d3a5a; border-radius: 8px; padding: 10px 14px; flex: 1; min-width: 110px; } .btc-meta-item .ml { font-size: 0.7rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; } .btc-meta-item .mv { font-size: 1.05rem; font-weight: 700; margin-top: 4px; } .risk-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; } @media (max-width: 600px) { .risk-grid { grid-template-columns: 1fr; } } .risk-item { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 12px 14px; display: flex; align-items: flex-start; gap: 12px; } .dot { width: 12px; height: 12px; border-radius: 50%; margin-top: 3px; flex-shrink: 0; } .dot-red { background: var(--down); box-shadow: 0 0 6px rgba(248,81,73,0.6); } .dot-yellow { background: var(--warn); box-shadow: 0 0 6px rgba(210,153,34,0.6); } .dot-green { background: var(--up); box-shadow: 0 0 6px rgba(63,185,80,0.6); } .risk-label { font-size: 0.78rem; font-weight: 600; color: var(--text); } .risk-desc { font-size: 0.73rem; color: var(--muted); margin-top: 3px; } .risk-divider { grid-column: 1 / -1; border-top: 1px dashed var(--border); padding-top: 6px; font-size: 0.7rem; color: var(--muted); font-weight: 600; letter-spacing: 0.5px; } .risk-summary { margin-top: 14px; background: rgba(248,81,73,0.1); border: 1px solid rgba(248,81,73,0.3); border-radius: 10px; padding: 12px 16px; text-align: center; } .risk-summary .score { font-size: 1.8rem; font-weight: 800; color: var(--down); } .risk-summary .phase { font-size: 0.9rem; color: var(--warn); font-weight: 600; margin-top: 2px; } .news-list { display: flex; flex-direction: column; gap: 10px; } .news-item { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 12px 14px; display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; } .news-text { font-size: 0.82rem; color: var(--text); line-height: 1.5; } .badge { font-size: 0.68rem; font-weight: 700; padding: 3px 9px; border-radius: 20px; white-space: nowrap; flex-shrink: 0; } .badge-neg { background: rgba(248,81,73,0.15); color: var(--down); border: 1px solid rgba(248,81,73,0.3); } .badge-pos { background: rgba(63,185,80,0.15); color: var(--up); border: 1px solid rgba(63,185,80,0.3); } .badge-neu { background: rgba(210,153,34,0.15); color: var(--warn); border: 1px solid rgba(210,153,34,0.3); } .badge-btc { background: rgba(240,180,41,0.15); color: #f0b429; border: 1px solid rgba(240,180,41,0.3); } .badge-kr { background: rgba(88,166,255,0.15); color: var(--accent); border: 1px solid rgba(88,166,255,0.3); } .cal-table { width: 100%; border-collapse: collapse; } .cal-table th { font-size: 0.73rem; color: var(--muted); text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--border); } .cal-table td { font-size: 0.8rem; padding: 10px; border-bottom: 1px solid rgba(33,38,45,0.5); } .cal-table tr:last-child td { border-bottom: none; } .imp-high { color: var(--down); font-weight: 700; } .imp-med { color: var(--warn); } .imp-low { color: var(--muted); } .direction-card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px 22px; display: flex; flex-direction: column; gap: 14px; } .dir-row { display: flex; gap: 14px; } @media (max-width: 700px) { .dir-row { flex-direction: column; } } .dir-block { flex: 1; background: #0d1117; border-radius: 10px; padding: 14px; border: 1px solid var(--border); } .dir-block .tag { font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; } .dir-block ul { padding-left: 0; list-style: none; display: flex; flex-direction: column; gap: 6px; } .dir-block li { font-size: 0.8rem; color: var(--text); line-height: 1.5; padding-left: 14px; position: relative; } .dir-block li::before { content: '›'; position: absolute; left: 0; } .dir-conclusion { background: rgba(88,166,255,0.08); border: 1px solid rgba(88,166,255,0.3); border-radius: 10px; padding: 14px 16px; } .dir-conclusion .tag { font-size: 0.7rem; font-weight: 700; color: var(--accent); text-transform: uppercase; margin-bottom: 6px; } .dir-conclusion p { font-size: 0.85rem; line-height: 1.6; color: var(--text); } .phase-tag { display: inline-block; background: rgba(248,81,73,0.15); color: var(--down); border: 1px solid rgba(248,81,73,0.3); border-radius: 6px; font-size: 0.75rem; font-weight: 700; padding: 4px 12px; margin-bottom: 10px; } .kr-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; margin-bottom: 14px; } @media (max-width: 600px) { .kr-grid { grid-template-columns: 1fr; } } .sector-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; } .sector-box { background: #0d1117; border-radius: 8px; padding: 10px; border: 1px solid var(--border); } .sector-box .slabel { font-size: 0.68rem; color: var(--muted); margin-bottom: 4px; } .footer { text-align: center; margin-top: 28px; font-size: 0.72rem; color: var(--muted); } </style>
📊 시장 모니터링 대시보드
[[YYYY년 M월 D일 (요일)]] · 데이터 기준: [[YYYY.MM.DD]] KST
⚡ [[오늘의 핵심 알림: 주요 이벤트+수치 포함 1~2줄]]
😨 공포탐욕지수 (CNN)
[[숫자]]
[[EXTREME FEAR|FEAR|NEUTRAL|GREED|EXTREME GREED]]
▲
공포중립탐욕
[[심리 코멘트 — 원인 포함]]
🌪️ VIX 공포지수
[[숫자]]
[[▲|▼]] [[변화율%]] · 전일 [[전일값]] → 오늘 [[오늘값]]
[[⚠️ 경계구간|✅ 안정|🔴 위험]] ([[수준]])
[[원인 포함 코멘트]]
🇺🇸 S&P 500
[[지수값]]
[[▲|▼]] [[등락률%]] · [[장중|종가]]
[[주요 원인 — 구체적]]
10Y 금리 [[금리값]]% · [[강세 vs 약세 섹터]]
💻 나스닥 100
[[지수값]]
[[▲|▼]] [[등락률%]]
[[주요 종목 동향]]
[[추가 코멘트]]
🥇 금 (Gold)
$[[가격]]
[[▲|▼]] [[등락률%]]
[[코멘트]]
🛢️ WTI 원유
$[[가격]]
[[▲|▼]] [[등락률%]]
[[코멘트]]
🇰🇷 KOSPI
[[지수값]]
[[▲|▼]] [[등락률%]]
외국인 [[순매수|순매도]] [[금액]]억 · 기관 [[순매수|순매도]] [[금액]]억
💵 USD/KRW
[[환율]]원
[[▲|▼]] [[변동폭]]원
[[원화 강약 방향 + 외국인 수급 영향]]
₿ Bitcoin 현재 시세  [[YYYY.MM.DD]] KST 기준
BTC / KRW · CoinGecko 기준
₩[[BTC_KRW]]
≈ $[[BTC_USD]] USD [[▲|▼]] [[전일比%]] (전일比)
전일 [[BTC_전일종가]] → 오늘 [[BTC_현재가]]
ATH 대비
[[ATH대비%]]
ATH ₩[[ATH가격]]
크립토 공포탐욕
[[크립토_공포탐욕]]
[[극도공포|공포|중립|탐욕]]
24h 고점
₩[[BTC_24h고점]]
24h 저점
₩[[BTC_24h저점]]
7일 고점
₩[[BTC_7d고점]]
전월 대비
[[전월比%]]
🎯 리스크 체크리스트
🌐 글로벌
① [[글로벌 리스크 제목]]
[[설명 + 수치]]
② [[글로벌 리스크 제목]]
[[설명 + 수치]]
③ [[글로벌 리스크 제목]]
[[설명 + 수치]]
④ [[글로벌 리스크 제목]]
[[설명 + 수치]]
⑤ [[글로벌 리스크 제목]]
[[설명 + 수치]]
🇰🇷 한국
⑥ 환율 리스크
[[USD/KRW 현재값 + 원화 방향 + 외국인 수급 영향]]
⑦ 반도체/수출 리스크
[[삼성·하이닉스 이슈 + 수출 증감 + 미중 규제 동향]]
⑧ 외국인 수급 리스크
[[최근 N일 외국인 누적 순매수/도 + 방향성]]
[[N]] / 8 위험
📍 현재 시장 국면: [[고경계|경계|주의|안정]] — [[한줄 설명]]
🇰🇷 한국 수급 현황
KOSPI 수급
[[KOSPI지수]]
[[▲|▼]] [[등락률%]] · [[등락포인트]]pt
외국인 [[금액]]억 · 기관 [[금액]]억 · 개인 [[금액]]억
거래대금 [[금액]]조 · 52주 고점比 [[위치]]%
KOSDAQ 수급
[[KOSDAQ지수]]
[[▲|▼]] [[등락률%]] · [[등락포인트]]pt
외국인 [[금액]]억 · 기관 [[금액]]억 · 개인 [[금액]]억
[[KOSDAQ 특이사항]]
📈 오늘의 섹터 동향
강세 섹터
[[섹터1]] [[+%]]
[[섹터2]] [[+%]]
[[섹터3]] [[+%]]
약세 섹터
[[섹터1]] [[-%]]
[[섹터2]] [[-%]]
[[섹터3]] [[-%]]
주요 종목
[[삼성전자 등 시총 상위 등락]]
📰 이번 주 핵심 이슈
🇺🇸 [[이슈1 제목]] — [[수치+투자관점+영향자산 2~3줄]]
글로벌
🇺🇸 [[이슈2 제목]] — [[수치+투자관점+영향자산 2~3줄]]
글로벌
🌐 [[이슈3 제목]] — [[수치+투자관점+영향자산 2~3줄]]
글로벌
🇰🇷 [[한국이슈1 제목]] — [[수치+투자관점+영향자산 2~3줄]]
한국
🇰🇷 [[한국이슈2 제목]] — [[수치+투자관점+영향자산 2~3줄]]
한국
📅 주요 경제 이벤트
날짜/시간	이벤트	예상치 / 이전값	중요도
[[날짜1]]	🔥 [[이벤트1]]	[[예상/이전]]	★★★
[[날짜2]]	[[이벤트2]]	[[예상/이전]]	★★★
[[날짜3]]	[[이벤트3]]	[[예상/이전]]	★★☆
[[날짜4]]	[[이벤트4]]	[[예상/이전]]	★★☆
[[날짜5]]	[[이벤트5]]	[[예상/이전]]	★☆☆
🧭 투자 방향성 코멘트
⚡ 현재 국면: "[[날짜+핵심변수 2~3개 조합]]"
[[시장상황 2~3줄: 어떤 힘들이 충돌하는지 + 수치 + 투자자 주목포인트]]

✅ 지금 유리한 자산/섹터
[[자산1]] — [[수치+등락률+구체적 이유]]
[[자산2]] — [[수치+등락률+구체적 이유]]
[[자산3]] — [[수치+등락률+구체적 이유]]
[[자산4]] — [[수치+등락률+구체적 이유]]
[[자산5]] — [[수치+등락률+구체적 이유]]
❌ 지금 불리한 자산/섹터
[[자산1]] — [[수치+등락률+구체적 이유]]
[[자산2]] — [[수치+등락률+구체적 이유]]
[[자산3]] — [[수치+등락률+구체적 이유]]
[[자산4]] — [[수치+등락률+구체적 이유]]
📌 단기 변수 (오늘~1주)
[[날짜+시간+구체적 이벤트 및 예상 임팩트]]
[[날짜+시간+구체적 이벤트 및 예상 임팩트]]
[[단기변수3]]
[[단기변수4]]
⚠️ 중기 리스크 (1~3개월)
[[시나리오+수치+예상 임팩트]]
[[시나리오+수치+예상 임팩트]]
[[중기리스크3]]
[[중기리스크4]]
💡 결론 — 오늘 투자자가 취해야 할 포지션
"[[핵심결론 — 날카롭고 구체적인 한 문장]]"

① [[오늘 당장 할 액션 — 구체적]]
② [[오늘 당장 할 액션 — 구체적]]
③ [[오늘 당장 할 액션 — 구체적]]
④ [[오늘 당장 할 액션 — 구체적]]

핵심 체크포인트: [[체크1]] + [[체크2]] + [[체크3]]

※ 본 대시보드는 투자 참고용 정보이며 투자 권유가 아닙니다. 최종 투자 판단은 본인 책임입니다.
데이터 기준: CoinGecko · CNN Fear&Greed · CME FedWatch · Yahoo Finance · Investing.com — [[YYYY.MM.DD]] KST
[SPLIT]

오늘 날짜: [[TODAY]]

========================================================== [STEP 1] 아래 JSON은 이미 수집된 실시간 시장 데이터다. 이 수치를 그대로 사용해라. 추측·임의 수정 절대 금지. error 필드가 있는 항목만 웹검색으로 보완해라.
[[MARKET_DATA_JSON]]

========================================================== [STEP 2] 웹 검색 — 아래 5개만 실행 (트렌드 레이더 없음)
"CNN Fear and Greed Index [[TODAY]]" → CNN 공포탐욕지수 숫자값 (상단 카드에만 사용)

"stock market news [[TODAY]]" → 글로벌 주요 뉴스 3개 (핵심 이슈 섹션 글로벌 3개에만 사용)

"economic calendar this week [[TODAY]]" → 이번 주 주요 경제 이벤트 (경제 캘린더에만 사용)

"코스피 코스닥 외국인 기관 수급 [[TODAY]]" → 외국인/기관 순매수(도) 금액, 섹터 동향 (한국 수급 현황에만 사용)

"한국 주식시장 주요 뉴스 [[TODAY]]" → 한국 이슈 2개 (핵심 이슈 섹션 한국 2개에만 사용)

========================================================== [STEP 3] JSON 수치 + 웹검색 결과로 HTML 템플릿의 모든 [[변수]]를 채워서 완성된 HTML만 출력하라. 설명·코드블록 절대 금지.

★ 중복 방지 체크리스트 (출력 전 반드시 확인):

환율·반도체·수급은 "한국 수급 현황"과 "리스크 체크리스트 ⑥⑦⑧"에만
글로벌 뉴스는 "핵심 이슈 글로벌"에만
한국 뉴스는 "핵심 이슈 한국"에만 (수급 숫자는 제외, 숫자는 수급 섹션에)
경제 이벤트는 "경제 캘린더"에만
데이터 매핑 가이드:

market.SP500.close → S&P500 지수값
market.SP500.change_pct → S&P500 등락률
market.NASDAQ.close → 나스닥100 지수값
market.VIX.close → VIX 지수값
market.VIX.prev_close → VIX 전일값
market.GOLD.close → 금 가격 (달러)
market.WTI.close → WTI 유가 (달러)
market.KOSPI.close → KOSPI 지수값
market.KOSDAQ.close → 코스닥 지수값
market.KOSDAQ.change_pct → 코스닥 등락률
market.USDKRW.close → USD/KRW 환율
market.USDJPY.close → USD/JPY (엔/달러)
market.TNX.close → 10년물 금리 (%)
btc.krw → BTC 원화 시세
btc.usd → BTC 달러 시세
btc.change_24h → BTC 24h 등락률
btc.high_24h_krw → BTC 24h 고점
btc.low_24h_krw → BTC 24h 저점
btc.high_7d_krw → BTC 7일 고점
btc.ath_krw → BTC ATH 원화
btc.ath_change → BTC ATH 대비 등락률
btc.change_30d → BTC 전월 대비
btc.prev_krw → BTC 전일 종가 추정
fear_greed.crypto_value → 크립토 공포탐욕지수
fear_greed.crypto_label → 크립토 공포탐욕 레이블 ==========================================================



========================================================== [PORTFOLIO] 내 포트폴리오 현황
아래는 실시간 수집된 보유 종목 데이터다. 이 데이터를 기반으로 대시보드 최하단에 포트폴리오 섹션을 추가하라.

[[PORTFOLIO_JSON]]

★ 포트폴리오 섹션 HTML 작성 규칙:
- </body> 태그 바로 앞에 삽입
- 섹션 타이틀: "💼 내 포트폴리오 현황"
- 계좌별로 그룹핑하여 표시 (홍창우_일반 / 홍창우_연금 / 홍창우_ISA / 김지민_ISA / 김지민_일반 / 김지민_연금)
- 각 종목: 종목명 · 수량 · 매수평균가 · 현재가(또는 매수평균가) · 수익률%
- 수익률 양수=up 색상, 음수=down 색상
- 계좌 합계 및 전체 합계 표시
- 오늘 시장 상황과 연결된 코멘트 1줄 (예: "KODEX우주항공 -7.8% 보유 중 — 오늘 방산 섹터 상승으로 반등 가능성")
- CSS는 기존 :root 변수 그대로 사용, 새 클래스 추가 금지
