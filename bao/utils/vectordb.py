from bao.settings.settings import settings
from qdrant_client.http import models
from qdrant_client import QdrantClient
from langchain_community.vectorstores.qdrant import Qdrant


def load_qdrant(embeddings):
    setting = settings()
    client = QdrantClient(**setting.qdrant.model_dump(exclude_unset=True))
    collection_name = setting.retriever.collection_name
    if collection_name not in [_.name for _ in client.get_collections().collections]:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=setting.embedding.embedding_size, distance=models.Distance.COSINE
            ),
        )
    return Qdrant(client=client, collection_name=collection_name, embeddings=embeddings)
