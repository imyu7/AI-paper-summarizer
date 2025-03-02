from abc import ABC, abstractmethod
import os
from typing import Any, Generic

from openai import OpenAI

from src.domain.services import ILLMService
from src.infrastructure.llm._types import ClientSettings, LLMInputType, LLMOutputType, LLMSettings, Messages, Response
from src.infrastructure.llm.utils import dict2json, json2dict


# -----------------------------
# Abstract Base Class
# -----------------------------
class AbstractLLM(ABC, Generic[LLMInputType, LLMOutputType]):
    def __init__(self, model: str, llm_settings: LLMSettings, client_settings: ClientSettings) -> None:
        self.llm_settings = llm_settings
        self.model = model
        self.client = OpenAI(**client_settings)

    @abstractmethod
    def preprocess(self, inputs: LLMInputType) -> Messages:
        pass

    def _generate(self, messages: Messages) -> Response:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **self.llm_settings,
        )
        return response

    @abstractmethod
    def postprocess(self, response: Response) -> LLMOutputType:
        pass

    def __call__(self, inputs: LLMInputType) -> LLMOutputType:
        messages = self.preprocess(inputs)
        response = self._generate(messages)
        return self.postprocess(response)


# -----------------------------
# Concrete Classes
# -----------------------------
class TitleExtractor(AbstractLLM[str, str]):
    def preprocess(self, inputs: str) -> Messages:
        output_format = {"title": "(string) Title of the content"}
        system_prompt = f"あなたは研究論文のタイトル抽出AIである。以下の形式に従い論文タイトルを抽出せよ。\n{dict2json(output_format)}"
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "テキストからタイトルを抽出せよ:\n" + inputs},
        ]

    def postprocess(self, response: Response) -> str:
        output_dict = json2dict(response.choices[0].message.content or "")
        return output_dict.get("title", "No Title")


class ContentSummarizer(AbstractLLM[dict[str, Any], dict[str, str]]):
    @property
    def questions(self) -> dict[str, str]:
        return {
            "Q1": "何に関する論文か、専門外の研究者向けに詳しく説明してください。",
            "Q2": "論文の内容を、背景、新規性、方法などに分けて詳しく説明してください。",
            "Q3": "本研究の手法について特筆すべき部分を、詳しく説明してください。",
            "Q4": "本研究の成果や知見について特筆すべき部分を、詳しく説明してください。",
            "Q5": "本研究の限界について特筆すべき部分を、詳しく説明してください。",
            "Q6": "この論文中の記載で曖昧な部分を、詳しく説明してください。",
            "Q7": "引用されている論文の中で特筆すべきものを列挙し、本研究との関連性や違いを詳しく説明してください。",
            "Q8": "本研究で用いたデータセットを網羅的に列挙し、名前やURLなどがあればそれらも含めて詳しく説明してください。",
        }

    def to_questions_str(self, question: str) -> str:
        return self.questions.get(question, "No Question")

    def preprocess(self, inputs: dict[str, Any]) -> Messages:
        output_format = {inputs["question"]: f"(string) Answer to {inputs['question']} in markdown format"}
        system_prompt = (
            "与えられる文章を読み、以下の問いに答えて下さい。\n"
            f"{inputs['question']}: {self.to_questions_str(inputs['question'])}\n"
            "# 注意\n"
            "- 出力は日本語で行うこと。その他の言語は一切認めません。ただし、専門用語と思われる単語はそのままでも良い。\n"
            "- 可能な限り詳細に出力すること。だたし、最大300字程度とする。\n"
            "- 敬語は使用しないこと。「〜である」、「〜だ」のような形式にすること。\n"
            "- markdown形式は使用しないこと。特に、**bold** と __italics__ は使用しないこと。\n"
            "- 見やすいように改行を入れること。箇条書きは・を使って表現すること。"
            "以下の番号の質問に対して、以下の形式で回答してください。\n"
            "# 出力形式\n"
            f"{dict2json(output_format)}"
        )
        return [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": "please summarize the following text:\n" + inputs["text"],
            },
        ]

    def postprocess(self, response: Response) -> dict[str, str]:
        output_dict = json2dict(response.choices[0].message.content or "")
        new_output_dict = {}
        for question, answer in output_dict.items():
            new_output_dict[f"{question}: {self.to_questions_str(question)}"] = answer
        return new_output_dict


