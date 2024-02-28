import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, BinaryIO

import yaml
from dotenv import load_dotenv
from injector import inject, singleton

load_dotenv()
import logging

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from qdrant_client.http import models
from tqdm.auto import tqdm

from bao.settings.settings import Settings
from bao.utils.embeddings import EmbeddingsCache
from bao.utils.injest_event_sync import InjestEventSync
from bao.utils.strings import extract_times_to_seconds, get_metadata_alias
from bao.utils.vectordb import load_qdrant

logger = logging.getLogger(__name__)


@singleton
class InjestService:
    @inject
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.embeddings = EmbeddingsCache()
        chunk_size = self.settings.injest.chunk_size
        chunk_overlap = self.settings.injest.chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        self.app_name = self.settings.retriever.collection_name
        self.db = load_qdrant(self.embeddings)
        self.event_sync = InjestEventSync(db_root=self.settings.injest.injest_from)

    def _find_all_entries(self) -> List[Path]:
        """
        Find all yaml files with keys:
        video, source, start-at, content, pub-date, pub-year, pub-yea-month, chunk-no
        The files should not be injested to db before
        """
        entries = list(Path(self.settings.injest.injest_from).glob("*/*.yaml"))
        entries = [_ for _ in entries if _.is_file()]
        enames = {
            e.name.split(os.path.sep)[-1][:-5]: i for i, e in enumerate(entries)
        }  # w/o .yaml
        # find them in db
        new_enames = self.event_sync.find_new_entries(
            app_name=self.app_name, entry_name_list=enames.keys()
        )
        return [entries[enames[e]] for e in new_enames]

    def _load_entry(self, entry_path: Path) -> Dict[str, Any]:
        with open(entry_path, "r") as f:
            data = yaml.safe_load(f)
            if not isinstance(data, dict):
                return None  # type: ignore
            if "metadata" not in data or "content" not in data:
                return None  # type: ignore
            return data

    def injest_bin(self, yaml_bin: BinaryIO) -> List[Document]:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            try:
                content = yaml_bin.read()
                path_to_tmp = Path(tmp.name)
                path_to_tmp.write_bytes(content)
                return self.injest_file(path_to_tmp)
            finally:
                tmp.close()
                path_to_tmp.unlink()

    def injest_file(self, yaml_file_path: Path) -> List[Document]:
        entry = yaml_file_path
        if not entry.exists() or not entry.is_file():
            raise ValueError(
                f"param value for yaml_file_path : {yaml_file_path} is invalid."
            )
        docs = self._injest_entry(Path(yaml_file_path))
        self.db.add_documents(docs)
        self.event_sync.batch_insert_event(self.app_name, [entry.name])
        return docs

    def _injest_entry(self, entry_yaml: Path) -> List[Document]:
        topic = entry_yaml.parent.name
        tim = 0
        entry_data = self._load_entry(entry_yaml)
        if not entry_data:
            logging.warning(f"{entry_yaml} is not a valid data entry.")
        metadata = entry_data["metadata"]
        if "topic" not in metadata:
            metadata["topic"] = topic
        if "source" not in metadata:
            metadata["source"] = entry_yaml.name  # make sure the source is not empty
        docs = [Document(page_content=entry_data["content"], metadata=metadata)]
        # if the source exist in metadata
        documents = self.text_splitter.split_documents(docs)
        for chunk_no, d in enumerate(documents):
            trans = d.page_content
            ts_arr = extract_times_to_seconds(trans)
            if ts_arr:
                d.metadata.update({"start-at": ts_arr[0]})
                tim = ts_arr[-1]
            else:
                d.metadata.update({"start-at": tim})
            if d.metadata.get("pub-date"):  # yyyyMMdd
                d.metadata["pub-year"] = d.metadata["pub-date"][:4]
                d.metadata["pub-year-month"] = d.metadata["pub-date"][:6]
            d.metadata["chunk-no"] = chunk_no
        return documents

    def _injest_from_folder(self):
        """
        Reads all .txt files in the given directory

        """

        def sync():
            if buff_window:
                self.db.add_documents(buff_window)
                synced_entries.extend([d.metadata["source"] for d in buff_window])
                buff_window.clear()

        def add_to_buffer(documents: List[Document]):
            nonlocal total_num_docs
            nonlocal buff_window
            nonlocal buff_size
            buff_window.extend(documents)
            total_num_docs += len(documents)
            # sync to db
            if len(buff_window) > buff_size:
                sync()

        root_directory = self.settings.injest.injest_from
        logger.info(f"documents will be loaded from: {root_directory}")
        yaml_entries = self._find_all_entries()
        buff_window: List[Document] = []
        synced_entries = []
        buff_size = 1000
        total_num_docs = 0
        total_num_pages = 0

        root_directory = Path(root_directory)
        for entry_yaml in tqdm(yaml_entries):
            documents = self._injest_entry(entry_yaml)
            add_to_buffer(documents)
            total_num_pages += 1
        sync()
        self.event_sync.batch_insert_event(self.app_name, list(set(synced_entries)))
        logger.info(f"total #pages processed: {total_num_pages}")
        logger.info(f"total #documents: {total_num_docs}")

    def injest_folder(self):
        logger.info("Begin data injest ...")
        logger.info(f"injest operation on {self.settings.retriever.collection_name}")
        self._injest_from_folder()
        logger.info("Done.")

    def remove(self, source_key: str, source_values: List[str]) -> None:
        """Remove by sources"""
        logger.info(f"del operation on {self.settings.retriever.collection_name}")
        if source_key not in get_metadata_alias(self.settings.retriever.metadata):
            raise ValueError(f"{source_key} is invalid metadata field.")
        if not source_values:
            raise ValueError(f"param: meta_value is empty.")
        # find all related record ids
        filters = models.Filter(
            must=[
                models.FieldCondition(
                    key=f"metadata.{source_key}",
                    match=models.MatchAny(any=source_values),
                )
            ]
        )
        points_selector = models.FilterSelector(filter=filters)
        self.db.client.delete(
            collection_name=self.settings.retriever.collection_name,
            points_selector=points_selector,
        )
        self.event_sync.remove(self.app_name, source_values)
