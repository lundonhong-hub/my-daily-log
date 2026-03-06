import anthropic
import os
import json

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
filename = os.environ["FILENAME"]
today = os.environ["TODAY"]
update_time = os.environ.get("UPDATE_TIME", "")

with open("prompt_template.md", "r", encoding="utf-8") as f:
    prompt = f.read().replace("[[TODAY]]", today)

print(f"Claude API 호출 중... (모델: claude-sonnet-4-6, 파일: {filename})")

# web_search_20250305는 서버사이드 도구 → tool_result를 직접 돌려줄 필요 없음
# 대신 stop_reason이 "end_turn"이 될 때까지 응답의 content 블록을 누적
messages = [{"role": "user", "content": prompt}]

while True:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=16000,  # HTML 전체 출력에 충분한 토큰
        tools=[{
            "type": "web_search_20250305",
            "name": "web_search"
        }],
        messages=messages
    )

    print(f"  → stop_reason: {response.stop_reason}")
    for block in response.content:
        print(f"     block type: {block.type}")

    # 웹검색 도구는 stop_reason이 "tool_use"가 아니라 "end_turn"으로 끝남
    # 단, 중간에 tool_use 블록이 있을 수 있으므로 assistant 응답을 messages에 추가
    messages.append({"role": "assistant", "content": response.content})

    if response.stop_reason == "end_turn":
        break

    # 혹시 tool_use stop_reason인 경우 (다른 tool 타입 대비 방어 코드)
    if response.stop_reason == "tool_use":
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": "검색 완료"
                })
        if tool_results:
            messages.append({"role": "user", "content": tool_results})
        continue

    # 그 외 stop_reason은 종료
    break

# 최종 응답에서 텍스트 블록만 추출
html = ""
for block in response.content:
    if hasattr(block, "text") and block.text:
        html += block.text

print(f"추출된 HTML 길이: {len(html)}자")

# HTML이 비어있으면 전체 messages에서 마지막 텍스트 찾기
if len(html) < 100:
    print("경고: HTML이 짧음. 전체 메시지에서 재탐색...")
    for msg in reversed(messages):
        if msg["role"] == "assistant":
            content = msg["content"]
            if isinstance(content, list):
                for block in content:
                    if hasattr(block, "text") and block.text and len(block.text) > 100:
                        html = block.text
                        break
            if len(html) > 100:
                break

# HTML 마크다운 코드블록 제거
html = html.strip()
if html.startswith("```"):
    html = html[html.find("\n")+1:]
if html.endswith("```"):
    html = html[:html.rfind("```")]

# DOCTYPE부터 자르기
if "<!DOCTYPE" in html:
    html = html[html.index("<!DOCTYPE"):]
elif "<!doctype" in html.lower():
    idx = html.lower().index("<!doctype")
    html = html[idx:]

if "</html>" in html:
    html = html[:html.index("</html>") + 7]

# 업데이트 시간 삽입
timestamp_html = (
    f'<div style="text-align:right; color:#8b949e; padding:6px 20px 0; '
    f'font-size:0.75rem;">⏱ 최종 업데이트: {update_time} KST</div>'
)
if "<body>" in html:
    html = html.replace("<body>", f"<body>\n{timestamp_html}", 1)

with open(filename, "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ 완료: {filename} 저장됨 (총 {len(html)}자)")
