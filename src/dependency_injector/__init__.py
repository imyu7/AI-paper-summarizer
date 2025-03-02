from injector import Binder, Injector

from src.domain.services import (
    IContentDownloader,
    ILLMService,
    INotionRepogitory,
    ISlackService,
)
from src.infrastructure.file_downloader.file_downloader import FileDownloader
from src.infrastructure.llm.llm import LLMService
from src.infrastructure.notion.notion import NotionRepository
from src.infrastructure.slack.slack import SlackService


def configure(binder: Binder) -> None:
    binder.bind(ISlackService, SlackService)  # type: ignore[type-abstract]
    binder.bind(IContentDownloader, FileDownloader)  # type: ignore[type-abstract]
    binder.bind(ILLMService, LLMService)  # type: ignore[type-abstract]
    binder.bind(INotionRepogitory, NotionRepository)  # type: ignore[type-abstract]


injector = Injector(configure)
