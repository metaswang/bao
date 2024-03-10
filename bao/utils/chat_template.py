from collections import defaultdict
from typing import Any, Dict, List

from langchain_core.documents import Document

from bao.utils.strings import seconds_to_hh_mm_ss

RENDER_YOUTUBE_CLIP_FN = "fn_render_video_clip"
SHOW_ALL_QUOTES = "show_all_quotes"


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
        seen_refs[ref].add(documents[i].metadata.get(meta_start_at_key, 0))

    references_section = ""

    def find_ref_no(doc):
        for doc_id, i in enumerate(ref_docs):
            if documents[i].metadata.get(meta_video_key) == doc.metadata.get(
                meta_video_key
            ):
                return f"[{doc_id+1}]"
        return ""

    if len(documents):
        quote_text = ""
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
        render_fn = (
            other_keys.get(RENDER_YOUTUBE_CLIP_FN)
            if RENDER_YOUTUBE_CLIP_FN in other_keys
            and callable(other_keys[RENDER_YOUTUBE_CLIP_FN])
            else lambda x: seconds_to_hh_mm_ss(x[-1])
        )
        for doc_no, i in enumerate(ref_docs):
            document = documents[i]
            # render_fn
            start_seconds = sorted(seen_refs[document.metadata.get(meta_video_key)])
            clip_links = [render_fn(document.metadata.get(meta_video_key), s) for s in start_seconds]  # type: ignore
            video_clips = ", ".join(clip_links)
            reference_line = f"[{doc_no+1}]. [{document.metadata.get(meta_title_key)}]({document.metadata.get(meta_source_key)}) {video_clips}\n"
            references_section += reference_line
    return references_section
