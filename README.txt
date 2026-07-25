시장 대시보드 파이프라인 — 배치 안내
====================================

레포에 넣을 파일은 5개입니다.

  레포 루트/
  ├── data_collector.py
  ├── generate_dashboard.py
  ├── dashboard_template.html
  ├── prompt.md
  └── .github/workflows/dashboard.yml   <- dashboard.yml 을 이 경로로

★ dashboard.yml 만 .github/workflows/ 안에 두어야 합니다.
  GitHub Actions 가 이 경로만 인식합니다.
  기존 레포에 이미 같은 폴더가 있으니 그 안에 덮어쓰면 됩니다.

★ 삭제할 파일
  prompt_template.md
  prompt_template_weekday.md

★ 이번 수정 사항
  1) setup-python 의 cache: pip 옵션 제거
     — requirements.txt 가 없는 구조라 캐시가 그 파일을 찾다가 실패했습니다.
  2) 한국 수급/업종 섹션 제거
     — pykrx 의 투자자별 수급·업종지수 함수가 KRX 로그인 세션을 요구해서
       (KRX_ID/KRX_PW 없이는 조회 자체가 실패) 이 환경에서 못 씁니다.
       KOSPI/KOSDAQ 지수 자체는 그대로 유지됩니다(yfinance).
       pip install 목록에서 pykrx, pandas 도 제거했습니다.
  3) 검증 스크립트의 오탐 수정
     — "KOSPI 뒤 80자 이내 등락률"로 찾다가 옆 카드(S&P500)의 값까지
       잘못 집어서 "표기 충돌"로 오판하던 버그. 종가 문자열 바로 뒤
       30자로 좁혀서 고쳤습니다.
  4) 최근 1개월 꺾은선 그래프 추가
     — S&P500 · 나스닥100 · KOSPI · USD/KRW · WTI 5종.
       Chart.js(CDN)로 그리며, 조회 실패한 지표만 그래프 없이 문구로 표시됩니다.

★ GitHub Secrets 추가
  TELEGRAM_BOT_TOKEN   @BotFather 에서 봇 생성 후 발급
  TELEGRAM_CHAT_ID     봇에게 메시지 한 번 보낸 뒤
                       api.telegram.org/bot<TOKEN>/getUpdates 에서 확인

★ 삭제 가능한 기존 Secrets
  NAVER_EMAIL, NAVER_PASSWORD, PORTFOLIO_SHEET_ID, GEMINI_API_KEY

★ 첫 실행
  Actions 탭 -> 수동 실행(workflow_dispatch)
  로그에서 아래 확인
    OK  차트 SP500 / NASDAQ / KOSPI / USDKRW / WTI  (5개 포인트 수집)
    stop_reason=end_turn
    산출물 검증 통과

docs 폴더는 참고용입니다. 레포에 넣지 않아도 됩니다.
