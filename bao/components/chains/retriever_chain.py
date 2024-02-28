import logging
from typing import Any, Dict

from injector import inject, singleton
from langchain.chains import TransformChain
from langchain_core.runnables import RunnableSerializable

from bao.settings.settings import Settings
from bao.utils.embeddings import EmbeddingsCache
from bao.utils.vectordb import load_qdrant

logger = logging.getLogger()
stream_handler = logging.StreamHandler()
logger.addHandler(stream_handler)
logger.setLevel(logging.INFO)


@singleton
class Retriever:
    @inject
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.embeddings = EmbeddingsCache()
        self.db = load_qdrant(embeddings=self.embeddings)

    def chain(self) -> RunnableSerializable[Dict[str, Any], Dict[str, Any]]:
        def vector_search(input: Dict[str, Any]) -> Dict[str, Any]:
            retriever_input = input.get("query_rewrite", {})
            retriever_input["topic"] = input.get("topic", {}).get("type")
            k = self.settings.retriever.k
            metadata_keys = set(
                [
                    field.alias or name
                    for name, field in self.settings.retriever.metadata.model_fields.items()
                ]
            )
            filter = {
                key: retriever_input[key]
                for key in metadata_keys
                if key in retriever_input and retriever_input[key]
            } or None
            query = retriever_input.get(
                "query"
            )  # reformulated key for vector retriever
            logger.info(f"input: {input}, filter: {filter}")
            docs_and_similarities = self.db.similarity_search_with_score(
                query,
                k=k,
                filter=filter,
                score_threshold=self.settings.retriever.score_threshold,
            )
            if not len(docs_and_similarities):
                raise Exception(
                    f"no relevant documents found! score threshold: {self.settings.retriever.score_threshold}"
                )
            docs = [doc for doc, _ in docs_and_similarities]
            scores = [score for _, score in docs_and_similarities]
            if scores:
                logger.info(
                    f"score distribution: max={max(scores)} min={min(scores)} avg={sum(scores)/len(scores):0.4f}"
                )
            return {
                "vector_docs": docs,
            }

        return TransformChain(
            transform=vector_search,
            input_variables=["query_rewrite", "topic"],
            output_variables=["vector_docs"],
        )  # type: ignore
