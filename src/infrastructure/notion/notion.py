import logging
import os
from typing import Any

from notion_client import Client

from src.domain.models import Paper
from src.domain.services import INotionRepogitory

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class NotionRequestError(Exception):
    pass


def get_notion_client() -> Client:
    return Client(auth=os.environ["NOTION_KEY"])


class NotionRepository(INotionRepogitory):
    def __init__(self) -> None:
        self.database_id = os.environ["NOTION_DATABASE_ID"]

    def add_content(self, paper: Paper) -> None:
        client = get_notion_client()
        properties = {
            "title": {"title": [{"text": {"content": paper.title}}]},
            "url": {"url": paper.url},
            "summary": {"rich_text": [{"text": {"content": paper.brief_digest}}]},
            "tag": {"multi_select": [{"name": tag} for tag in paper.category]},
        }
        children = [{"object": "block", "type": "table_of_contents", "table_of_contents": {}}]
        for question, answer in paper.summary.items():
            children.append(self._create_callout_block(emoji="❓", title=question, content=answer))
        try:
            response = client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties,
                children=children,
            )
            logger.info("Notion page created: %s", response)
        except Exception as e:
            raise NotionRequestError from e

    def update_content(self, url: str, contents: dict[str, Any]) -> None:
        client = get_notion_client()
        page_id = self._fetch_page_id(url)
        if not page_id:
            logger.error("No page found with URL: %s", url)
            return
        children = [self._create_callout_block("💬", contents["question"], contents["answer"])]
        try:
            response = client.blocks.children.append(
                block_id=page_id,
                children=children,
            )
            logger.info("Notion update response: %s", response)
        except Exception as e:
            raise NotionRequestError from e

    def _fetch_page_id(self, url: str) -> str | None:
        client = get_notion_client()
        try:
            response = client.databases.query(database_id=self.database_id)
            for result in response.get("results", []):  # type: ignore[union-attr]
                try:
                    if result["properties"]["url"]["url"] == url:
                        return result["id"]
                except Exception as e:
                    raise NotionRequestError from e
        except Exception as e:
            raise NotionRequestError from e

        return None

    def _create_callout_block(self, emoji: str, title: str, content: str) -> dict[str, Any]:
        return {
            "object": "block",
            "type": "callout",
            "callout": {
                "color": "default",
                "icon": {"emoji": emoji, "type": "emoji"},
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": title},
                        "annotations": {"bold": True},
                    }
                ],
                "children": [
                    {"object": "block", "type": "divider", "divider": {}},
                    {
                        "object": "block",
                        "paragraph": {"rich_text": [{"text": {"content": content}}]},
                    },
                ],
            },
        }
