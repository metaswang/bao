import time
from functools import lru_cache
from typing import List

import torch.nn.functional as F
from langchain_core.embeddings import Embeddings
from torch import Tensor
from transformers import AutoModel, AutoTokenizer

from bao import MODEL_CACHE
from bao.settings.settings import settings
import logging

logger = logging.getLogger(__name__)


def average_pool(last_hidden_states: Tensor, attention_mask: Tensor) -> Tensor:
    last_hidden = last_hidden_states.masked_fill(~attention_mask[..., None].bool(), 0.0)
    return last_hidden.sum(dim=1) / attention_mask.sum(dim=1)[..., None]


class EmbeddingsCache(Embeddings):
    def __init__(self) -> None:
        super().__init__()
        self.model_id = settings().local.embedding_hf_model_name
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id, cache_dir=MODEL_CACHE)  # type: ignore
        self.model = AutoModel.from_pretrained(self.model_id, cache_dir=MODEL_CACHE)  # type: ignore
        self.embedding_max_tokens = settings().local.embedding_hf_model_tokens

    def inference(self, texts: List[str]) -> List[List[float]]:
        time_st = time.time()
        batch_dict = self.tokenizer(
            texts,
            max_length=self.embedding_max_tokens,
            padding=True,
            truncation=True,
            return_tensors="pt",
        )
        outputs = self.model(**batch_dict)
        embeddings = average_pool(
            outputs.last_hidden_state, batch_dict["attention_mask"]  # type: ignore
        )
        embeddings = F.normalize(embeddings, p=2, dim=1)
        logger.info(f"Elapsed time for query embedding: {time.time() - time_st:0.3f}")
        return embeddings.detach().cpu().numpy()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # Tokenize the input texts
        texts = ["passage: " + _ for _ in texts]
        return self.inference(texts)

    @lru_cache(maxsize=1000)
    def embed_query(self, text: str) -> List[float]:
        text = "query: " + text
        return self.inference([text])[0]
