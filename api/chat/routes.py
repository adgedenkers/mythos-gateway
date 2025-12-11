from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from .schemas import ChatRequest
from .service import stream_chat_response

router = APIRouter()

@router.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    return StreamingResponse(stream_chat_response(), media_type="text/event-stream")
