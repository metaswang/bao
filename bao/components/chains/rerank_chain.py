from typing import Any, Dict

import cohere
from injector import inject, singleton
from langchain.chains import TransformChain
from langchain_core.runnables import RunnableSerializable

from bao.settings.settings import Settings
from bao.utils.strings import hash_of_text


@singleton
class ReRanker:
    @inject
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.co = cohere.Client(api_key=self.settings.reranker.cohere.api_key)

    def chain(self) -> RunnableSerializable[Dict[str, Any], Dict[str, Any]]:

        def rerank(input: Dict[str, Any]) -> Dict[str, Any]:
            question = input.get("query_rewrite", {}).get("query")
            vector_docs = input.get("vector_docs", [])
            if len(vector_docs) <= self.settings.reranker.cohere.k:
                return {"input_documents": vector_docs}

            docs_hash = dict([(hash_of_text(_.page_content), _) for _ in vector_docs])
            docs = docs_hash.values()
            rerank_resp = self.co.rerank(
                query=question,
                documents=[doc.page_content for doc in docs],
                top_n=self.settings.reranker.cohere.k,
                model=self.settings.reranker.cohere.model,
            )
            return {
                "input_documents": [
                    docs_hash[hash_of_text(d.document["text"])] for d in rerank_resp
                ]
            }

        return TransformChain(
            input_variables=["query_rewrite", "vector_docs"],
            output_variables=["input_documents"],
            transform=rerank,
        ) # type: ignore
