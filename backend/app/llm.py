import httpx

async def polish_answer(api_key, model, user_question, raw_answer):
    if not api_key:
        return raw_answer
    payload = {
        "model": model,
        "messages": [
            {"role":"system","content":"Rewrite the factual business answer for a founder. Do not change numbers, caveats, scope, or uncertainty. Do not invent information."},
            {"role":"user","content":f"Question:\n{user_question}\n\nFactual answer:\n{raw_answer}"}
        ],
        "temperature": 0.1,
    }
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post("https://api.openai.com/v1/chat/completions",
                                  headers={"Authorization":f"Bearer {api_key}"},
                                  json=payload)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return raw_answer
