import os
from typing import Any

import requests  # type: ignore[import-untyped]

from src.domain.services import ISlackService


class SlackRequestError(Exception):
    pass


class SlackService(ISlackService):
    BASE_URL = "https://slack.com/api"

    def __init__(self) -> None:
        self.token = os.environ["SLACK_TOKEN"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json; charset=utf-8",
        }

    def post_message(self, channel: str, message: str, thread_ts: str | None = None) -> None:
        url = f"{self.BASE_URL}/chat.postMessage"
        data = {
            "channel": channel,
            "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": message}}],
        }
        if thread_ts:
            data["thread_ts"] = thread_ts
        self._send_request("POST", url, json=data)

    def get_conversations(self, channel: str, ts: str) -> dict[str, Any]:
        url = f"{self.BASE_URL}/conversations.replies"
        params = {"channel": channel, "ts": ts}
        return self._send_request("GET", url, params=params)

    def _send_request(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        try:
            if method.upper() == "POST":
                response = requests.post(url, headers=self.headers, timeout=5, **kwargs)
            else:
                response = requests.get(url, headers=self.headers, timeout=5, **kwargs)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise SlackRequestError from e
