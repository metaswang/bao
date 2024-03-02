import logging
from pathlib import Path
from typing import Any, List, Optional

import gradio as gr
from fastapi import FastAPI
from injector import inject, singleton

from bao import PROJECT_ROOT_PATH
from bao.settings.settings import Settings
from bao.components.injest.injest_service import InjestService, SOURCE_KEY

logger = logging.getLogger(__name__)

RELATIVE_PATH = Path(__file__).parent.relative_to(PROJECT_ROOT_PATH)


@singleton
class IngestUI:

    @inject
    def __init__(self, ingest_service: InjestService, settings: Settings) -> None:
        self._ui = None
        self.ingestor = ingest_service
        self.settings = settings
        self.selected_source = None
        self.filter_text = ""

    def _select_list_item(self, select_data: gr.SelectData) -> Any:
        self.selected_source = select_data.value
        return [
            gr.components.Button(interactive=True),
            gr.components.Button(interactive=True),
        ]

    def _list(self) -> List[List[str]]:
        return self.ingestor.list_sources(title_like=self.filter_text)

    def _upload(self, files: List[str]) -> None:
        file_paths = [Path(_) for _ in files]
        file_names = [_.name for _ in file_paths]
        # (entry data: dict, index)
        valid_sources = [
            (self.ingestor._load_entry(_), i) for i, _ in enumerate(file_paths)
        ]
        # (source, path_index)
        valid_sources = [
            (_[0].get(SOURCE_KEY, file_names[_[1]]), _[1])
            for _ in valid_sources
            if _ is not None
        ]
        # first batch remove
        self.ingestor.remove(
            source_key=SOURCE_KEY, source_values=[_[0] for _ in valid_sources]
        )
        # then insert
        for _, i_path in valid_sources:
            self.ingestor.injest_file(file_paths[i_path])

    def _select_source(self, select_data: gr.SelectData):
        self.selected_source = select_data.value
        return [
            gr.components.Button(interactive=True),  # delete
            gr.components.Button(interactive=True),  # delete all
            gr.components.Textbox(self.selected_source),  # source
        ]

    def _filter_submit(self, filter_text):
        self.filter_text = filter_text
        return self.ingestor.list_sources(title_like=self.filter_text)

    def _remove(self):
        if self.selected_source:
            self.ingestor.remove(
                source_key=SOURCE_KEY, source_values=[self.selected_source]
            )

    def _remove_all(self):
        points = self.ingestor.list_sources(title_like=self.filter_text)
        sources = [_[0] for _ in points]
        self.ingestor.remove(source_key=SOURCE_KEY, source_values=sources)

    def _build_ui(self) -> gr.Blocks:
        with gr.Blocks(
            title="Ingest UI",
            theme=gr.themes.Soft(primary_hue=gr.themes.colors.blue),
            css=".logo { "
            "display:flex;"
            f"background-color: {self.settings.web_chat.header_color};"
            "height: 50px;"
            "border-radius: 5px;"
            "align-content: center;"
            "justify-content: center;"
            "align-items: center;"
            "}"
            ".logo img { height: 60%;}"
            ".contain { display: flex !important; flex-direction: column !important; }",
        ) as blocks:
            with gr.Row(equal_height=False):
                with gr.Column(scale=10):
                    filter_source = gr.Textbox(
                        label="Filter Source (press Enter to submit)",
                        max_lines=1,
                        autofocus=True,
                    )
            with gr.Row(equal_height=False):
                with gr.Column(scale=10):
                    data_list = gr.List(
                        self._list,
                        label="Filtered Data",
                        headers=["Source"],
                        datatype=["str"],
                        height=300,
                        interactive=False,
                    )
            with gr.Row():
                btn_upload = gr.components.UploadButton(
                    "Upload", scale=2, file_count="multiple", type="filepath", size="sm"
                )
                btn_remove = gr.Button("Remove Selected", interactive=False)
                btn_remove_all = gr.Button("Remove All", interactive=False)
            data_list.change(self._list, outputs=data_list)
            filter_source.submit(
                self._filter_submit, inputs=filter_source, outputs=data_list
            )
            btn_upload.upload(self._upload, inputs=btn_upload, outputs=data_list)
            btn_remove.click(self._remove, outputs=data_list)
            btn_remove_all.click(self._remove_all, outputs=data_list)
            data_list.select(
                self._select_list_item, outputs=[btn_remove, btn_remove_all]
            )
            return blocks

    def get_ui(self) -> gr.Blocks:
        if self._ui is None:
            self._ui = self._build_ui()
        return self._ui

    def mount_in_app(self, app: FastAPI, path: str) -> None:
        blocks = self.get_ui()
        blocks.queue()
        logger.info("Mounting the ingest gradio UI, at path=%s", path)
        gr.mount_gradio_app(app, blocks, path=path)
