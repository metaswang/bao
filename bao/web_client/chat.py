from typing import List, Tuple, Union
from weakref import ref
from langchain_core.messages import HumanMessage, AIMessage
from injector import inject, singleton
from pydantic import BaseModel, Field

from bao.components.chains.chat_chain import ChatChains
from bao.utils.chat_template import gen_refence
from bao.utils.strings import get_metadata_alias
import logging
from itertools import chain as iter_chain

logger = logging.getLogger(__name__)


class ChatRequestBody(BaseModel):
    chat_history: List[Union[Tuple[str], List[str]]] = Field(
        description="Chat history. [(human message, bot message), ... (human message, bot message)]. will keep the latest 5"
    )
    question: str = Field(description="question you want to ask the bot")


class ChatResponse(BaseModel):
    answer: str = Field("", description="chat resonpse")
    reference: str = Field("", description="source references for the answer")


@singleton
class Chat:
    @inject
    def __init__(self, chat_chain: ChatChains) -> None:
        self.chat_chain = chat_chain
        self.max_len_history_msg = self.chat_chain.settings.web.max_history_message_len
        self.max_history_len = self.chat_chain.settings.web.max_history_len

    async def chat(self, input: ChatRequestBody) -> ChatResponse:
        try:
            question = input.question.strip()
            history = input.chat_history[-self.max_history_len :]
            history = list(iter_chain.from_iterable(history))
            history = [_[: self.max_len_history_msg] for _ in history]
            search = question.lower().startswith("/s")
            if search:
                chain = self.chat_chain.retriever_chain()
                question = question[2:].strip()
            else:
                chain = self.chat_chain.chat_chain()
            answer = await chain.ainvoke(
                {
                    "question": question,
                    "chat_history": history,
                }
            )
        except Exception as e:
            logger.exception("failed to answer:", e)
            return ChatResponse(
                answer="",
                reference=f"{self.chat_chain.settings.discord.fallback_message}\nFrequently Asked Questions:\n{self.chat_chain.settings.discord.get_frequently_asked_questions()}",
            )

        doc_metadata_fields = self.chat_chain.settings.retriever.metadata
        context = dict(
            documents=answer.get("input_documents", []),
            **{
                f"meta_{alias}_key": alias
                for alias in get_metadata_alias(doc_metadata_fields)
            },
        )
        context["show_all_quotes"] = True
        if search:
            if not answer.get("input_documents"):
                return ChatResponse(
                    answer="",
                    reference=f"{self.chat_chain.settings.discord.fallback_message}\nFrequently Asked Questions:\n{self.chat_chain.settings.discord.get_frequently_asked_questions()}",
                )
            return ChatResponse(answer="", reference=gen_refence(**context))
        answer_txt = answer.get("output_text") if not search else ""
        logger.info(f"from Bot: {answer_txt}")

        return ChatResponse(answer=answer_txt, reference=gen_refence(**context))  # type: ignore
