from typing import Any, Dict

from injector import inject, singleton
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable

from bao.components.llms import LLMs
from bao.settings.settings import Settings
from langchain_core.output_parsers.json import JsonOutputParser
from langchain.chains.transform import TransformChain


@singleton
class Grader:
    @inject
    def __init__(self, settings: Settings, llms: LLMs) -> None:
        self.settings = settings
        self.llms = llms

    def chain(
        self, fallback: bool = False
    ) -> RunnableSerializable[Dict[str, Any], Dict[str, Any]]:
        llm = self.llms.get_llm(
            llm_type=self.settings.chain_templates.grader_model[1 if fallback else 0]
        )
        chat_template = ChatPromptTemplate.from_messages(
            [
                ("system", self.settings.chain_templates.grader_template),
                (
                    "human",
                    """Document: 
                    {document} 
                    
                    Question: 
                    {question}""",
                ),
            ]
        )

        def grader(input: Dict[str, Any]) -> Dict[str, Any]:
            question = input.get("question")
            docs = input.get("vector_docs", [])
            if not docs:
                return {"input_documents": []}
            q_docs = [{"question": question, "document": _.page_content} for _ in docs]
            chain = chat_template | llm | JsonOutputParser()
            results = chain.batch(q_docs, {"max_concurrency": len(q_docs)})
            doc_idx_relevant = [
                i for i, res in enumerate(results) if res["score"] == "yes"
            ]
            return {
                "input_documents": [docs[_] for _ in doc_idx_relevant][
                    : self.settings.grader.k
                ]
            }

        return TransformChain(
            transform=grader,
            input_variables=["question", "vector_docs"],
            output_variables=["input_documents"],
        )  # type: ignore
