from typing import Any, Dict

import cohere
import time
from cohere.error import CohereAPIError
from injector import inject, singleton
from langchain.chains import TransformChain
from langchain_core.runnables import RunnableSerializable

from bao.components import CHAT_MODE_SEARCH
from bao.settings.settings import Settings
from bao.utils.strings import hash_of_text
import logging

logger = logging.getLogger(__name__)


MAX_RETRIES_RERANK = 3
RETRY_INTERVAL = 1  # second


@singleton
class ReRanker:
    @inject
    def __init__(self, settings: Settings):
        self.settings = settings
        self.co = cohere.Client(api_key=self.settings.reranker.cohere.api_key)

    def chain(self) -> RunnableSerializable[Dict[str, Any], Dict[str, Any]]:

        def rerank(input: Dict[str, Any]) -> Dict[str, Any]:
            question = input.get("query_rewrite", {}).get("query")
            chat_mode = input.get("chat_mode")
            rerank_k = self.settings.reranker.cohere.k
            context_size = input.get("context_size", rerank_k)
            vector_docs = input.get("vector_docs", [])
            if chat_mode == CHAT_MODE_SEARCH:
                rerank_k = context_size
            elif len(vector_docs) <= self.settings.reranker.cohere.k:
                return {"input_documents": vector_docs}

            time_st = time.time()
            docs_hash = dict([(hash_of_text(_.page_content), _) for _ in vector_docs])
            docs = docs_hash.values()
            aft_reranked = vector_docs
            for _ in range(MAX_RETRIES_RERANK):
                try:
                    rerank_resp = self.co.rerank(
                        query=question,
                        documents=[doc.page_content for doc in docs],
                        top_n=rerank_k,
                        model=self.settings.reranker.cohere.model,
                    )
                    aft_reranked = [
                        docs_hash[hash_of_text(d.document["text"])] for d in rerank_resp
                    ]
                    break
                except CohereAPIError:
                    time.sleep(RETRY_INTERVAL)
            logger.info(f"Elapsed time for rerank: {time.time() - time_st:0.3f}")
            return {
                "input_documents": (
                    aft_reranked
                    if context_size > rerank_k
                    else aft_reranked[:context_size]
                )
            }

        return TransformChain(
            input_variables=[
                "query_rewrite",
                "vector_docs",
                "chat_mode",
                "context_size",
            ],
            output_variables=["input_documents"],
            transform=rerank,
        )  # type: ignore
