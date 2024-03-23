from typing import Any, Dict, List, Optional, Tuple

from langchain_anthropic import ChatAnthropic
from langchain_core.callbacks import AsyncCallbackManagerForLLMRun
from langchain_core.language_models.chat_models import agenerate_from_stream
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult


class ChatAnthropicWithCallback(ChatAnthropic):

    streaming: bool = False

    class Config:
        """Configuration for this pydantic object."""

        allow_population_by_field_name = True

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        stream: Optional[bool] = None,
        **kwargs: Any,
    ) -> ChatResult:
        should_stream = stream if stream is not None else self.streaming
        if should_stream:
            stream_iter = self._astream(
                messages, stop=stop, run_manager=run_manager, **kwargs
            )
            return await agenerate_from_stream(stream_iter)
        params = self._format_params(messages=messages, stop=stop, **kwargs)
        data = await self._async_client.messages.create(**params)
        return self._format_output(data, **kwargs)
