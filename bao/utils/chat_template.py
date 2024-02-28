from collections import defaultdict
from typing import List, Any, Dict

from langchain_core.documents import Document

from bao.utils.strings import seconds_to_hh_mm_ss


def gen_refence(
    documents: List[Document],
    meta_title_key: str = "title",
    meta_source_key: str = "source",
    meta_video_key: str = "video",
    meta_start_at_key: str = "start-at",
    show_all_quotes: bool = False,
    **other_keys: Dict[str, Any],
) -> str:
    """
    Generate the refences for the bot answer with given documents which the answer comes from.
    """
    seen_refs = defaultdict(set)
    ref_docs = []
    for i in range(len(documents)):
        ref = documents[i].metadata.get(meta_video_key)
        if ref not in seen_refs:
            ref_docs.append(i)
        seen_refs[ref].add(
            seconds_to_hh_mm_ss(documents[i].metadata.get(meta_start_at_key, 0))
        )

    references_section = ""

    def find_ref_no(doc):
        for i in ref_docs:
            if documents[i].metadata.get(meta_video_key) == doc.metadata.get(
                meta_video_key
            ):
                return f"[{i+1}]"
        return ""

    quote_text = ""
    if len(documents):
        if not show_all_quotes:
            extract_quote = documents[0].page_content.replace("\n", " ")
            quote_text += "\n> " + extract_quote + f"{find_ref_no(documents[0])}\n"
            for _ in range(1, len(documents)):
                quote_text += f"\nVew more? Please click the link below. \n"
                break
        else:
            for d in documents:
                extract_quote = d.page_content.replace("\n", " ")
                quote_text += "\n> " + extract_quote + f"{find_ref_no(d)}\n\n"

    references_section += quote_text + "\n"
    for i in ref_docs:
        document = documents[i]
        start_at = ", ".join(sorted(seen_refs[document.metadata.get(meta_video_key)]))
        reference_line = f"{i+1}. [{document.metadata.get(meta_title_key)}]({document.metadata.get(meta_source_key)}) {start_at}\n"
        references_section += reference_line
    return references_section
