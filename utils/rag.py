import os
from collections import defaultdict
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain.chains.question_answering import load_qa_chain
from langchain_core.runnables import RunnableBranch
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from config.rag_config import rag_config
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from config.prompt_template import (
    QA_SYSTEM_PROMPT,
    CONTEXTUALIZE_Q_SYSTEM_PROMPT,
    QUESTION_CLASSIFY_TEMPLATE,
    GREETING_TEMPLATE,
)
from typing import Dict
from langchain.chains import TransformChain
from langchain_core.documents import Document
from utils.strings import hash_of_text, seconds_to_hh_mm_ss
from utils.ttl_dict import ChatHistDict
from utils.vectordb import load_qdrant
import cohere
import logging
import numpy as np
from utils.embeddings import EmbeddingsCache
import google.generativeai as genai
from utils.rag_hellper import flatten_dict


load_dotenv()

import logging

# Specify the log file name
log_file = os.getenv("LOG_FILE", "./data/discord.chat.log")

# Create a file handler with INFO logging level
file_handler = logging.handlers.RotatingFileHandler(
    log_file, maxBytes=1024000, backupCount=5
)
file_handler.setLevel(logging.INFO)

# Create a formatter for formatting log messages
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)

# Get the root logger and add the file handler to it
logger = logging.getLogger()
logger.addHandler(file_handler)

# Set the logging level to INFO (so that INFO and higher levels are logged)
logger.setLevel(logging.INFO)


