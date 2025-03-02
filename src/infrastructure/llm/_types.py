from typing import Any, TypeVar

from openai.types.chat import ChatCompletion, ChatCompletionMessageParam

# -----------------------------
# Type definitions
# -----------------------------
LLMInputType = TypeVar("LLMInputType")
LLMOutputType = TypeVar("LLMOutputType")
Messages = list[ChatCompletionMessageParam]
Response = ChatCompletion
LLMSettings = dict[str, Any]
ClientSettings = dict[str, Any]
