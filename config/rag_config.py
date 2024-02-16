from yacs.config import CfgNode as CN
import os
from threading import Lock

__all__ = ["get_cfg_default", "merge_cfg", "rag_config"]

_c = CN()
_c.VERSION = "0.0.1"

_c.METADATA = CN()
_c.METADATA.KEYS = [
    "video",
    "pub-date",
    "source",
    "title",
    "start-at",
    "pub-year",
    "pub-year-month",
]

_c.QUESTION_KEY = "question"
_c.TOPIC_KEY = "topic"
_c.ES_INDEX_KEY = "index_name"
_c.CHAT_HISTORY_KEY = "chat_history"
_c.CHAT_HISTORY_TTL = 3600

_c.METADATA.CONTENT = "transcript"
_c.METADATA.DATE = _c.METADATA.KEYS[1]
_c.METADATA.REF_LINK = _c.METADATA.KEYS[0]
_c.METADATA.SOURCE = _c.METADATA.KEYS[2]
_c.METADATA.START_AT = _c.METADATA.KEYS[4]
_c.METADATA.YEAR = _c.METADATA.KEYS[-2]
_c.METADATA.YEAR_MONTH = _c.METADATA.KEYS[-1]
_c.METADATA.TITLE = _c.METADATA.KEYS[3]
_c.METADATA.ES_FIELD_TYPE_DEFAULT = "keyword"
_c.METADATA.ES_FIELDS_TYPE_AS_TEXT = []

_c.INDEX = CN()
_c.INDEX.CHUNK_SIZE = 500
_c.INDEX.CHUNK_OVERLAP = 50
_c.INDEX.CRAWL_DIR = "./data/crawl"

_c.RETRIEVER_VECT = CN()
_c.RETRIEVER_VECT.FETCH_K = 40
_c.RETRIEVER_VECT.K = 10
_c.RETRIEVER_VECT.SCORE_THRESHOLD = 0.75
_c.RETRIEVER_VECT.QUERY_KEY = "query_vector"
_c.RETRIEVER_VECT.URL = "http://localhost:6333"
_c.RETRIEVER_VECT.PORT = 6333
_c.RETRIEVER_VECT.COLLECTION_NAME = "bao"

_c.RERANKER = CN()
_c.RERANKER.K = 5
_c.RERANKER.MODEL = "rerank-multilingual-v2.0"

_c.LLM = CN()
_c.LLM.VENDOR = "openai"
_c.LLM.MODEL = "gpt-4-turbo-preview"
_c.LLM.CHEAP_MODEL = "gpt-3.5-turbo-0125"
_c.LLM.FREE_MODEL_GEMINI = "gemini-pro"
_c.LLM_CHAIN_INPUT_KEY = "input_documents"
_c.LLM_CHAIN_OUTPUT_KEY = "output_text"
_c.LLM_BRANCH_GREETING = "greeting"
_c.LLM_BRANCH_OTHERS = "others"

_c.EMBEDDING = CN()
_c.EMBEDDING.MODEL = ""
_c.EMBEDDING.INFER_BATCH = 200


def get_cfg_default() -> CN:
    return _c.clone()


def merge_cfg(cfg_yml: str) -> CN:
    cfg = get_cfg_default()
    cfg.merge_from_file(cfg_yml)
    return cfg


class SingleCfg:
    _instance = None
    _lock = Lock()

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = merge_cfg(os.getenv("RAG_CFG"))
        return cls._instance


rag_config = SingleCfg.get_instance()
