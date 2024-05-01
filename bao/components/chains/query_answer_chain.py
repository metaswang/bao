from typing import Any, Dict

from injector import inject, singleton
from langchain.chains.question_answering import load_qa_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableSerializable

from bao.components.llms import LLMs
from bao.settings.settings import Settings


@singleton
class Answering:
    @inject
    def __init__(self, settings: Settings, llms: LLMs) -> None:
        self.settings = settings
        self.llms = llms

    def chain(
        self, fallback: bool = False
    ) -> RunnableSerializable[Dict[str, Any], Dict[str, Any]]:
        llm = self.llms.get_llm(
            llm_type=self.settings.chain_templates.answer_model[1 if fallback else 0]
        )
        chat_template = ChatPromptTemplate.from_messages(
            [
                ("system", self.settings.chain_templates.answer_template),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{question}"),
            ]
        )
        return load_qa_chain(
            llm=llm, chain_type="stuff", verbose=True, prompt=chat_template  # type: ignore
        )
