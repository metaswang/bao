from typing import Dict, List, Literal, Union

from pydantic import BaseModel, Field, field_validator

from bao.components import METADATA_TYPE, MODEL_TYPES
from bao.settings.settings_loader import load_active_settings
from bao.utils.strings import date_from_yyyy, date_from_yyyymm, date_from_yyyymmdd


class Crawler(BaseModel):
    source_type: Literal["youtube"] = Field(
        "youtube", description="Source of the transcripts"
    )
    output_dir: str = Field(
        description="output of the crawler result files, vtt transcript file and mp4 audio file"
    )
    whisper_model: Literal["tiny", "small", "base", "medium", "large"] = Field(
        description="Based on https://github.com/openai/whisper. The model name can be: tiny, base, small, medium, large"
    )
    transcript_merge_size: int = Field(
        300,
        description="The expected chunk size after merged some neighbor transcript segments",
    )
    youtube_short_url_domain: str = Field(
        "https://youtu.be", description="Youtube short domain"
    )
    youtube_url_domain: str = Field(
        "https://www.youtube.com", description="Youtube url domain"
    )


class LLMSettings(BaseModel):
    mode: Literal["local", "openai"]
    max_new_tokens: int = Field(
        256,
        description="The maximum number of token that the LLM is authorized to generate in one completion.",
    )
    context_window: int = Field(
        8000,
        description="The maximum number of context tokens for the model.",
    )


class VectorstoreSettings(BaseModel):
    database: Literal["qdrant"]


class LocalSettings(BaseModel):
    llm_hf_repo_id: str | None = Field(None, description="llm_hf_repo_id")
    llm_hf_model_file: str | None = Field(None, description="llm_hf_model id")
    embedding_hf_model_name: str | None = Field(
        None, description="Name of the HuggingFace model to use for embeddings"
    )
    embedding_hf_model_tokens: int | None = Field(
        512, description="Max number of tokens the HuggingFace embedding model can take"
    )
    prompt_style: Literal["default", "llama2", "tag", "mistral", "chatml"] = Field(
        "llama2",
        description=(
            "The prompt style to use for the chat engine. "
            "If `default` - use the default prompt style from the llama_index. It should look like `role: message`.\n"
            "If `llama2` - use the llama2 prompt style from the llama_index. Based on `<s>`, `[INST]` and `<<SYS>>`.\n"
            "If `tag` - use the `tag` prompt style. It should look like `<|role|>: message`. \n"
            "If `mistral` - use the `mistral prompt style. It shoudl look like <s>[INST] {System Prompt} [/INST]</s>[INST] { UserInstructions } [/INST]"
            "`llama2` is the historic behaviour. `default` might work better with your custom models."
        ),
    )


class EmbeddingSettings(BaseModel):
    mode: Literal["local", "openai"]
    embedding_size: int = Field(
        768,
        description="embedding size. 768 is for E5 base. For OpenAI, by default, the length of the embedding vector will be 1536 for text-embedding-3-small or 3072 for text-embedding-3-large",
    )
    count_workers: int = Field(
        2,
        description=(
            "The number of workers to use for file ingestion.\n"
            "In `batch` mode, this is the number of workers used to parse the files.\n"
            "In `parallel` mode, this is the number of workers used to parse the files and embed them.\n"
            "This is only used if `ingest_mode` is not `simple`.\n"
            "Do not go too high with this number, as it might cause memory issues. (especially in `parallel` mode)\n"
            "Do not set it higher than your number of threads of your CPU."
        ),
    )


class AnthropicSettings(BaseModel):
    api_key: str = Field(description="Anthropic API key")
    eco_model: str = Field(
        "claude-3-sonnet-20240229", description="Economic/cheap model name"
    )
    supper_model: str = Field("claude-3-opus-20240229", description="Supper model name")
    haiku_model: str = Field("claude-3-haiku-20240229", description="Haiku model name")


class GroqSettings(BaseModel):
    api_key: str = Field(description="Anthropic API key")
    llama3_8b_8192: str | None = Field("llama3-8b-8192", description="llama3-8b")
    llama3_70b_8192: str | None = Field("llama3-70b-8192", description="llama3-70b")


