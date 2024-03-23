import time
import logging
from typing import Any, Dict

from injector import inject, singleton
from langchain.chains import TransformChain
from langchain_core.runnables import RunnableSerializable

from bao.components import CHAT_MODE_SEARCH, SCALE_CONTEXT_RETREIVER
from bao.components.vectordb import QdrantVectorDB
from bao.settings.settings import Settings
from bao.settings.settings import MetadataValue

logger = logging.getLogger(__name__)


@singleton
class Retriever:
    @inject
    def __init__(self, settings: Settings, db: QdrantVectorDB):
        self.settings = settings
        self.db = db

    def chain(self) -> RunnableSerializable[Dict[str, Any], Dict[str, Any]]:
        def vector_search(input: Dict[str, Any]) -> Dict[str, Any]:
            time_st = time.time()
            retriever_input = input.get("query_rewrite", {})
            retriever_input["topic"] = input.get("topic", {}).get("type")
            chat_mode = input.get("chat_mode")
            k = self.settings.retriever.k
            context_size = input.get("context_size", k)
            if chat_mode == CHAT_MODE_SEARCH:
                k = int(context_size * SCALE_CONTEXT_RETREIVER)
            filter_model = MetadataValue(**retriever_input).to_dict(
                exclude_defaults=True
            )
            filter = filter_model or None
            query = retriever_input.get(
                "query"
            )  # reformulated key for vector retriever
            logger.info(f"input: {input}, filter: {filter}")
            docs_and_similarities = self.db.similarity_search_with_score(
                query,
                k=k,
                filter=filter,  # type: ignore
            )
            score_threshold = self.settings.retriever.score_threshold
            docs = [doc for doc, _ in docs_and_similarities if _ >= score_threshold]
            scores = [
                score for _, score in docs_and_similarities if score >= score_threshold
            ]
            if scores:
                logger.info(
                    f"score distribution: max={max(scores)} min={min(scores)} avg={sum(scores)/len(scores):0.4f}"
                )
            if not len(docs):
                logger.warning(
                    f"no relevant documents found with score threshold: {self.settings.retriever.score_threshold}!"
                )
                # use top - 2
                docs = [doc for doc, _ in docs_and_similarities][:2]
            logger.info(f"Elapsed time for vector search: {time.time() - time_st:0.3f}")
            return {
                "vector_docs": docs,
            }

        return TransformChain(
            transform=vector_search,
            input_variables=["query_rewrite", "topic", "chat_mode", "context_size"],
            output_variables=["vector_docs"],
        )  # type: ignore
