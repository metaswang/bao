from typing import Any, Dict

from injector import inject, singleton
from langchain_core.runnables import (
    RunnableBranch,
    RunnablePassthrough,
    RunnableSerializable,
)

from bao.components.chains.grader_chain import Grader
from bao.components.chains.intent_classification_chain import IntentClassification
from bao.components.chains.query_answer_chain import Answering
from bao.components.chains.query_rewrite_chain import QueryReWrite
from bao.components.chains.retriever_chain import Retriever
from bao.components.chains.greeting_chain import Greeting
from bao.settings.settings import Settings


@singleton
class ChatChains:
    @inject
    def __init__(
        self,
        settings: Settings,
        intent_classifier: IntentClassification,
        greeting: Greeting,
        query_rewrite: QueryReWrite,
        retriever: Retriever,
        grader: Grader,
        answer: Answering,
    ) -> None:
        self.settings = settings
        self.intent_classifier = intent_classifier
        self.greeting = greeting
        self.query_rewrite = query_rewrite
        self.retriever = retriever
        self.grader = grader
        self.answer = answer

    def retriever_chains(self, fallback: bool = False):
        return (
            RunnablePassthrough.assign(query_rewrite=self.query_rewrite.chain(fallback))
            | self.retriever.chain()
            | self.grader.chain(fallback)
        )

    def retriever_chat_chains(self, fallback: bool = False):
        return (
            RunnablePassthrough.assign(query_rewrite=self.query_rewrite.chain(fallback))
            | self.retriever.chain()
            | self.grader.chain(fallback)
            | self.answer.chain(fallback)
        )

    def greeting_branch(self, fallback):
        return (
            lambda x: "greeting" == x["topic"].get("type"),
            {"output_text": self.greeting.chain(fallback)},
        )

    def chat_chain(
        self, fallback: bool = False
    ) -> RunnableSerializable[Dict[str, Any], Dict[str, Any]]:
        return RunnablePassthrough.assign(
            topic=self.intent_classifier.chain(fallback),
        ) | RunnableBranch(
            self.greeting_branch(fallback),
            self.retriever_chat_chains(fallback),
        )

    def retriever_chain(
        self, fallback: bool = False
    ) -> RunnableSerializable[Dict[str, Any], Dict[str, Any]]:
        return RunnablePassthrough.assign(
            topic=self.intent_classifier.chain(fallback),
        ) | RunnableBranch(
            self.greeting_branch(fallback), self.retriever_chains(fallback)
        )
