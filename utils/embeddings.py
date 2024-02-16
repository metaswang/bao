import os
from functools import lru_cache
from langchain_core.embeddings import Embeddings
import numpy as np
from config.rag_config import rag_config
from typing import List

import torch.nn.functional as F

from torch import Tensor
from transformers import AutoTokenizer, AutoModel


def average_pool(last_hidden_states: Tensor, attention_mask: Tensor) -> Tensor:
    last_hidden = last_hidden_states.masked_fill(~attention_mask[..., None].bool(), 0.0)
    return last_hidden.sum(dim=1) / attention_mask.sum(dim=1)[..., None]


class EmbeddingsCache(Embeddings):
    def __init__(self) -> None:
        super().__init__()
        self.model_id = rag_config.EMBEDDING.MODEL
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)

        self.model = AutoModel.from_pretrained(self.model_id)

    def inference(self, texts: List[str]) -> List[List[float]]:
        batch_dict = self.tokenizer(
            texts, max_length=512, padding=True, truncation=True, return_tensors="pt"
        )
        outputs = self.model(**batch_dict)
        embeddings = average_pool(
            outputs.last_hidden_state, batch_dict["attention_mask"]
        )
        embeddings = F.normalize(embeddings, p=2, dim=1)
        return embeddings.detach().cpu().numpy()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # Tokenize the input texts
        texts = ["passage: " + _ for _ in texts]
        return self.inference(texts)

    @lru_cache(maxsize=1000)
    def embed_query(self, text: str) -> List[float]:
        text = "query: " + text
        return self.inference([text])[0]
