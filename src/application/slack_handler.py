import json
import logging
import re
from typing import Any

from injector import inject

from src.domain.models import Paper
from src.domain.services import (
    IContentDownloader,
    ILLMService,
    INotionRepogitory,
    ISlackService,
)

logger = logging.getLogger(__name__)


class SlackEventHandlerError(Exception):
    pass


class SlackEventHandler:
    @inject
    def __init__(
        self,
        slack_service: ISlackService,
        content_downloader: IContentDownloader,
        llm_service: ILLMService,
        notion_repogitpry: INotionRepogitory,
    ) -> None:
        self.slack_service = slack_service
        self.content_downloader = content_downloader
        self.llm_service = llm_service
        self.notion_repogitpry = notion_repogitpry

    def handle_event(self, event: dict[str, Any]) -> dict[str, Any]:
        if "X-Slack-Retry-Num" in event.get("headers", {}):
            return {"statusCode": 200}
        body = self._parse_event_body(event)
        if "challenge" in body:
            return {
                "statusCode": 200,
                "body": json.dumps({"challenge": body["challenge"]}),
            }
        slack_event = body.get("event", {})
        if slack_event.get("type") == "app_mention":
            self.handle_mention(slack_event)
        return {"statusCode": 200}

    def _parse_event_body(self, event: dict[str, Any]) -> dict[str, Any]:
        try:
            body = json.loads(event.get("body", "{}"))
        except Exception:
            body = {}
        return body

    def handle_mention(self, slack_event: dict[str, Any]) -> None:
        if "thread_ts" not in slack_event:
            self._handle_main_message(slack_event)
        else:
            self._handle_thread_message(slack_event)

    def _handle_main_message(self, slack_event: dict[str, Any]) -> None:
        try:
            target_url = self._extract_url_from_blocks(slack_event.get("blocks", []))
        except ValueError:
            self.slack_service.post_message(
                channel=slack_event["channel"],
                message="URLが見つかりませんでした。",
                thread_ts=slack_event.get("ts"),
            )
            return

        try:
            content = self.content_downloader.download_content(target_url)
        except Exception:
            self.slack_service.post_message(
                slack_event["channel"],
                "コンテンツのダウンロードに失敗しました。",
                slack_event.get("ts"),
            )
            return

        try:
            title = self.llm_service.generate_title(content)
            summary = self.llm_service.generate_summary(content)
            category = self.llm_service.generate_category(content)
            brief_digest = self.llm_service.generate_brief_digest(summary)
            paper = Paper(
                title=title,
                url=target_url,
                brief_digest=brief_digest,
                category=category,
                summary=summary,
            )
        except Exception:
            self.slack_service.post_message(
                slack_event["channel"],
                "コンテンツの処理に失敗しました。",
                slack_event.get("ts"),
            )
            return

        # 論文タイトルと URL を Slack に投稿
        self.slack_service.post_message(slack_event["channel"], f"{paper.title}\n{paper.url}", slack_event["ts"])
        # 論文の要約を Slack に投稿
        for question, answer in paper.summary.items():
            self.slack_service.post_message(slack_event["channel"], f"{question}\n\n{answer}", slack_event["ts"])

        try:
            self.notion_repogitpry.add_content(paper)
        except Exception:
            logger.exception("Failed to add content to Notion")

    def _handle_thread_message(self, slack_event: dict[str, Any]) -> None:
        question, answer, url = self._answer_message_from_history(slack_event)
        self.slack_service.post_message(slack_event["channel"], answer, slack_event["thread_ts"])
        try:
            if url:
                self.notion_repogitpry.update_content(url, {"question": question, "answer": answer})
        except Exception:
            logger.exception("Failed to update content in Notion")

    def _answer_message_from_history(self, slack_event: dict[str, Any]) -> tuple[str, str, str | None]:
        messages = []
        first_url = None
        conversations = self.slack_service.get_conversations(slack_event["channel"], slack_event["thread_ts"])
        if not conversations.get("ok"):
            raise SlackEventHandlerError
        for chat_message in conversations.get("messages", [])[-30:]:
            if chat_message.get("bot_id"):
                messages.append({"role": "assistant", "content": chat_message.get("text", "")})
            elif "attachments" in chat_message and "original_url" in chat_message["attachments"][0] and not first_url:
                first_url = chat_message["attachments"][0]["original_url"]
                content = self.content_downloader.download_content(first_url)
                messages.append({"role": "user", "content": content})
            else:
                messages.append({"role": "user", "content": chat_message.get("text", "")})
        answer = self.llm_service.generate_chat_response(messages)
        if not first_url:
            logger.warning("URL not found in thread messages")
        return re.sub(r"<[^>]*>", "", messages[-1]["content"]), answer, first_url

    def _extract_url_from_blocks(self, blocks: list[Any]) -> str:
        for block in blocks:
            for element in block.get("elements", []):
                for inner in element.get("elements", []):
                    if inner.get("type") == "link":
                        return inner.get("url", "").strip()
        raise KeyError
