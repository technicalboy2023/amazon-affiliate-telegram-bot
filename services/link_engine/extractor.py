"""Provider-agnostic URL extraction."""

from __future__ import annotations

import re

from services.link_engine.models import ExtractedUrl, UrlSource

URL_RE = re.compile(
    r"(?P<url>(?:https?://|www\.)[^\s<>()]+|(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}/[^\s<>()]+)"
)


class UrlExtractor:
    """Extract URLs without provider-specific assumptions."""

    def extract(self, text: str | None, source: UrlSource = "text") -> list[ExtractedUrl]:
        if not text:
            return []

        urls: list[ExtractedUrl] = []
        for match in URL_RE.finditer(text):
            original = match.group("url").rstrip(".,;!?)]")
            normalized = self._normalize(original)
            urls.append(
                ExtractedUrl(
                    original=original,
                    normalized=normalized,
                    start=match.start("url"),
                    end=match.start("url") + len(original),
                    source=source,
                )
            )
        return urls

    @staticmethod
    def _normalize(url: str) -> str:
        if url.startswith("http://") or url.startswith("https://"):
            return url
        return f"https://{url}"
