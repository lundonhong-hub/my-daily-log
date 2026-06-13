import os
import json
from datetime import datetime
from data_collector import collect_market_data

# ============================================================
# ★ API 선택 — "claude" 또는 "gemini"
# ============================================================
API_MODE = os.environ.get("API_MODE", "claude")
# ============================================================

filename    = os.environ["FILENAME"]
today       = os.environ["TODAY"]
update_time = os.environ.get("UPDATE_TIME", "")

# ── 1. 요일 확인 (0=월 ~ 6=일) ─────────────────────────────
weekday   = datetime.now().weekday()
is_sunday = (weekday == 6)
template_file = "prompt_template.md" if is_sunday else "prompt_template_weekday.md"
print(f"📅 {['월','화','수','목','금','토','일'][weekday]}요일 → {template_file}")

# ── 2. 실제 수치 수집 → JSON ────────────────────────────────
market_data = collect_market_data()
market_json = json.dumps(market_data, ensure_ascii=False, indent=2)

# ── 3. 프롬프트 로드 + 치환 ─────────────────────────────────
with open(template_file, "r", encoding="utf-8") as f:
    prompt = f.read()

prompt = prompt.replace("[[TODAY]]", today)
prompt = prompt.replace("[[MARKET_DATA_JSON]]", market_json)

# ── 4. API 호출 ─────────────────────────────────────────────
if API_MODE == "claude":
    import anthropic

    CLAUDE_MODEL = "claude-haiku-4-5"
    print(f"Claude API 호출 중... (모델: {CLAUDE_MODEL})")

    client   = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    messages = [{"role": "user", "content": prompt}]

    while True:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=16000,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=messages
        )
        print(f"  → stop_reason: {response.stop_reason}")
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

    html = ""
    for block in response.content:
        if hasattr(block, "text") and block.text:
            html += block.text

    if len(html) < 100:
        print("경고: HTML 짧음. 재탐색...")
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

elif API_MODE == "gemini":
    from google import genai
    from google.genai import types

    GEMINI_MODEL = "gemini-2.5-flash"
    print(f"Gemini API 호출 중... (모델: {GEMINI_MODEL})")

    client   = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.3,
            max_output_tokens=65536,
        ),
    )
    html = response.text

else:
    raise ValueError(f"API_MODE 오류: '{API_MODE}' — 'claude' 또는 'gemini' 만 가능")

# ── 5. HTML 후처리 ───────────────────────────────────────────
print(f"추출된 HTML 길이: {len(html)}자")

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

print(f"✅ 완료: {filename} ({API_MODE}, {'일요일' if is_sunday else '평일'}) 저장됨 (총 {len(html)}자)")
