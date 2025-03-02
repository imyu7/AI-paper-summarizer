from abc import ABC, abstractmethod
from typing import Any

from .models import Paper


class IContentDownloader(ABC):
    @abstractmethod
    def download_content(self, url: str) -> str:
        """指定された URL からコンテンツをダウンロードし、テキスト（もしくは Markdown 化された HTML）として返す"""


class ILLMService(ABC):
    @abstractmethod
    def generate_title(self, text: str) -> str:
        """タイトル抽出のための LLM 呼び出し"""

    @abstractmethod
    def generate_summary(self, text: str) -> dict[str, str]:
        """詳細な要約のための LLM 呼び出し"""

    @abstractmethod
    def generate_category(self, text: str) -> list[str]:
        """カテゴリ分類のための LLM 呼び出し"""

    @abstractmethod
    def generate_brief_digest(self, summary: dict[str, str]) -> str:
        """短い要約（ダイジェスト）のための LLM 呼び出し"""

    @abstractmethod
    def generate_chat_response(self, messages: list[dict[str, Any]]) -> str:
        """会話のための LLM 呼び出し"""


class INotionRepogitory(ABC):
    @abstractmethod
    def add_content(self, paper: Paper) -> None:
        """Notion に新しいコンテンツを追加する"""

    @abstractmethod
    def update_content(self, url: str, contents: dict[str, Any]) -> None:
        """Notion のコンテンツを更新する"""


class ISlackService(ABC):
    @abstractmethod
    def post_message(self, channel: str, message: str, thread_ts: str | None = None) -> None:
        """指定されたメッセージを Slack に通知する"""

    @abstractmethod
    def get_conversations(self, channel: str, ts: str) -> dict[str, Any]:
        """指定されたスレッドのメッセージを取得する"""
