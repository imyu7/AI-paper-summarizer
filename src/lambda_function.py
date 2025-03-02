from typing import Any

from src.application.slack_handler import SlackEventHandler
from src.dependency_injector import injector
from src.infrastructure.file_downloader.file_downloader import FileDownloader
from src.infrastructure.llm.llm import LLMService
from src.infrastructure.notion.notion import NotionRepository
from src.infrastructure.slack.slack import SlackService

slack_event_handler = SlackEventHandler(
    slack_service=injector.get(SlackService),
    content_downloader=injector.get(FileDownloader),
    llm_service=injector.get(LLMService),
    notion_repogitpry=injector.get(NotionRepository),
)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    _ = context  # NOTE: context は使用しない
    return slack_event_handler.handle_event(event)
