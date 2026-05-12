import os
import asyncio
from google import genai

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            _client = genai.Client(api_key=api_key)
    return _client


async def analyze_rainfall(location: str, time_str: str, basic_desc: str) -> str | None:
    client = _get_client()
    if not client:
        return None

    prompt = (
        f"你是台灣氣象雷達分析助理。根據以下雷達回波資料，用繁體中文寫出 2 句話的降雨說明。\n\n"
        f"規則：\n"
        f"- 只根據提供的雷達回波資料說明，不要推測或捏造其他資訊\n"
        f"- 不提紫外線、氣溫、濕度、空氣品質等雷達以外的數據\n"
        f"- 可根據降雨強度給出是否需要帶傘的建議\n"
        f"- 口語化、簡潔，不要有標題或符號\n\n"
        f"位置：{location}\n"
        f"時間：{time_str}\n"
        f"雷達回波分析：{basic_desc}"
    )

    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: _get_client().models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=prompt,
            ),
        )
        text = (response.text or "").strip()
        return text if text else None
    except Exception as e:
        print(f"[LLM 分析失敗] {e}")
        return None
