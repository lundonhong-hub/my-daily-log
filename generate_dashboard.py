import anthropic
import os

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
filename = os.environ["FILENAME"]
today = os.environ["TODAY"]

# prompt_template.md 읽기
with open("prompt_template.md", "r", encoding="utf-8") as f:
    prompt = f.read().replace("[[TODAY]]", today)

print(f"Claude API 호출 중... ({filename})")

message = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=8192,
    messages=[
        {"role": "user", "content": prompt}
    ]
)

html = message.content[0].text

# HTML 태그만 추출 (혹시 마크다운 코드블록이 붙는 경우 대비)
if "<!DOCTYPE" in html:
    html = html[html.index("<!DOCTYPE"):]
if html.endswith("```"):
    html = html[:-3].strip()

with open(filename, "w", encoding="utf-8") as f:
    f.write(html)

print(f"완료: {filename} 저장됨")
