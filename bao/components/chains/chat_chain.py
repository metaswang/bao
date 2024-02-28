from typing import Any, Dict

from injector import inject, singleton
from langchain_core.runnables import (
    RunnableBranch,
    RunnablePassthrough,
    RunnableSerializable,
)

from bao.components.chains.intent_classification_chain import IntentClassification
from bao.components.chains.query_answer_chain import Answering
from bao.components.chains.query_rewrite_chain import QueryReWrite
from bao.components.chains.rerank_chain import ReRanker
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
        rerank: ReRanker,
        answer: Answering,
    ) -> None:
        self.settings = settings
        self.intent_classifier = intent_classifier
        self.greeting = greeting
        self.query_rewrite = query_rewrite
        self.retriever = retriever
        self.rerank = rerank
        self.answer = answer
        self.retriever_chains = (
            RunnablePassthrough.assign(query_rewrite=self.query_rewrite.chain())
            | self.retriever.chain()
            | self.rerank.chain()
        )
        self.retriever_chat_chains = (
            RunnablePassthrough.assign(query_rewrite=self.query_rewrite.chain())
            | self.retriever.chain()
            | self.rerank.chain()
            | self.answer.chain()
        )
        self.route_condition = (
            lambda x: "greeting" == x["topic"].get("type"),
            {"output_text": self.greeting.chain()},
        )

    def chat_chain(self) -> RunnableSerializable[Dict[str, Any], Dict[str, Any]]:
        return RunnablePassthrough.assign(
            topic=self.intent_classifier.chain(),
        ) | RunnableBranch(
            self.route_condition,
            self.retriever_chat_chains,
        )

    def retriever_chain(self) -> RunnableSerializable[Dict[str, Any], Dict[str, Any]]:
        return (
            RunnablePassthrough.assign(
                topic=self.intent_classifier.chain(),
            )
            | self.retriever_chains
        )
