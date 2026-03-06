import anthropic
import os

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
filename = os.environ["FILENAME"]
today = os.environ["TODAY"]
update_time = os.environ.get("UPDATE_TIME", "")

with open("prompt_template.md", "r", encoding="utf-8") as f:
    prompt = f.read().replace("[[TODAY]]", today)

print(f"Claude API 호출 중... (모델: claude-sonnet-4-6, 파일: {filename})")

messages = [{"role": "user", "content": prompt}]

# 웹 검색 도구 포함, 멀티턴으로 최종 HTML 받기
while True:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=messages
    )

    # tool_use가 없으면 최종 응답
    if response.stop_reason != "tool_use":
        break

    # tool_use 블록 처리 → messages에 추가
    messages.append({"role": "assistant", "content": response.content})
    tool_results = []
    for block in response.content:
        if block.type == "tool_use":
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": ""  # 검색 결과는 Anthropic 서버에서 자동 처리
            })
    messages.append({"role": "user", "content": tool_results})

# 최종 텍스트 추출
html = ""
for block in response.content:
    if hasattr(block, "text"):
        html += block.text

# HTML 정리
if "<!DOCTYPE" in html:
    html = html[html.index("<!DOCTYPE"):]
if "</html>" in html:
    html = html[:html.index("</html>") + 7]

# 업데이트 시간 삽입
timestamp_html = f'<div style="text-align: right; color: #888; padding: 10px; font-size: 0.9em;">최종 업데이트: {update_time} (KST)</div>'
if "<body>" in html:
    html = html.replace("<body>", f"<body>\n    {timestamp_html}")

with open(filename, "w", encoding="utf-8") as f:
    f.write(html)

print(f"완료: {filename} 저장됨")
