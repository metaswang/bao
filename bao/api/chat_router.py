from fastapi import APIRouter, Depends, Request

from bao.api.authenticate import authenticated
from bao.components.chat import Chat, ChatRequestBody, ChatResponse

chat_router = APIRouter(prefix="/chat", dependencies=[Depends(authenticated)])


@chat_router.post("/ask", tags=["Chat"])
async def chat(request: Request, chat_input: ChatRequestBody) -> ChatResponse:
    """chat"""
    bot: Chat = request.state.injector.get(Chat)
    return await bot.chat(input=chat_input)  # type: ignore
