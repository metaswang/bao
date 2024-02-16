from config.rag_config import rag_config as cfg


def load_qdrant(embeddings):
    from qdrant_client import QdrantClient
    from langchain_community.vectorstores.qdrant import Qdrant

    client = QdrantClient(url=cfg.RETRIEVER_VECT.URL)
    collection_name = cfg.RETRIEVER_VECT.COLLECTION_NAME
    return Qdrant(client=client, collection_name=collection_name, embeddings=embeddings)
