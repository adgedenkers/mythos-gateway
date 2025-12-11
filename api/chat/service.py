import asyncio

async def stream_chat_response():
    for i in range(5):  # Simulated token stream
        yield f"data: {{\"id\": \"msg-{i}\", \"choices\": [{{\"delta\": {{\"content\": \"Token {i}\"}}, \"index\": 0}}]}}\n\n"
        await asyncio.sleep(0.5)
    yield "data: [DONE]\n\n"
