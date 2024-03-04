import logging

from injector import inject, singleton
from bao.components import SEARCH_MODE_PERFIX

from bao.components.chains.chat_chain import ChatChains
from bao.components.chat import Chat, ChatRequestBody, ChatResponse
from bao.utils.strings import clean_msg
from bao.utils.ttl_dict import ChatHistDict

logger = logging.getLogger()


@singleton
class DiscordChat:
    SEARCH_TRIGGER = SEARCH_MODE_PERFIX

    @inject
    def __init__(self, chat_chain: ChatChains, chat: Chat):
        self.chat_history = ChatHistDict(
            max_size=chat_chain.settings.discord.max_history_len
        )  # List[Tuple[str, str]]
        self.chat_bot = chat

    def search_mode(self, question: str) -> bool:
        return question.lower().strip().startswith(DiscordChat.SEARCH_TRIGGER)

    async def chat(self, message: str, author: str) -> str:
        logger.info(f"from @{author}: {message}")
        question = clean_msg(message)
        history = self.chat_history.get(author, [])
        resp: ChatResponse = await self.chat_bot.chat(input=ChatRequestBody(question=question, chat_history=history, show_all_sources=False))  # type: ignore
        self.chat_history.add(author, (question, resp.answer))
        if self.search_mode(question):
            return resp.reference
        else:
            return f"{resp.answer}\n## References:\n\n{resp.reference}"
