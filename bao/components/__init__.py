from typing import Literal, List


MODEL_TYPE = Literal[
    "gemini",
    "gpt-3.5",
    "gpt-4",
    "anthropic-sonnet",
    "anthropic-opus",
    "anthropic-haiku",
    "llama3-8b-8192",  # Groq
    "llama3-70b-8192",  # Groq
]
MODEL_TYPES = List[MODEL_TYPE]
TOPIC_TYPE = Literal["greeting", "bao", "miles", "dc_farm", "federation", "other_forms"]
METADATA_TYPE = Literal["str", "int"]
CHAT_MODE_CHAT = "chat"
CHAT_MODE_SEARCH = "search"
CHAT_MODE = Literal["chat", "search"]
SCALE_CONTEXT_RETREIVER = 1.5

SEARCH_MODE_PERFIX = "/s"
