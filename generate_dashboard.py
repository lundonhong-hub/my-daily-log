import anthropic
import os

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
filename = os.environ["FILENAME"]
today = os.environ["TODAY"]
update_time = os.environ.get("UPDATE_TIME", "")

with open("prompt_template.md", "r", encoding="utf-8") as f:
    full_prompt = f.read()

# [SPLIT] 마커로 system(캐싱용) / user(매번 바뀌는 부분) 분리
if "[SPLIT]" in full_prompt:
    parts = full_prompt.split("[SPLIT]", 1)
    system_content = parts[0].strip()
    user_content = parts[1].strip().replace("[[TODAY]]", today)
else:
    system_content = None
    user_content = full_prompt.replace("[[TODAY]]", today)

print(f"Claude API 호출 중... (모델: claude-sonnet-4-6, 캐싱 적용)")

# 캐싱 적용: HTML 템플릿(고정 부분)은 system에 넣어서 90% 할인
if system_content:
    system_param = [
        {
            "type": "text",
            "text": system_content,
            "cache_control": {"type": "ephemeral"}
        }
    ]
else:
    system_param = None

messages = [{"role": "user", "content": user_content}]

max_turns = 8
turn = 0

while turn < max_turns:
    turn += 1

    kwargs = dict(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=messages
    )
    if system_param:
        kwargs["system"] = system_param

    response = client.messages.create(**kwargs)

    usage = response.usage
    cache_hit = getattr(usage, 'cache_read_input_tokens', 0)
    print(f"  턴 {turn} | stop: {response.stop_reason} | input: {usage.input_tokens} | output: {usage.output_tokens} | 캐시hit: {cache_hit}")

    messages.append({"role": "assistant", "content": response.content})

    if response.stop_reason == "end_turn":
        break

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

    break

# 최종 HTML 추출
html = ""
for block in response.content:
    if hasattr(block, "text") and block.text:
        html += block.text

if len(html) < 500:
    print("경고: HTML 짧음. 전체 메시지 재탐색...")
    for msg in reversed(messages):
        if msg["role"] == "assistant":
            content = msg["content"]
            if isinstance(content, list):
                for block in content:
                    if hasattr(block, "text") and block.text and len(block.text) > 500:
                        html = block.text
                        break
            if len(html) > 500:
                break

# 마크다운 코드블록 제거
html = html.strip()
if html.startswith("```"):
    html = html[html.find("\n")+1:]
if html.endswith("```"):
    html = html[:html.rfind("```")]

if "<!DOCTYPE" in html:
    html = html[html.index("<!DOCTYPE"):]
elif "<!doctype" in html.lower():
    html = html[html.lower().index("<!doctype"):]

if "</html>" in html:
    html = html[:html.index("</html>") + 7]

timestamp_html = (
    f'<div style="text-align:right; color:#8b949e; padding:6px 20px 0; '
    f'font-size:0.75rem;">⏱ 최종 업데이트: {update_time} KST</div>'
)
if "<body>" in html:
    html = html.replace("<body>", f"<body>\n{timestamp_html}", 1)

with open(filename, "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ 완료: {filename} 저장됨 (총 {len(html)}자)")