class CategoryClassifier(AbstractLLM[str, list[str]]):
    def preprocess(self, text: str) -> Messages:
        output_format = {"category": "(list) [Generative Model, Audio, LLM, Agent, Survey, CV, World Model, Reinforcement Learning]"}
        system_prompt = "あなたは論文分類の専門AIである。以下のテキストから適切なカテゴリを判定せよ。\n出力形式:\n" + dict2json(
            output_format
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "テキストからカテゴリを抽出せよ:\n" + text},
        ]

    def postprocess(self, response: Response) -> list[str]:
        output_dict = json2dict(response.choices[0].message.content or "")
        list_str = output_dict.get("category", "['No Category']")
        return [item.strip() for item in list_str.strip("[]").split(",")]


class BrieflySummarizer(AbstractLLM[str, str]):
    def preprocess(self, text: str) -> Messages:
        few_shot_list = [
            {"summary": "スマートフォンで音声を別の声に変換する高速モデル「LLVC」"},
            {"summary": "3.2兆トークンで学習された130億パラメータの大規模言語モデル「Skywork」"},
            {"summary": "OpenAIの文字起こしAI「Whisper」を軽量化したモデル「Distil-Whisper」"},
        ]
        system_prompt = "あなたは論文要約AIである。以下の制約に従い、論文内容を60文字以内・1文で要約せよ。\n例:\n" + "\n".join(
            dict2json(item) for item in few_shot_list
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "以下のテキストを要約せよ:\n" + text},
        ]

    def postprocess(self, response: Response) -> str:
        output_dict = json2dict(response.choices[0].message.content or "")
        return output_dict.get("summary", "No Summary")


class ChatAssistant(AbstractLLM[list[dict[str, Any]], str]):
    def preprocess(self, messages: list[dict[str, Any]]) -> Messages:
        system_prompt = (
            "あなたはAI研究の専門家である。論文の内容に関するやりとりを踏まえて、ユーザーの質問に回答しなさい。\n"
            "# 注意\n"
            "- 出力は日本語で行うこと。その他の言語は一切認めません。ただし、専門用語と思われる単語はそのままでも良い。\n"
            "- 可能な限り詳細に出力すること。だたし、最大300字程度とする。\n"
            "- markdown形式は使用しないこと。特に、**bold** と __italics__ は使用しないこと。\n"
            "- 見やすいように改行を入れること。箇条書きは・を使って表現すること。"
        )
        return [{"role": "system", "content": system_prompt}] + [
            {"role": message["role"], "content": message["content"]} for message in messages
        ]

    def postprocess(self, response: Response) -> str:
        return response.choices[0].message.content or "No Response"


# Service class ----------------------------
class LLMService(ILLMService):
    @property
    def client_settings(self) -> dict[str, str]:
        return {
            "api_key": os.environ["OPENAI_API_KEY"],
        }

    def generate_title(self, text: str) -> str:
        title_extractor = TitleExtractor(model="gpt-4o-mini", client_settings=self.client_settings, llm_settings={"max_tokens": 512})
        return title_extractor(text)

    def generate_summary(self, text: str) -> dict[str, str]:
        content_summarizer = ContentSummarizer(model="gpt-4o-mini", client_settings=self.client_settings, llm_settings={"max_tokens": 2048})
        return_results = {}
        questoins = ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8"]
        for question_idx in questoins:
            result = content_summarizer({"text": text, "question": question_idx})
            return_results.update(result)
        return return_results

    def generate_category(self, text: str) -> list[str]:
        category_classifier = CategoryClassifier(
            model="gpt-4o-mini", client_settings=self.client_settings, llm_settings={"max_tokens": 512}
        )
        return category_classifier(text)

    def generate_brief_digest(self, summary: dict[str, str]) -> str:
        briefly_summarizer = BrieflySummarizer(model="gpt-4o-mini", client_settings=self.client_settings, llm_settings={"max_tokens": 512})
        return briefly_summarizer(str(summary))

    def generate_chat_response(self, messages: list[dict[str, Any]]) -> str:
        chat_assistant = ChatAssistant(model="gpt-4o-mini", client_settings=self.client_settings, llm_settings={"max_tokens": 4096})
        return chat_assistant(messages)
