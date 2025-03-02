from io import BytesIO

import arxiv  # type: ignore[import-untyped]
from markdownify import markdownify  # type: ignore[import-untyped]
from pypdf import PdfReader
import requests  # type: ignore[import-untyped]

from src.domain.services import IContentDownloader


class DownloadFailureError(Exception):
    pass


class PDFProcessor:
    def __init__(self) -> None:
        self.text = ""

    def to_file(self, binary_content: bytes) -> BytesIO:
        return BytesIO(binary_content)

    def read_text(self, binary_content: bytes) -> str:
        reader = PdfReader(self.to_file(binary_content))
        self.text = ""
        for page in reader.pages:
            self.text += page.extract_text() or ""
        return self.text


class FileDownloader(IContentDownloader):
    def __init__(self) -> None:
        self.pdf_processor = PDFProcessor()

    def download_content(self, url: str) -> str:
        url_lower = url.lower()
        if "arxiv" in url_lower:
            arxiv_id = url.split("/")[-1].removesuffix(".pdf")
            binary_content = self._download_pdf_from_arxiv(arxiv_id)
            return self.pdf_processor.read_text(binary_content)
        if "pdf" in url_lower:
            binary_content = self._download_pdf(url)
            return self.pdf_processor.read_text(binary_content)
        return self._download_html_as_markdown(url)

    def _download_pdf_from_arxiv(self, arxiv_id: str) -> bytes:
        client = arxiv.Client()
        search = arxiv.Search(id_list=[arxiv_id], max_results=1)
        paper = next(client.results(search))
        try:
            return requests.get(paper.pdf_url, timeout=10).content
        except Exception as e:
            raise DownloadFailureError from e

    def _download_pdf(self, url: str) -> bytes:
        try:
            return requests.get(url, timeout=10).content
        except Exception as e:
            raise DownloadFailureError from e

    def _download_html_as_markdown(self, url: str) -> str:
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            html_text = requests.get(url, headers=headers, timeout=10).text
            return markdownify(html_text)
        except Exception as e:
            raise DownloadFailureError from e
