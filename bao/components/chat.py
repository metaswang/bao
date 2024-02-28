import logging
from itertools import chain as iter_chain
from typing import Iterable, List, Tuple, Union

from injector import inject, singleton
from pydantic import BaseModel, Field

from bao.components.chains.chat_chain import ChatChains
from bao.utils.chat_template import RENDER_YOUTUBE_CLIP_FN, SHOW_ALL_QUOTES, gen_refence
from bao.utils.strings import get_metadata_alias, seconds_to_hh_mm_ss

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
    def __init__(self, chat_chain: ChatChains, show_all_quotes: bool = True) -> None:
        self.chat_chain = chat_chain
        self.settings = chat_chain.settings
        self.max_len_history_msg = self.settings.web.max_history_message_len
        self.max_history_len = self.settings.web.max_history_len
        self.show_all_quotes = show_all_quotes

    def render_video_clip(
        self, title: str, video_url: str, start_at: Iterable[int]
    ) -> str:
        """
        Render the youtube video clip link with short format when given playing start time
        """
        youtube_vid = ""
        if video_url.startswith(self.settings.crawler.youtube_url_domain):
            youtube_vid = video_url.split("v=")[-1].split("&")[0]
        elif video_url.startswith(self.settings.crawler.youtube_short_url_domain):
            youtube_vid = video_url.split("/")[-1].split("?")[0]
        if youtube_vid:
            return f"[{seconds_to_hh_mm_ss(start_at)}]({self.settings.crawler.youtube_short_url_domain}/{youtube_vid}?t={start_at})"
        return seconds_to_hh_mm_ss(start_at)

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
                reference=f"{self.settings.discord.fallback_message}\nFrequently Asked Questions:\n{self.settings.discord.get_frequently_asked_questions()}",
            )

        doc_metadata_fields = self.settings.retriever.metadata
        context = dict(
            documents=answer.get("input_documents", []),
            **{
                f"meta_{alias}_key": alias
                for alias in get_metadata_alias(doc_metadata_fields)
            },
        )
        context[SHOW_ALL_QUOTES] = self.show_all_quotes
        context[RENDER_YOUTUBE_CLIP_FN] = self.render_video_clip
        if search:
            if not answer.get("input_documents"):
                return ChatResponse(
                    answer="",
                    reference=f"{self.settings.discord.fallback_message}\nFrequently Asked Questions:\n{self.settings.discord.get_frequently_asked_questions()}",
                )
            return ChatResponse(answer="", reference=gen_refence(**context))
        answer_txt = answer.get("output_text") if not search else ""
        logger.info(f"from Bot: {answer_txt}")

        return ChatResponse(answer=answer_txt, reference=gen_refence(**context))  # type: ignore
