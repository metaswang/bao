import logging

from typing import Iterable, List, Tuple, Union
from langchain_core.messages import AIMessage, HumanMessage
from injector import inject, singleton
from pydantic import BaseModel, Field
from bao.components import (
    CHAT_MODE,
    CHAT_MODE_CHAT,
    CHAT_MODE_SEARCH,
    SEARCH_MODE_PERFIX,
)

from bao.components.chains.chat_chain import ChatChains
from bao.utils.chat_template import RENDER_YOUTUBE_CLIP_FN, SHOW_ALL_QUOTES, gen_refence
from bao.utils.strings import get_metadata_alias, seconds_to_hh_mm_ss

logger = logging.getLogger(__name__)


class ChatRequestBody(BaseModel):
    question: str = Field("", description="question you want to ask the bot")
    chat_history: List[Union[Tuple[str], List[str]]] = Field(
        description="Chat history. [(human message, bot message), ... (human message, bot message)]. will keep the latest 5",
    )
    show_all_sources: bool = Field(
        True,
        description="if show all source references. In case of Discord, the size of message window is limited, so it's better to set it as false",
    )
    chat_mode: CHAT_MODE = Field("chat", description="Work mode: 'retrieve' or 'chat'")
    context_size: int = Field(
        4, description="Maximum retrieved item size in LLM context"
    )


class ChatResponse(BaseModel):
    answer: str = Field("", description="chat resonpse")
    reference: str = Field("", description="source references for the answer")
    reference_head_line: str = "### Reference"

    def response_text(self, search=False) -> str:
        if search:
            return self.reference
        if self.reference.strip():
            return f"{self.answer}\n\n{self.reference_head_line}\n{self.reference}"
        else:
            return self.answer


@singleton
class Chat:
    @inject
    def __init__(self, chat_chain: ChatChains) -> None:
        self.chat_chain = chat_chain
        self.settings = chat_chain.settings
        self.max_len_history_msg = self.settings.web_chat.max_history_message_len
        self.max_history_len = self.settings.web_chat.max_history_len

    def render_video_clip(self, video_url: str, start_at: Iterable[int]) -> str:
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
            history: List[Union[Tuple[str], List[str]]] = input.chat_history[
                -self.max_history_len :
            ]
            history_msg = []
            for p in history:
                if (
                    len(p) == 2 and p[1] is not None and p[1].strip()
                ):  # make sure the AIMessage is not retrieved from search result
                    history_msg.append(
                        HumanMessage(content=p[0][: self.max_len_history_msg])
                    )
                    history_msg.append(
                        AIMessage(content=p[1][: self.max_len_history_msg])
                    )
            search = question.lower().startswith(SEARCH_MODE_PERFIX)
            if search:
                chain = self.chat_chain.retriever_chain()
                question = question[2:].strip()
            else:
                chain = self.chat_chain.chat_chain()
            answer = await chain.ainvoke(
                {
                    "question": question,
                    "chat_history": history_msg,
                    "chat_mode": CHAT_MODE_SEARCH if search else CHAT_MODE_CHAT,
                    "context_size": input.context_size,
                }
            )
        except Exception as e:
            logger.exception("failed to answer:", e)
            return ChatResponse(
                answer=f"{self.settings.discord.fallback_message}\nFrequently Asked Questions:\n{self.settings.discord.get_frequently_asked_questions()}",
                reference="",
            )

        doc_metadata_fields = self.settings.retriever.metadata
        context = dict(
            documents=answer.get("input_documents", []),
            **{
                f"meta_{alias}_key": alias
                for alias in get_metadata_alias(doc_metadata_fields)
            },
        )
        context[SHOW_ALL_QUOTES] = input.show_all_sources
        context[RENDER_YOUTUBE_CLIP_FN] = self.render_video_clip
        if search:
            if not answer.get("input_documents"):
                return ChatResponse(
                    answer=f"{self.settings.discord.fallback_message}\nFrequently Asked Questions:\n{self.settings.discord.get_frequently_asked_questions()}",
                    reference="",
                )
            return ChatResponse(answer="", reference=gen_refence(**context))
        answer_txt = answer.get("output_text") if not search else ""
        logger.info(f"from Bot: {answer_txt}")

        return ChatResponse(answer=answer_txt, reference=gen_refence(**context))  # type: ignore
