from bao.settings.settings import Settings
from qdrant_client.http import models
from qdrant_client import QdrantClient
from langchain_community.vectorstores.qdrant import Qdrant

from bao.utils.embeddings import EmbeddingsCache
from injector import singleton, inject


@singleton
class QdrantVectorDB(Qdrant):
    @inject
    def __init__(self, settings: Settings):
        embeddings = EmbeddingsCache()
        client = QdrantClient(**settings.qdrant.model_dump(exclude_unset=True))
        collection_name = settings.retriever.collection_name
        if collection_name not in [
            _.name for _ in client.get_collections().collections
        ]:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=settings.embedding.embedding_size,
                    distance=models.Distance.COSINE,
                ),
            )
        super().__init__(
            client=client, collection_name=collection_name, embeddings=embeddings
        )