class OpenAISettings(BaseModel):
    api_base: str = Field(
        None,
        description="Base URL of OpenAI API. Example: 'https://api.openai.com/v1'.",
    )
    api_key: str = Field(description="OpenAI API Key")
    eco_model: str = Field(
        "gpt-3.5-turbo-0125",
        description="The most cost-effective model to use. Example: 'gpt-3.5-turbo-0125'.",
    )
    super_model: str = Field(
        "gpt-4-0125-preview",
        description="High performance model to use. Example: 'gpt-4-0125-preview'.",
    )


class GoogleSettings(BaseModel):
    api_key: str
    model: str = Field("gemini-pro", description="model name")


class QdrantSettings(BaseModel):
    location: str | None = Field(
        None,
        description=(
            "If `:memory:` - use in-memory Qdrant instance.\n"
            "If `str` - use it as a `url` parameter.\n"
        ),
    )
    url: str | None = Field(
        None,
        description=(
            "Either host or str of 'Optional[scheme], host, Optional[port], Optional[prefix]'."
        ),
    )
    port: int | None = Field(6333, description="Port of the REST API interface.")
    grpc_port: int | None = Field(6334, description="Port of the gRPC interface.")
    prefer_grpc: bool | None = Field(
        False,
        description="If `true` - use gRPC interface whenever possible in custom methods.",
    )
    https: bool | None = Field(
        None,
        description="If `true` - use HTTPS(SSL) protocol.",
    )
    api_key: str | None = Field(
        None,
        description="API key for authentication in Qdrant Cloud.",
    )
    prefix: str | None = Field(
        None,
        description=(
            "Prefix to add to the REST URL path."
            "Example: `service/v1` will result in "
            "'http://localhost:6333/service/v1/{qdrant-endpoint}' for REST API."
        ),
    )
    timeout: float | None = Field(
        None,
        description="Timeout for REST and gRPC API requests.",
    )
    host: str | None = Field(
        None,
        description="Host name of Qdrant service. If url and host are None, set to 'localhost'.",
    )
    path: str | None = Field(None, description="Persistence path for QdrantLocal.")
    force_disable_check_same_thread: bool | None = Field(
        True,
        description=(
            "For QdrantLocal, force disable check_same_thread. Default: `True`"
            "Only use this if you can guarantee that you can resolve the thread safety outside QdrantClient."
        ),
    )


class IngestUISettings(BaseModel):
    enabled: bool = Field(False, description="bind to the FastAPI path if enabled")
    path: str = Field(description="the UI path binded to FastAPI")


class WebUISettings(BaseModel):
    enabled: bool = Field(True, description="bind to the FastAPI path if enabled")
    path: str = Field(description="Relative path to the fast api server domain.")
    title: str = Field(description="Set the title of the chatbot window")
    header_color: str = Field(
        description="Set the color value for the header or title bar."
    )
    max_history_message_len: int = Field(
        50, description="Max length of history message. To avoid context overflow"
    )
    max_history_len: int = Field(
        3,
        description="max number of history records will be used as chat history in LLM context",
    )
    frequently_asked_questions: List[str] | None = Field(
        description="most often asked questions from users."
    )
    btn_undo: str = Field("Delete Previous", description="undo button text in chatbot")
    btn_clear: str = Field("Clear", description="clear button text in chatbot")
    btn_submit: str = Field("Submit", description="submit button text in chatbot")
    work_mode_label: str = Field(
        "Mode", description="Interaction mode, ask question or search"
    )
    work_modes: List[str] = Field(
        description="Interaction modes, 1. Ask Question, 2. Search"
    )


