너는 10년 경력의 수석 투자 애널리스트야. 아래 HTML 템플릿의 모든 [[변수]]를 실제 데이터로 채워서 완성된 HTML 파일을 만들어라.

==========================================================
품질 기준 (반드시 준수)
==========================================================

★ 핵심 이슈 작성:
- 단순 헤드라인 금지. 수치 + 투자관점 + 영향자산 포함 2~3줄 필수
- 나쁜 예: "연준 금리 동결"
- 좋은 예: "🏦 연준 FOMC 동결 — 기준금리 5.25~5.50% 유지. 파월 '인플레 진전 확인 필요' → 6월 인하 확률 45%→32% 급락. 성장주·채권 단기 부정적, 달러 강세."

★ 리스크 체크리스트:
- dot-red: 현재 실제 위험 (수치 기준 위반, 현실화된 리스크)
- dot-yellow: 잠재 위험 또는 혼재 신호
- dot-green: 안전/긍정
- 반드시 구체적 수치와 판단 근거 포함
- 나쁜 예: "VIX 높음"
- 좋은 예: "VIX 25.26 · 전일比 +19.4% · 전쟁+유가 쇼크로 공포 폭발 · 25 이상 = 본격 위험구간"

★ 투자 방향성 작성:
- 현재 국면 태그: 날짜 + 핵심변수 2~3개 조합한 구체적 문장
  예: "이란 전쟁 6일차 · 유가 급등 · 공포 극대화 · NFP D-Day"
- 시장 상황 서술: 지금 어떤 힘들이 충돌하는지 2~3줄 (수치 포함)
- 유리/불리 자산: 구체적 이유 + 등락률 + 수급 + 매크로 연결
- 단기 변수: 날짜/시간이 있는 이벤트 위주
- 결론: 모호한 표현 절대 금지. ①②③④ 형식으로 오늘 당장 할 것을 명확하게

★ 출력 규칙:
- HTML 코드만 출력. 설명·마크다운·코드블록 절대 금지
- CSS / 레이아웃 / 섹션 순서 절대 변경 금지
- [[변수]] 하나도 남기지 말 것
- up=class="up" / down=class="down" / neutral=class="neutral"
- 공포탐욕 게이지: margin-left:calc(지수값% - 5px) 정확히 계산

==========================================================
HTML 템플릿
==========================================================

