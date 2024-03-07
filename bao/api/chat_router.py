from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse

from bao.api.authenticate import authenticated
from bao.components.chat import Chat, ChatRequestBody, ChatResponse

chat_router = APIRouter(prefix="/chat", dependencies=[Depends(authenticated)])


@chat_router.post("/ask", tags=["Chat"])
async def chat(request: Request, chat_input: ChatRequestBody) -> ChatResponse:
    """chat"""
    bot: Chat = request.state.injector.get(Chat)
    return await bot.chat(input=chat_input)  # type: ignore


# favorate icon

favicon_router = APIRouter(prefix="/favicon.ico")

favicon_path = "./bao/web_client/static/favico.ico"


@favicon_router.get("", include_in_schema=False)
def favicon():
    return FileResponse(favicon_path)