class DiscordSettings(BaseModel):
    enabled: bool | None = Field(True, description="true: ON and false for OFF")
    reply_mode: bool | None = Field(
        True,
        description="answer in a new reply thread and reference the question message",
    )
    discord_token: str | None = Field(description="Discord client token")
    bot_id: int | None = Field(description="Discord bot ID")
    chat_history_ttl: int = Field(600, description="expire time in seconds")
    max_history_len: int = Field(
        3,
        description="max number of history records will be used as chat history in LLM context",
    )
    max_history_message_len: int = Field(
        100, description="Max length of history message. To avoid context overflow"
    )
    fallback_message: str = Field(
        description="fallback messages when no answer from bot"
    )
    frequently_asked_questions: List[str] | None = Field(
        description="most often asked questions from users."
    )
    limit_channel: List[int] | None = Field(
        None, description="constrain the channel id that users can interact the bot"
    )

    def get_frequently_asked_questions(self, markdown=True) -> str:
        if markdown:
            return "\n".join([f"* {_}" for _ in self.frequently_asked_questions or []])
        else:
            return "\n".join(self.frequently_asked_questions or [])


class MetadataValue(BaseModel):
    video: str | None = Field("", description="video URL")
    source: str | None = Field("", description="source path or URL")
    pub_date: Union[str, int] | None = Field(
        "", alias="pub-date", description="string as date. yyyyMMdd format"
    )
    pub_year: Union[str, int] | None = Field(
        "", alias="pub-year", description="string as date. yyyy format"
    )
    pub_year_month: Union[str, int] | None = Field(
        "", alias="pub-year-month", description="string as date. yyyyMM format"
    )
    title: str | None = Field("", description="source title")
    start_at: int | None = Field(None, description="video clip started at")
    chunk_no: int | None = Field(None, description="document chunk no")
    topic: str | None = Field("", description="document topic / category name")

    @field_validator("pub_date")
    def validate_date(cls, value):
        return date_from_yyyymmdd(value)

    @field_validator("pub_year_month")
    def validate_year_month(cls, value):
        return date_from_yyyymm(value)

    @field_validator("pub_year")
    def validate_year(cls, value):
        return date_from_yyyy(value)

    def to_dict(self, **kwargs) -> Dict[str, Union[str, int]]:
        model_dic = self.model_dump(**kwargs)
        for fname, finf in self.model_fields.items():
            if finf.alias and fname in model_dic:
                model_dic[finf.alias] = model_dic[fname]
                del model_dic[fname]
        return model_dic


class MetadataSchema(BaseModel):
    video: METADATA_TYPE | None = Field("str", alias="video", description="video link")
    source: METADATA_TYPE | None = Field(
        "str", alias="source", description="subtitle html link"
    )
    pub_date: METADATA_TYPE | None = Field(
        "str", alias="pub-date", description="video publish date"
    )
    pub_year: METADATA_TYPE | None = Field(
        "str", alias="pub-year", description="video publish year"
    )
    pub_year_month: METADATA_TYPE | None = Field(
        "str", alias="pub-year-month", description="video publish year and month"
    )
    title: METADATA_TYPE | None = Field(None, alias="title", description="video title")
    start_at: METADATA_TYPE | None = Field(
        "int", alias="start-at", description="video title"
    )
    chunk_no: METADATA_TYPE | None = Field(
        "int", alias="chunk-no", description="chunk no in the document"
    )
    topic: METADATA_TYPE | None = Field(
        "str",
        description="topic that will be attached to document.metadata and narrow the retriever",
    )


class RetrieverSettings(BaseModel):
    k: int = Field(10, description="get the top k after retrieved")
    score_threshold: float = Field(0.7, description="Threshold for retriever top-k")
    metadata: MetadataSchema
    collection_name: str = Field(description="collection name of vector db")


class GraderSettings(BaseModel):
    k: int | None = Field(4, description="number of keepings")


