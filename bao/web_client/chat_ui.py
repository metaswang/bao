import logging
from pathlib import Path
from typing import List

import gradio as gr
from fastapi import FastAPI
from injector import inject, singleton

from bao import PROJECT_ROOT_PATH
from bao.settings.settings import Settings
from bao.components.chat import Chat, ChatRequestBody, ChatResponse
from bao.settings.settings import settings

logger = logging.getLogger(__name__)

RELATIVE_PATH = Path(__file__).parent.relative_to(PROJECT_ROOT_PATH)


DEFAULT_CHAT_MODE_ASK, DEFAULT_CHAT_MODE_SEARCH = settings().web_chat.work_modes
DEFAULT_CHAT_MODE = [DEFAULT_CHAT_MODE_ASK, DEFAULT_CHAT_MODE_SEARCH]


@singleton
class ChatUI:

    @inject
    def __init__(self, chat: Chat, settings: Settings) -> None:
        self._ui = None
        self.chat = chat
        self.settings = settings

    async def _chat(self, message: str, history: List[List[str]], mode: str) -> str:
        is_retriever_mode = mode == DEFAULT_CHAT_MODE_SEARCH
        if is_retriever_mode:
            message = "/s" + message
        res: ChatResponse = await self.chat.chat(input=ChatRequestBody(question=message, chat_history=history))  # type: ignore
        if is_retriever_mode:
            return res.reference
        else:
            return f"{res.answer}\n\n\n## References:\n\n{res.reference}"

    def _build_ui(self) -> gr.Blocks:
        with gr.Blocks(
            title="Bob Bot",
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
            ".contain { display: flex !important; flex-direction: column !important; }"
            "#component-0, #component-3, #component-10, #component-8  { height: 100% !important; }"
            "#chatbot { flex-grow: 1 !important; overflow: auto !important;}"
            "#baobot { height: calc(100vh - 200px) !important; }"
            "blockquote {"
            "padding: 0 1em !important; "
            "border-left: .3em solid !important; "
            "}",
        ) as blocks:
            with gr.Row(equal_height=False) as r:
                logo = f"{RELATIVE_PATH}/static/logo.png"
                logo_path = r.move_resource_to_block_cache(logo)
                gr.HTML(
                    f"<div class='logo'/><img src='file={logo_path}' alt='BaoGPT'>{self.settings.web_chat.title}</div"
                )
            with gr.Row(equal_height=False):
                with gr.Column(scale=10):
                    mode = gr.Radio(
                        DEFAULT_CHAT_MODE,  # type: ignore
                        label=self.settings.web_chat.work_mode_label,
                        value=DEFAULT_CHAT_MODE_SEARCH,
                    )
            with gr.Row(equal_height=False):
                with gr.Column(scale=10, elem_id="baobot"):
                    _ = gr.ChatInterface(
                        self._chat,
                        chatbot=gr.Chatbot(
                            show_copy_button=True,
                            elem_id="chatbot",
                            render=False,
                            avatar_images=(
                                None,
                                f"{RELATIVE_PATH}/static/bob_bot.ico",
                            ),
                            render_markdown=True,
                        ),
                        retry_btn=None,
                        undo_btn=self.settings.web_chat.btn_undo,
                        clear_btn=self.settings.web_chat.btn_clear,
                        submit_btn=self.settings.web_chat.btn_submit,
                        additional_inputs=[mode],
                    )
            return blocks

    def get_ui(self) -> gr.Blocks:
        if self._ui is None:
            self._ui = self._build_ui()
        return self._ui

    def mount_in_app(self, app: FastAPI, path: str) -> None:
        blocks = self.get_ui()
        blocks.queue()
        logger.info("Mounting the Chat gradio UI, at path=%s", path)
        gr.mount_gradio_app(app, blocks, path=path)
