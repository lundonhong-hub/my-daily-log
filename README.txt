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

★ GitHub Secrets 추가
  TELEGRAM_BOT_TOKEN   @BotFather 에서 봇 생성 후 발급
  TELEGRAM_CHAT_ID     봇에게 메시지 한 번 보낸 뒤
                       api.telegram.org/bot<TOKEN>/getUpdates 에서 확인

★ 삭제 가능한 기존 Secrets
  NAVER_EMAIL, NAVER_PASSWORD, PORTFOLIO_SHEET_ID, GEMINI_API_KEY

★ 첫 실행
  Actions 탭 -> 수동 실행(workflow_dispatch)
  로그에서 아래 3줄 확인
    OK  한국 수급
    OK  섹터
    stop_reason=end_turn

docs 폴더는 참고용입니다. 레포에 넣지 않아도 됩니다.
