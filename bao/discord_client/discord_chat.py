from langchain_core.messages import HumanMessage, AIMessage
from injector import inject, singleton

from bao.components.chains.chat_chain import ChatChains
from bao.utils.chat_template import gen_refence
from bao.utils.strings import clean_msg
from bao.utils.ttl_dict import ChatHistDict
import logging


logger = logging.getLogger()


@singleton
class DiscordChat:
    @inject
    def __init__(self, chat_chain: ChatChains) -> None:
        self.chat_chain = chat_chain
        self.chat_history = ChatHistDict(
            max_size=chat_chain.settings.discord.max_history_len * 2
        )
        self.max_len_history_msg = (
            self.chat_chain.settings.discord.max_history_message_len
        )

    async def chat(self, message: str, author: str) -> str:
        logger.info(f"from @{author}: {message}")
        try:
            question = clean_msg(message)
            search = question.lower().startswith("/s")
            if search:
                chain = self.chat_chain.retriever_chain()
                question = question[2:].strip()
            else:
                chain = self.chat_chain.chat_chain()
            answer = await chain.ainvoke(
                {
                    "question": question,
                    "chat_history": self.chat_history.get(author, []),
                }
            )
        except Exception as e:
            logger.exception("failed to answer:", e)
            return f"{self.chat_chain.settings.discord.fallback_message}\nFrequently Asked Questions:\n{self.chat_chain.settings.discord.get_frequently_asked_questions()}"

        doc_metadata_fields = self.chat_chain.settings.retriever.metadata.model_fields
        context = dict(
            documents=answer.get("input_documents", []),
            **{
                f"meta_{field_name}_key": field_info.alias
                for field_name, field_info in doc_metadata_fields.items()
            },
        )
        if search:
            if not answer.get("input_documents"):
                return f"{self.chat_chain.settings.discord.fallback_message}\nFrequently Asked Questions:\n{self.chat_chain.settings.discord.get_frequently_asked_questions()}"
            return gen_refence(**context)
        answer_txt = answer.get("output_text")
        logger.info(f"from Bot: {answer_txt}")
        self.chat_history.add(
            user=author, msg=HumanMessage(content=question[: self.max_len_history_msg])
        )
        self.chat_history.add(
            user=author, msg=AIMessage(content=answer_txt[: self.max_len_history_msg])  # type: ignore
        )
        return answer_txt + "\n## References\n" + gen_refence(**context)  # type: ignore