<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>시장 모니터링 대시보드 | [[날짜]]</title>
<style>
  :root {
    --bg: #0d1117; --card: #161b22; --border: #21262d;
    --up: #3fb950; --down: #f85149; --warn: #d29922;
    --accent: #58a6ff; --text: #e6edf3; --muted: #8b949e;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', sans-serif; padding: 20px; }
  .header { text-align: center; margin-bottom: 28px; }
  .header h1 { font-size: 1.6rem; font-weight: 700; color: var(--accent); letter-spacing: -0.5px; }
  .header .subtitle { font-size: 0.85rem; color: var(--muted); margin-top: 6px; }
  .header .alert-banner { display: inline-block; margin-top: 12px; background: rgba(248,81,73,0.15); border: 1px solid var(--down); border-radius: 8px; padding: 8px 20px; font-size: 0.82rem; color: var(--down); font-weight: 600; }
  .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 14px; }
  @media (max-width: 900px) { .grid-4 { grid-template-columns: repeat(2, 1fr); } }
  @media (max-width: 500px) { .grid-4 { grid-template-columns: 1fr; } }
  .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 16px 18px; }
  .card .label { font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
  .card .value { font-size: 1.55rem; font-weight: 700; line-height: 1; }
  .card .change { font-size: 0.82rem; margin-top: 5px; }
  .card .sub { font-size: 0.75rem; color: var(--muted); margin-top: 4px; }
  .up { color: var(--up); } .down { color: var(--down); } .neutral { color: var(--warn); }
  .gauge-wrap { margin-top: 10px; }
  .gauge-bar-bg { height: 7px; border-radius: 4px; background: linear-gradient(to right, #f85149, #d29922, #3fb950); }
  .gauge-labels { display: flex; justify-content: space-between; font-size: 0.65rem; color: var(--muted); margin-top: 6px; }
  .section-title { font-size: 1rem; font-weight: 700; color: var(--accent); margin-bottom: 14px; padding-bottom: 8px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 8px; }
  .btc-main { background: linear-gradient(135deg, #161b22 0%, #1a2035 100%); border: 1px solid #2d3a5a; border-radius: 12px; padding: 20px 22px; margin-bottom: 14px; }
  .btc-price-hero { font-size: 2.6rem; font-weight: 800; color: #f0b429; line-height: 1; }
  .btc-meta { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 16px; }
  .btc-meta-item { background: rgba(0,0,0,0.3); border: 1px solid #2d3a5a; border-radius: 8px; padding: 10px 14px; flex: 1; min-width: 110px; }
  .btc-meta-item .ml { font-size: 0.7rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; }
  .btc-meta-item .mv { font-size: 1.05rem; font-weight: 700; margin-top: 4px; }
  .risk-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
  @media (max-width: 600px) { .risk-grid { grid-template-columns: 1fr; } }
  .risk-item { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 12px 14px; display: flex; align-items: flex-start; gap: 12px; }
  .dot { width: 12px; height: 12px; border-radius: 50%; margin-top: 3px; flex-shrink: 0; }
  .dot-red { background: var(--down); box-shadow: 0 0 6px rgba(248,81,73,0.6); }
  .dot-yellow { background: var(--warn); box-shadow: 0 0 6px rgba(210,153,34,0.6); }
  .dot-green { background: var(--up); box-shadow: 0 0 6px rgba(63,185,80,0.6); }
  .risk-label { font-size: 0.78rem; font-weight: 600; color: var(--text); }
  .risk-desc { font-size: 0.73rem; color: var(--muted); margin-top: 3px; }
  .risk-summary { margin-top: 14px; background: rgba(248,81,73,0.1); border: 1px solid rgba(248,81,73,0.3); border-radius: 10px; padding: 12px 16px; text-align: center; }
  .risk-summary .score { font-size: 1.8rem; font-weight: 800; color: var(--down); }
  .risk-summary .phase { font-size: 0.9rem; color: var(--warn); font-weight: 600; margin-top: 2px; }
  .news-list { display: flex; flex-direction: column; gap: 10px; }
  .news-item { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 12px 14px; display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
  .news-text { font-size: 0.82rem; color: var(--text); line-height: 1.5; }
  .badge { font-size: 0.68rem; font-weight: 700; padding: 3px 9px; border-radius: 20px; white-space: nowrap; flex-shrink: 0; }
  .badge-neg { background: rgba(248,81,73,0.15); color: var(--down); border: 1px solid rgba(248,81,73,0.3); }
  .badge-pos { background: rgba(63,185,80,0.15); color: var(--up); border: 1px solid rgba(63,185,80,0.3); }
  .badge-neu { background: rgba(210,153,34,0.15); color: var(--warn); border: 1px solid rgba(210,153,34,0.3); }
  .badge-btc { background: rgba(240,180,41,0.15); color: #f0b429; border: 1px solid rgba(240,180,41,0.3); }
  .cal-table { width: 100%; border-collapse: collapse; }
  .cal-table th { font-size: 0.73rem; color: var(--muted); text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--border); }
  .cal-table td { font-size: 0.8rem; padding: 10px; border-bottom: 1px solid rgba(33,38,45,0.5); }
  .cal-table tr:last-child td { border-bottom: none; }
  .imp-high { color: var(--down); font-weight: 700; } .imp-med { color: var(--warn); } .imp-low { color: var(--muted); }
  .direction-card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px 22px; display: flex; flex-direction: column; gap: 14px; }
  .dir-row { display: flex; gap: 14px; }
  @media (max-width: 700px) { .dir-row { flex-direction: column; } }
  .dir-block { flex: 1; background: #0d1117; border-radius: 10px; padding: 14px; border: 1px solid var(--border); }
  .dir-block .tag { font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
  .dir-block ul { padding-left: 0; list-style: none; display: flex; flex-direction: column; gap: 6px; }
  .dir-block li { font-size: 0.8rem; color: var(--text); line-height: 1.5; padding-left: 14px; position: relative; }
  .dir-block li::before { content: '›'; position: absolute; left: 0; }
  .dir-conclusion { background: rgba(88,166,255,0.08); border: 1px solid rgba(88,166,255,0.3); border-radius: 10px; padding: 14px 16px; }
  .dir-conclusion .tag { font-size: 0.7rem; font-weight: 700; color: var(--accent); text-transform: uppercase; margin-bottom: 6px; }
  .dir-conclusion p { font-size: 0.85rem; line-height: 1.6; color: var(--text); }
  .phase-tag { display: inline-block; background: rgba(248,81,73,0.15); color: var(--down); border: 1px solid rgba(248,81,73,0.3); border-radius: 6px; font-size: 0.75rem; font-weight: 700; padding: 4px 12px; margin-bottom: 10px; }
  .footer { text-align: center; margin-top: 28px; font-size: 0.72rem; color: var(--muted); }
</style>
</head>
<body>
<div class="header">
  <h1>📊 시장 모니터링 대시보드</h1>
  <div class="subtitle">[[YYYY년 M월 D일 (요일)]] · 데이터 기준: [[YYYY.MM.DD]] KST</div>
  <div class="alert-banner">⚡ [[오늘의 핵심 알림: 주요 이벤트+수치 포함 1~2줄]]</div>
</div>
<div class="grid-4">
  <div class="card">
    <div class="label">😨 공포탐욕지수 (CNN)</div>
    <div class="value [[up|down|neutral]]">[[숫자]]</div>
    <div class="change [[up|down|neutral]]">[[EXTREME FEAR|FEAR|NEUTRAL|GREED|EXTREME GREED]]</div>
    <div class="gauge-wrap">
      <div class="gauge-bar-bg"></div>
      <div style="margin-top:4px; margin-left:calc([[지수값]]% - 5px)"><span style="font-size:10px;color:#e6edf3;">▲</span></div>
      <div class="gauge-labels"><span>공포</span><span>중립</span><span>탐욕</span></div>
    </div>
    <div class="sub">[[심리 코멘트 — 원인 포함]]</div>
  </div>
  <div class="card">
    <div class="label">🌪️ VIX 공포지수</div>
    <div class="value [[up|down|neutral]]">[[숫자]]</div>
    <div class="change [[up|down|neutral]]">[[▲|▼]] [[변화율%]] · 전일 [[전일값]] → 오늘 [[오늘값]]</div>
    <div class="sub" style="margin-top:8px; color:var(--[[warn|down|up]])">[[⚠️ 경계구간|✅ 안정|🔴 위험]] ([[수준]])</div>
    <div class="sub">[[원인 포함 코멘트]]</div>
  </div>
  <div class="card">
    <div class="label">🇺🇸 S&P 500</div>
    <div class="value [[up|down|neutral]]">[[지수값]]</div>
    <div class="change [[up|down|neutral]]">[[▲|▼]] [[등락률%]] · [[장중|종가]]</div>
    <div class="sub">[[주요 원인 — 구체적]]</div>
    <div class="sub" style="color:var(--warn)">10Y 금리 [[금리값]]% · [[강세 vs 약세 섹터]]</div>
  </div>
  <div class="card">
    <div class="label">💻 나스닥 100</div>
    <div class="value [[up|down|neutral]]">[[지수값]]</div>
    <div class="change [[up|down|neutral]]">[[▲|▼]] [[등락률%]]</div>
    <div class="sub">[[주요 종목명 + 등락률]]</div>
    <div class="sub" style="color:var(--[[down|up]])">[[추가 코멘트]]</div>
  </div>
</div>
<div class="grid-4" style="margin-bottom:28px;">
  <div class="card">
    <div class="label">🥇 금 (Gold)</div>
    <div class="value [[up|down|neutral]]">$[[가격]]</div>
    <div class="change [[up|down|neutral]]">[[▲|▼]] [[등락률%]]</div>
    <div class="sub">[[원인 포함 코멘트]]</div>
  </div>
  <div class="card">
    <div class="label">🛢️ WTI 원유</div>
    <div class="value [[up|down|neutral]]">$[[가격]]</div>
    <div class="change [[up|down|neutral]]">[[▲|▼]] [[등락률%]]</div>
    <div class="sub">[[원인 포함 코멘트]]</div>
  </div>
  <div class="card">
    <div class="label">🇰🇷 KOSPI</div>
    <div class="value [[up|down|neutral]]">[[지수값]]</div>
    <div class="change [[up|down|neutral]]">[[▲|▼]] [[등락률%]]</div>
    <div class="sub">외국인 [[순매수|순매도]] [[금액]] · [[주요 종목 동향]]</div>
  </div>
  <div class="card">
    <div class="label">💵 USD/KRW</div>
    <div class="value [[up|down|neutral]]">[[환율]]원</div>
    <div class="change [[up|down|neutral]]">[[▲|▼]] [[전일比변화]] · [[방향 코멘트]]</div>
    <div class="sub">[[원인 포함 코멘트]]</div>
  </div>
</div>
<div style="margin-bottom:28px;">
  <div class="section-title">₿ Bitcoin 현재 시세 &nbsp;<span style="font-size:0.75rem; color:var(--muted); font-weight:400;">[[YYYY.MM.DD]] KST 기준</span></div>
  <div class="btc-main">
    <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:20px; margin-bottom:20px;">
      <div>
        <div style="font-size:0.75rem; color:var(--muted); text-transform:uppercase; letter-spacing:0.8px; margin-bottom:10px;">BTC / KRW · 업비트 기준</div>
        <div class="btc-price-hero">₩[[BTC_KRW]]</div>
        <div style="margin-top:10px; display:flex; gap:16px; flex-wrap:wrap;">
          <span style="font-size:1rem; color:#aaa;">≈ <strong style="color:#e6edf3;">$[[BTC_USD]]</strong> USD</span>
          <span style="font-size:1rem; color:var(--[[up|down]]); font-weight:700;">[[▲|▼]] [[전일比%]] (전일比)</span>
        </div>
        <div style="margin-top:8px; font-size:0.78rem; color:var(--muted);">전일 [[BTC_전일종가]] → 오늘 [[BTC_현재가]]</div>
      </div>
      <div style="display:flex; flex-direction:column; gap:8px; align-items:flex-end;">
        <div style="background:rgba(248,81,73,0.12); border:1px solid rgba(248,81,73,0.3); border-radius:8px; padding:8px 14px; text-align:center;">
          <div style="font-size:0.68rem; color:var(--muted);">ATH 대비</div>
          <div style="font-size:1.3rem; font-weight:800; color:var(--down);">[[ATH대비%]]</div>
          <div style="font-size:0.68rem; color:var(--muted);">ATH ₩[[ATH가격]]</div>
        </div>
        <div style="background:rgba(210,153,34,0.12); border:1px solid rgba(210,153,34,0.3); border-radius:8px; padding:8px 14px; text-align:center;">
          <div style="font-size:0.68rem; color:var(--muted);">공포탐욕지수</div>
          <div style="font-size:1.3rem; font-weight:800; color:var(--down);">[[크립토_공포탐욕]]</div>
          <div style="font-size:0.68rem; color:var(--down); font-weight:600;">[[극도공포|공포|중립|탐욕]]</div>
        </div>
      </div>
    </div>
    <div style="background:rgba(0,0,0,0.25); border:1px solid #2d3a5a; border-radius:10px; padding:14px 16px; margin-bottom:16px;">
      <div style="font-size:0.72rem; color:var(--muted); text-transform:uppercase; letter-spacing:0.5px; margin-bottom:10px;">📡 소스별 현재 시세 비교</div>
      <div style="display:grid; grid-template-columns:repeat(3,1fr); gap:10px;">
        <div style="text-align:center;">
          <div style="font-size:0.7rem; color:var(--muted); margin-bottom:4px;">CoinGecko</div>
          <div style="font-size:1rem; font-weight:700; color:#f0b429;">₩[[CG_KRW]]</div>
          <div style="font-size:0.68rem; color:var(--[[up|down]]);">[[CG_24h%]] 24h</div>
        </div>
        <div style="text-align:center; border-left:1px solid #2d3a5a; border-right:1px solid #2d3a5a;">
          <div style="font-size:0.7rem; color:var(--muted); margin-bottom:4px;">CoinMarketCap</div>
          <div style="font-size:1rem; font-weight:700; color:#f0b429;">₩[[CMC_KRW]]</div>
          <div style="font-size:0.68rem; color:var(--[[up|down]]);">[[CMC_24h%]] 24h</div>
        </div>
        <div style="text-align:center;">
          <div style="font-size:0.7rem; color:var(--muted); margin-bottom:4px;">Coinbase</div>
          <div style="font-size:1rem; font-weight:700; color:#f0b429;">₩[[CB_KRW]]</div>
          <div style="font-size:0.68rem; color:var(--[[up|down]]);">[[CB_24h%]] 24h</div>
        </div>
      </div>
      <div style="margin-top:10px; font-size:0.72rem; color:var(--muted); text-align:center;">※ 소스별 집계 방식 차이로 시세 편차 발생 · 업비트 실시간 확인 권장</div>
    </div>
    <div class="btc-meta">
      <div class="btc-meta-item"><div class="ml">24h 고점</div><div class="mv" style="color:var(--up);">₩[[BTC_24h고점]]</div></div>
      <div class="btc-meta-item"><div class="ml">24h 저점</div><div class="mv" style="color:var(--down);">₩[[BTC_24h저점]]</div></div>
      <div class="btc-meta-item"><div class="ml">7일 고점</div><div class="mv" style="color:#f0b429;">₩[[BTC_7d고점]]</div></div>
      <div class="btc-meta-item"><div class="ml">전월 대비</div><div class="mv" style="color:var(--[[up|down]]);">[[전월比%]]</div></div>
      <div class="btc-meta-item"><div class="ml">Coinbase 프리미엄</div><div class="mv" style="color:var(--[[up|down]]);">[[프리미엄값 + 해석]]</div></div>
    </div>
  </div>
</div>
<div style="margin-bottom:28px;">
  <div class="section-title">🎯 리스크 체크리스트</div>
  <div class="risk-grid">
    <div class="risk-item"><div class="dot [[dot-red|dot-yellow|dot-green]]"></div><div><div class="risk-label">① [[제목]]</div><div class="risk-desc">[[수치+근거+판단]]</div></div></div>
    <div class="risk-item"><div class="dot [[dot-red|dot-yellow|dot-green]]"></div><div><div class="risk-label">② [[제목]]</div><div class="risk-desc">[[수치+근거+판단]]</div></div></div>
    <div class="risk-item"><div class="dot [[dot-red|dot-yellow|dot-green]]"></div><div><div class="risk-label">③ [[제목]]</div><div class="risk-desc">[[수치+근거+판단]]</div></div></div>
    <div class="risk-item"><div class="dot [[dot-red|dot-yellow|dot-green]]"></div><div><div class="risk-label">④ [[제목]]</div><div class="risk-desc">[[수치+근거+판단]]</div></div></div>
    <div class="risk-item"><div class="dot [[dot-red|dot-yellow|dot-green]]"></div><div><div class="risk-label">⑤ [[제목]]</div><div class="risk-desc">[[수치+근거+판단]]</div></div></div>
    <div class="risk-item"><div class="dot [[dot-red|dot-yellow|dot-green]]"></div><div><div class="risk-label">⑥ [[제목]]</div><div class="risk-desc">[[수치+근거+판단]]</div></div></div>
    <div class="risk-item"><div class="dot [[dot-red|dot-yellow|dot-green]]"></div><div><div class="risk-label">⑦ [[제목]]</div><div class="risk-desc">[[수치+근거+판단]]</div></div></div>
    <div class="risk-item"><div class="dot [[dot-red|dot-yellow|dot-green]]"></div><div><div class="risk-label">⑧ [[제목]]</div><div class="risk-desc">[[수치+근거+판단]]</div></div></div>
  </div>
  <div class="risk-summary">
    <div class="score">[[N]] / 8 위험</div>
    <div class="phase">📍 현재 시장 국면: [[고경계|경계|주의|안정]] — [[핵심 리스크 한줄 요약]]</div>
  </div>
</div>
<div style="margin-bottom:28px;">
  <div class="section-title">📰 이번 주 핵심 이슈</div>
  <div class="news-list">
    <div class="news-item"><div class="news-text"><strong>[[이슈1 제목]]</strong> — [[수치+투자관점+영향자산 2~3줄]]</div><span class="badge [[badge-neg|badge-pos|badge-neu|badge-btc]]">[[레이블]]</span></div>
    <div class="news-item"><div class="news-text"><strong>[[이슈2 제목]]</strong> — [[수치+투자관점+영향자산 2~3줄]]</div><span class="badge [[badge-neg|badge-pos|badge-neu|badge-btc]]">[[레이블]]</span></div>
    <div class="news-item"><div class="news-text"><strong>[[이슈3 제목]]</strong> — [[수치+투자관점+영향자산 2~3줄]]</div><span class="badge [[badge-neg|badge-pos|badge-neu|badge-btc]]">[[레이블]]</span></div>
    <div class="news-item"><div class="news-text"><strong>[[이슈4 제목]]</strong> — [[수치+투자관점+영향자산 2~3줄]]</div><span class="badge [[badge-neg|badge-pos|badge-neu|badge-btc]]">[[레이블]]</span></div>
    <div class="news-item"><div class="news-text"><strong>[[이슈5 제목]]</strong> — [[수치+투자관점+영향자산 2~3줄]]</div><span class="badge [[badge-neg|badge-pos|badge-neu|badge-btc]]">[[레이블]]</span></div>
  </div>
</div>
<div style="margin-bottom:28px;">
  <div class="section-title">📅 주요 경제 이벤트</div>
  <div class="card" style="padding:0; overflow:hidden;">
    <table class="cal-table">
      <thead><tr><th>날짜/시간</th><th>이벤트</th><th>예상치 / 이전값</th><th>중요도</th></tr></thead>
      <tbody>
        <tr><td style="color:var(--down); font-weight:700;">[[날짜1]]</td><td>🔥 [[이벤트1]]</td><td>[[예상/이전]]</td><td class="imp-high">★★★</td></tr>
        <tr><td>[[날짜2]]</td><td>[[이벤트2]]</td><td>[[예상/이전]]</td><td class="imp-high">★★★</td></tr>
        <tr><td>[[날짜3]]</td><td>[[이벤트3]]</td><td>[[예상/이전]]</td><td class="imp-med">★★☆</td></tr>
        <tr><td>[[날짜4]]</td><td>[[이벤트4]]</td><td>[[예상/이전]]</td><td class="imp-med">★★☆</td></tr>
        <tr><td>[[날짜5]]</td><td>[[이벤트5]]</td><td>[[예상/이전]]</td><td class="imp-low">★☆☆</td></tr>
      </tbody>
    </table>
  </div>
</div>
<div style="margin-bottom:28px;">
  <div class="section-title">🧭 투자 방향성 코멘트</div>
  <div class="direction-card">
    <div>
      <div class="phase-tag">⚡ 현재 국면: "[[날짜+핵심변수 2~3개 조합]]"</div>
      <p style="font-size:0.85rem; color:var(--muted); line-height:1.7;">[[시장상황 2~3줄: 어떤 힘들이 충돌하는지 + 수치 + 투자자 주목포인트]]</p>
    </div>
    <div class="dir-row">
      <div class="dir-block" style="border-color:rgba(63,185,80,0.3);">
        <div class="tag" style="color:var(--up)">✅ 지금 유리한 자산/섹터</div>
        <ul>
          <li><strong>[[자산1]]</strong> — [[수치+등락률+구체적 이유]]</li>
          <li><strong>[[자산2]]</strong> — [[수치+등락률+구체적 이유]]</li>
          <li><strong>[[자산3]]</strong> — [[수치+등락률+구체적 이유]]</li>
          <li><strong>[[자산4]]</strong> — [[수치+등락률+구체적 이유]]</li>
          <li><strong>[[자산5]]</strong> — [[수치+등락률+구체적 이유]]</li>
        </ul>
      </div>
      <div class="dir-block" style="border-color:rgba(248,81,73,0.3);">
        <div class="tag" style="color:var(--down)">❌ 지금 불리한 자산/섹터</div>
        <ul>
          <li><strong>[[자산1]]</strong> — [[수치+등락률+구체적 이유]]</li>
          <li><strong>[[자산2]]</strong> — [[수치+등락률+구체적 이유]]</li>
          <li><strong>[[자산3]]</strong> — [[수치+등락률+구체적 이유]]</li>
          <li><strong>[[자산4]]</strong> — [[수치+등락률+구체적 이유]]</li>
        </ul>
      </div>
    </div>
    <div class="dir-row">
      <div class="dir-block">
        <div class="tag" style="color:var(--warn)">📌 단기 변수 (오늘~1주)</div>
        <ul>
          <li>[[날짜+시간+구체적 이벤트 및 예상 임팩트]]</li>
          <li>[[날짜+시간+구체적 이벤트 및 예상 임팩트]]</li>
          <li>[[단기변수3]]</li>
          <li>[[단기변수4]]</li>
        </ul>
      </div>
      <div class="dir-block">
        <div class="tag" style="color:var(--down)">⚠️ 중기 리스크 (1~3개월)</div>
        <ul>
          <li>[[시나리오+수치+예상 임팩트]]</li>
          <li>[[시나리오+수치+예상 임팩트]]</li>
          <li>[[중기리스크3]]</li>
          <li>[[중기리스크4]]</li>
        </ul>
      </div>
    </div>
    <div class="dir-conclusion">
      <div class="tag">💡 결론 — 오늘 투자자가 취해야 할 포지션</div>
      <p>
        <strong>"[[핵심결론 — 날카롭고 구체적인 한 문장]]"</strong><br><br>
        ① [[오늘 당장 할 액션 — 구체적]]<br>
        ② [[오늘 당장 할 액션 — 구체적]]<br>
        ③ [[오늘 당장 할 액션 — 구체적]]<br>
        ④ [[오늘 당장 할 액션 — 구체적]]
        <br><br>
        핵심 체크포인트: <strong>[[체크1]] + [[체크2]] + [[체크3]]</strong>
      </p>
    </div>
  </div>
</div>
<div class="footer">
  ※ 본 대시보드는 투자 참고용 정보이며 투자 권유가 아닙니다. 최종 투자 판단은 본인 책임입니다.<br>
  데이터 기준: CoinGecko · CoinMarketCap · Coinbase · CNN Fear&Greed · CME FedWatch · Yahoo Finance · Investing.com — [[YYYY.MM.DD]] KST
</div>
</body>
</html>

[SPLIT]

오늘 날짜: [[TODAY]]

==========================================================
[STEP 1] 아래 JSON은 이미 수집된 실시간 시장 데이터다. 이 수치를 그대로 사용해라.
추측·임의 수정 절대 금지. error 필드가 있는 항목만 웹검색으로 보완해라.
==========================================================

[[MARKET_DATA_JSON]]

==========================================================
[STEP 2] 웹 검색 — 아래 3개만 실행 (JSON에 없는 데이터)
==========================================================

1. "CNN Fear and Greed Index [[TODAY]]" → CNN 공포탐욕지수 숫자값
2. "stock market news [[TODAY]]" → 오늘 주요 시장 뉴스 5가지 (투자관점 포함)
3. "economic calendar this week [[TODAY]]" → 이번 주 주요 경제 이벤트

==========================================================
[STEP 3] JSON 수치 + 웹검색 결과로 HTML 템플릿의 모든 [[변수]]를 채워서
완성된 HTML만 출력하라. 설명·코드블록 절대 금지.

데이터 매핑 가이드:
- market.SP500.close → S&P500 지수값
- market.SP500.change_pct → S&P500 등락률
- market.NASDAQ.close → 나스닥100 지수값
- market.VIX.close → VIX 지수값
- market.VIX.prev_close → VIX 전일값
- market.GOLD.close → 금 가격 (달러)
- market.WTI.close → WTI 유가 (달러)
- market.KOSPI.close → KOSPI 지수값
- market.USDKRW.close → USD/KRW 환율
- market.TNX.close → 10년물 금리 (%)
- btc.krw → BTC 원화 시세
- btc.usd → BTC 달러 시세
- btc.change_24h → BTC 24h 등락률
- btc.high_24h_krw → BTC 24h 고점
- btc.low_24h_krw → BTC 24h 저점
- btc.high_7d_krw → BTC 7일 고점
- btc.ath_krw → BTC ATH 원화
- btc.ath_change → BTC ATH 대비 등락률
- btc.change_30d → BTC 전월 대비
- btc.prev_krw → BTC 전일 종가 추정
- fear_greed.crypto_value → 크립토 공포탐욕지수
- fear_greed.crypto_label → 크립토 공포탐욕 레이블
==========================================================
