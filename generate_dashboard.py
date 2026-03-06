import anthropic
import os

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
filename = os.environ["FILENAME"]
today = os.environ["TODAY"]
update_time = os.environ.get("UPDATE_TIME", "") # Actions에서 넘겨준 시간 정보

# prompt_template.md 읽기
with open("prompt_template.md", "r", encoding="utf-8") as f:
    prompt = f.read().replace("[[TODAY]]", today)

print(f"Claude API 호출 중... (모델: claude-sonnet-4-6, 파일: {filename})")

# 사용자가 지정한 모델 명칭으로 호출
message = client.messages.create(
    model="claude-sonnet-4-6", 
    max_tokens=8192,
    messages=[
        {"role": "user", "content": prompt}
    ]
)

html = message.content[0].text

# HTML 태그만 추출 (마크다운 코드블록 제거 등)
if "<!DOCTYPE" in html:
    html = html[html.index("<!DOCTYPE"):]
if "</html>" in html:
    html = html[:html.index("</html>") + 7]

# --- 대시보드 상단에 업데이트 일시 삽입 로직 ---
# <body> 태그 바로 뒤에 시간 정보를 삽입하여 디자인을 유지합니다.
timestamp_html = f'<div style="text-align: right; color: #888; padding: 10px; font-size: 0.9em;">최종 업데이트: {update_time} (KST)</div>'
if "<body>" in html:
    html = html.replace("<body>", f"<body>\n    {timestamp_html}")
# ------------------------------------------

with open(filename, "w", encoding="utf-8") as f:
    f.write(html)

print(f"완료: {filename} 저장됨 (업데이트 일시: {update_time})")