class ChainTemplates(BaseModel):
    intent_classify_model: MODEL_TYPES = Field(description="intent classification model type from 1. gemini 2. gpt-3.5 3. gpt-4")  # type: ignore
    intent_classify_template: str = Field(
        description="""Classify the user query if it is greeting-like or else.
                                        If greeting-like, the chain will be routed to greeting chain.
                                        Else the retriever and LLM answer chains will be used."""
    )
    greeting_model: MODEL_TYPES = Field(description="model type for greeting, from 1. gemini 2. gpt-3.5 3. gpt-4")  # type: ignore
    greeting_template: str = Field(description="Greeting-like question answer")
    answer_model: MODEL_TYPES = Field(description="model type for question answering, from 1. gemini 2. gpt-3.5 3. gpt-4")  # type: ignore
    answer_template: str = Field(
        description="Using the retriever result as context to call LLM for question answering"
    )
    query_rewrite_model: MODEL_TYPES = Field(description="model type for query rewrite, from 1. gemini 2. gpt-3.5 3. gpt-4")  # type: ignore
    query_rewrite_template: str = Field(
        description="prompt template for query rewrite for retriever"
    )
    grader_model: MODEL_TYPES = Field(description="grader models")
    grader_template: str = Field(
        description="grader template for question <-> document. return {'score': 'yes' or 'no'}"
    )


class InjestSettings(BaseModel):
    chunk_size: int = Field(description="chunk size when indexing.")
    chunk_overlap: int = Field(description="chunk overlap size.")
    injest_from: str = Field(description="source folder for data injestion")
    default_topic: str = Field(description="default topic when none valid topic given")


class CorsSettings(BaseModel):
    """CORS configuration.

    For more details on the CORS configuration, see:
    # * https://fastapi.tiangolo.com/tutorial/cors/
    # * https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
    """

    enabled: bool = Field(
        description="Flag indicating if CORS headers are set or not."
        "If set to True, the CORS headers will be set to allow all origins, methods and headers.",
        default=False,
    )
    allow_credentials: bool = Field(
        description="Indicate that cookies should be supported for cross-origin requests",
        default=False,
    )
    allow_origins: list[str] = Field(
        description="A list of origins that should be permitted to make cross-origin requests.",
        default=[],
    )
    allow_origin_regex: list[str] = Field(
        description="A regex string to match against origins that should be permitted to make cross-origin requests.",
        default=None,
    )
    allow_methods: list[str] = Field(
        description="A list of HTTP methods that should be allowed for cross-origin requests.",
        default=[
            "GET",
        ],
    )
    allow_headers: list[str] = Field(
        description="A list of HTTP request headers that should be supported for cross-origin requests.",
        default=[],
    )


class AuthSettings(BaseModel):
    """Authentication configuration.

    The implementation of the authentication strategy must
    """

    enabled: bool = Field(
        description="Flag indicating if authentication is enabled or not.",
        default=False,
    )
    secret: str = Field(
        description="The secret to be used for authentication. "
        "It can be any non-blank string. For HTTP basic authentication, "
        "this value should be the whole 'Authorization' header that is expected"
    )


class ServerSettings(BaseModel):
    port: int = Field(description="Port of PrivateGPT FastAPI server, defaults to 8001")
    cors: CorsSettings = Field(
        description="CORS configuration", default=CorsSettings(enabled=False)
    )
    auth: AuthSettings = Field(
        description="Authentication configuration",
        default_factory=lambda: AuthSettings(enabled=False, secret="secret-key"),
    )


class Settings(BaseModel):
    crawler: Crawler
    llm: LLMSettings
    embedding: EmbeddingSettings
    local: LocalSettings
    openai: OpenAISettings
    anthropic: AnthropicSettings
    groq: GroqSettings
    vectorstore: VectorstoreSettings
    qdrant: QdrantSettings
    google_api: GoogleSettings
    discord: DiscordSettings
    web_chat: WebUISettings
    web_ingest: IngestUISettings
    retriever: RetrieverSettings
    grader: GraderSettings
    chain_templates: ChainTemplates
    injest: InjestSettings
    server: ServerSettings


"""
This is visible just for DI or testing purposes.

Use dependency injection or `settings()` method instead.
"""
unsafe_settings = load_active_settings()

"""
This is visible just for DI or testing purposes.

Use dependency injection or `settings()` method instead.
"""
unsafe_typed_settings = Settings(**unsafe_settings)


def settings() -> Settings:
    """Get the current loaded settings from the DI container.

    This method exists to keep compatibility with the existing code,
    that require global access to the settings.

    For regular components use dependency injection instead.
    """
    from bao.di import global_injector

    return global_injector.get(Settings)
