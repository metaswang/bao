"""Wrapper around Elasticsearch database."""

from __future__ import annotations

from typing import Any, Iterable, List, Dict, Optional

from langchain_core.documents import Document
from elasticsearch import Elasticsearch
from tqdm.auto import tqdm
from config.bm25_es_settings_cn import CN_SETTING
from utils.strings import hash_of_text
from config.rag_config import rag_config


class ESBM25Retriever:
    """`Elasticsearch` retriever that uses `BM25`."""

    content_field: str = rag_config.METADATA.CONTENT
    video_link_field: str = rag_config.METADATA.REF_LINK
    video_title: str = rag_config.METADATA.TITLE

    client: Any
    """Elasticsearch client."""
    index_name: str
    """Name of the index to use in Elasticsearch."""

    def __init__(
        self,
        client: Elasticsearch,
        index_name: str,
    ) -> None:
        self.client = client
        self.index_name = index_name

    @classmethod
    def create(
        cls,
        elasticsearch_url: str,
        index_name: str,
        metadata_schema: Dict[str, str],
        settings: Dict = CN_SETTING,
        recreate_index: bool = False,
    ) -> ESBM25Retriever:
        """
        Create a ESBM25Retriever from a list of texts.

        Args:
            elasticsearch_url: URL of the Elasticsearch instance to connect to.
            index_name: Name of the index to use in Elasticsearch.
            metadata_schema: field name and type
            settings: ES index settings
        Returns:

        """
        from elasticsearch import Elasticsearch

        # Create an Elasticsearch client instance
        es = Elasticsearch(elasticsearch_url)

        # Define the index settings and mappings

        mappings = {
            "properties": {
                cls.content_field: {
                    "type": "text",
                    "similarity": "custom_bm25",  # Use the custom BM25 similarity
                }
            }
        }
        for field, tp in metadata_schema.items():
            if field == cls.content_field:
                continue
            mappings["properties"][field] = {"type": tp or "keyword"}
        # Create the index with the specified settings and mappings
        if recreate_index:
            try:
                es.indices.delete(index=index_name)
            except:
                pass  # ignore when not exist
        if not es.indices.exists(index=index_name):
            es.indices.create(
                index=index_name, body={"settings": settings, "mappings": mappings}
            )
        return cls(client=es, index_name=index_name)

    @classmethod
    def create_from_documents(
        cls,
        elasticsearch_url: str,
        index_name: str,
        documents: Iterable[Document],
        ids: Optional[Iterable[str]] = None,
        batch_size=5000,
    ) -> ESBM25Retriever:
        """create a BM25 retriever with index built from a list of documents.

        Args:
            documents: Iterable of Documents

        Returns:
            List of ids from adding the documents into the retriever.
        """
        if not documents:
            raise ValueError("make sure documents is not empty.")

        def get_field_type(field: str):
            return (
                rag_config.METADATA.ES_FIELD_TYPE_DEFAULT
                if field in rag_config.METADATA.ES_FIELDS_TYPE_AS_TEXT
                else "text"
            )

        bm25_retriever = ESBM25Retriever.create(
            elasticsearch_url=elasticsearch_url,
            index_name=index_name,
            metadata_schema={
                field: get_field_type(field) for field in documents[0].metadata
            },
        )
        try:
            from elasticsearch.helpers import bulk
        except ImportError:
            raise ValueError(
                "Could not import elasticsearch python package. "
                "Please install it with `pip install elasticsearch`."
            )
        requests = []
        doc_ids = ids or [hash_of_text(d.page_content) for d in documents]
        for i in tqdm(range(0, len(documents), batch_size)):
            d_ids = doc_ids[i : i + batch_size]
            for j, d in enumerate(documents[i : i + batch_size]):
                idx_dic = {bm25_retriever.content_field: d.page_content}
                idx_dic.update(d.metadata)
                idx_dic = {
                    "_id": d_ids[j],
                    "_index": index_name,
                    "_op_type": "update",
                    "doc": idx_dic,
                    "upsert": idx_dic,
                }
                requests.append(idx_dic)
            bulk(bm25_retriever.client, requests)

        bm25_retriever.client.indices.refresh(index=bm25_retriever.index_name)
        return bm25_retriever

    def get_relevant_documents(
        self, query_dict: Dict, limit: int = 20
    ) -> List[Document]:
        if not self.index_name:
            raise ValueError(f"Specify index name before running ES search.")
        res = self.client.search(index=self.index_name, body=query_dict)
        docs = []
        for r in res["hits"]["hits"][:limit]:
            docs.append(
                Document(
                    page_content=r["_source"][self.content_field],
                    metadata={
                        k: v for k, v in r["_source"].items() if k != self.content_field
                    },
                )
            )
        return docs

    def get_relevant_doc_ids(self, query_dict: Dict, limit: int = 20) -> List[str]:
        if not self.index_name:
            raise ValueError(f"Specify index name before running ES search.")
        res = self.client.search(index=self.index_name, body=query_dict)
        docs = []
        for r in res["hits"]["hits"][:limit]:
            docs.append(r.get("_id"))
        return docs
