import os
import json
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from tqdm.auto import tqdm
from utils.embeddings import EmbeddingsCache
from utils.strings import hash_of_text, extract_times_to_seconds
from dotenv import load_dotenv
from config.rag_config import rag_config
from utils.vectordb import load_qdrant

load_dotenv()


def main():
    print(rag_config)
    chunk_size = rag_config.INDEX.CHUNK_SIZE
    chunk_overlap = rag_config.INDEX.CHUNK_OVERLAP
    src_dir = rag_config.INDEX.CRAWL_DIR
    embeddings = EmbeddingsCache()
    db = load_qdrant(embeddings)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )

    def load_and_split_documents(directory):
        """Reads all .txt files in the given directory and prints their contents."""
        print(f"documents will be loaded from: {directory}")
        buff_window = []
        buff_size = 1000
        total_num_docs = 0
        total_num_pages = 0

        def add_to_buffer(documents):
            buff_window.extend(documents)
            total_num_docs += len(documents)
            # sync to db
            if len(buff_window) > buff_size:
                db.add_documents(buff_window)
                buff_window.clear()

        for filename in tqdm(os.listdir(directory)):
            if filename.endswith(".pdf"):
                PyPDFLoader
            if filename.endswith(".txt"):
                tim = 0
                total_num_pages += 1
                full_path = os.path.join(directory, filename)
                docs = TextLoader(full_path).load()
                json_fn = full_path[:-3] + "json"
                with open(json_fn, "rb") as f:
                    meta = json.load(f)
                    for d in docs:
                        d.metadata.update(meta)
                documents = text_splitter.split_documents(docs)
                for d in documents:
                    trans = d.page_content
                    ts_arr = extract_times_to_seconds(trans)
                    if ts_arr:
                        d.metadata.update({rag_config.METADATA.START_AT: ts_arr[0]})
                        tim = ts_arr[-1]
                    else:
                        d.metadata.update({rag_config.METADATA.START_AT: tim})
                    if d.metadata.get(rag_config.METADATA.DATE):
                        d.metadata[rag_config.METADATA.YEAR] = d.metadata.get(
                            rag_config.METADATA.DATE
                        )[:4]
                        d.metadata[rag_config.METADATA.YEAR_MONTH] = d.metadata.get(
                            rag_config.METADATA.DATE
                        )[:6]
                add_to_buffer(documents)

        print(f"total #pages processed: {total_num_pages}")
        print(f"total #documents: {total_num_docs}")

    load_and_split_documents(src_dir)
    print("Done.")


if __name__ == "__main__":
    main()