class RAG:
    rag_yaml_cfg_key = "RAG_CFG"
    vector_idx_path_key = "INDEX_DIR"
    google_api_key = "GOOGLE_API_KEY"

    def __init__(self) -> None:
        genai.configure(api_key=os.getenv(RAG.google_api_key))
        self.embeddings = EmbeddingsCache()
        self.cfg = rag_config
        self.llm = ChatOpenAI(temperature=0.01, model=self.cfg.LLM.MODEL)
        self.cheap_llm = ChatOpenAI(temperature=0.8, model=self.cfg.LLM.CHEAP_MODEL)
        self.gemini_pro_llm = genai.GenerativeModel(self.cfg.LLM.FREE_MODEL_GEMINI)
        self.memory = ChatHistDict()
        self.db = load_qdrant(embeddings=self.embeddings)
        self.qa_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", QA_SYSTEM_PROMPT),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{question}"),
            ]
        )

        self.chat_chain = load_qa_chain(
            llm=self.llm, chain_type="stuff", verbose=True, prompt=self.qa_prompt
        )

        self.ir_chain = (
            RunnablePassthrough.assign(
                retriever_input=self.get_contextualized_chain,
            )
            | {"vector_result": self.get_vector_retriever_chain()}
            | self.get_rank_chain()
        )
        self.qa_chain = self.ir_chain | flatten_dict | self.chat_chain

        self.chain = RunnablePassthrough.assign(
            topic=lambda x: self.get_query_classify_chain(),
        ) | RunnableBranch(
            (
                lambda x: self.cfg.LLM_BRANCH_GREETING
                == x["topic"].get(self.cfg.TOPIC_KEY, self.cfg.LLM_BRANCH_OTHERS),
                {self.cfg.LLM_CHAIN_OUTPUT_KEY: self.get_greeting_chain()},
            ),
            self.qa_chain,
        )

    def get_query_classify_chain(self):
        from langchain_core.output_parsers.json import parse_json_markdown

        def parse_json(text):
            try:
                return parse_json_markdown(text)
            except:
                return {"type": self.cfg.LLM_BRANCH_OTHERS}

        def question_classify(input: Dict):
            resp = self.gemini_pro_llm.generate_content(
                QUESTION_CLASSIFY_TEMPLATE.format(
                    question=input.get(self.cfg.QUESTION_KEY)
                )
            )
            return {self.cfg.TOPIC_KEY: parse_json(resp.text)["type"]}

        return TransformChain(
            input_variables=[self.cfg.QUESTION_KEY],
            output_variables=[self.cfg.TOPIC_KEY],
            transform=question_classify,
        )

    def get_contextualized_chain(self, input: dict):
        if not input.get("chat_history"):
            input["chat_history"] = []
        contextualize_q_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    CONTEXTUALIZE_Q_SYSTEM_PROMPT.format(
                        key_q_vect=self.cfg.RETRIEVER_VECT.QUERY_KEY,
                        key_dt=self.cfg.METADATA.DATE,
                        key_year=self.cfg.METADATA.YEAR,
                        key_year_month=self.cfg.METADATA.YEAR_MONTH,
                        key_video=self.cfg.METADATA.REF_LINK,
                    ),
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{question}"),
            ]
        )
        return contextualize_q_prompt | self.llm | JsonOutputParser()

    def get_greeting_chain(self):
        q_prompt = ChatPromptTemplate.from_template(GREETING_TEMPLATE)
        return q_prompt | self.cheap_llm | StrOutputParser()

    def get_rank_chain(self):
        co = cohere.Client(os.getenv("COHERE_API_KEY"))

        def rerank(input: Dict):
            question = (
                input.get("vector_result", {})
                .get("retriever_input", {})
                .get(self.cfg.RETRIEVER_VECT.QUERY_KEY)
            )
            vector_docs = input.get("vector_result", {}).get("vector_docs", [])
            if len(vector_docs) <= self.cfg.RERANKER.K:
                return {"input_documents": vector_docs}

            docs_hash = dict([(hash_of_text(_.page_content), _) for _ in vector_docs])
            docs = docs_hash.values()
            rerank_resp = co.rerank(
                query=question,
                documents=[doc.page_content for doc in docs],
                top_n=self.cfg.RERANKER.K,
                model=self.cfg.RERANKER.MODEL,
            )
            return {
                "input_documents": [
                    docs_hash[hash_of_text(d.document["text"])] for d in rerank_resp
                ]
            }

        return TransformChain(
            input_variables=["vector_result"],
            output_variables=["input_documents"],
            transform=rerank,
        )

    def get_vector_retriever_chain(self):
        def vector_search(input: Dict):
            retriever_input = input.get("retriever_input", {})
            k = self.cfg.RETRIEVER_VECT.K
            filter = {
                k: retriever_input[k]
                for k in self.cfg.METADATA.KEYS
                if k in retriever_input
            } or None
            query = retriever_input.get(
                self.cfg.RETRIEVER_VECT.QUERY_KEY
            )  # reformulated key for vector retriever
            docs_and_similarities = self.db.similarity_search_with_score(
                query,
                k=k,
                filter=filter,
                score_threshold=self.cfg.RETRIEVER_VECT.SCORE_THRESHOLD,
            )
            docs = [doc for doc, _ in docs_and_similarities]
            scores = [score for _, score in docs_and_similarities]
            if scores:
                logger.info(
                    f"score distribution: max={max(scores)} min={min(scores)} avg={sum(scores)/len(scores):0.4f}"
                )
            return {
                "vector_docs": docs,
            }

        return TransformChain(
            transform=vector_search,
            input_variables=["retriever_input"],
            output_variables=["vector_docs"],
        )

    async def chat(self, message: str, author: str):
        logger.info(f"from @{author}: {message}")
        answer = await self.chain.ainvoke(
            {
                "question": message,
                "chat_history": self.memory.get(author, []),
            }
        )
        logger.info(f"from Bot: {answer.get(self.cfg.LLM_CHAIN_OUTPUT_KEY)}")
        self.memory.add(user=author, msg=HumanMessage(content=message))
        seen_refs = defaultdict(set)
        documents = answer.get(self.cfg.LLM_CHAIN_INPUT_KEY, [])
        ref_docs = []
        for i in range(len(documents)):
            ref = documents[i].metadata.get(self.cfg.METADATA.REF_LINK)
            if ref not in seen_refs:
                ref_docs.append(i)
            seen_refs[ref].add(
                seconds_to_hh_mm_ss(
                    documents[i].metadata.get(self.cfg.METADATA.START_AT, 0)
                )
            )

        references_section = (
            ("\n## References\n") if ref_docs else ""  # Start the references section
        )

        def find_ref(doc):
            for i in ref_docs:
                if documents[i].metadata.get(
                    self.cfg.METADATA.REF_LINK
                ) == doc.metadata.get(self.cfg.METADATA.REF_LINK):
                    return f"[{i+1}]"
            return ""

        quote_text = ""
        if len(documents):
            extract_quote = documents[0].page_content.replace("\n", " ")
            quote_text += "\n > " + extract_quote + f"{find_ref(documents[0])}\n"
            for j in range(1, len(documents)):
                quote_text += f"\n 查看更多？ 请点击下方链接 \n"
                break

        references_section += quote_text + "\n"
        for i in ref_docs:
            document = documents[i]
            start_at = ", ".join(
                sorted(seen_refs[document.metadata.get(self.cfg.METADATA.REF_LINK)])
            )
            reference_line = f"{i+1}. [{document.metadata.get(self.cfg.METADATA.TITLE)}]({document.metadata.get(self.cfg.METADATA.SOURCE)}) {start_at}\n"
            references_section += reference_line
        return answer.get(self.cfg.LLM_CHAIN_OUTPUT_KEY) + references_section
