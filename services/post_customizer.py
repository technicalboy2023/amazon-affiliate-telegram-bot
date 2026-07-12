import json
import logging

logger = logging.getLogger(__name__)


class PostCustomizer:
    def __init__(self, settings_service):
        self.settings_service = settings_service

    async def get_replacements(self) -> list[dict[str, str]]:
        raw = await self.settings_service.get("replacements", "[]")
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []

    async def set_replacements(self, replacements: list[dict[str, str]]) -> None:
        await self.settings_service.set("replacements", json.dumps(replacements))

    async def get_blocked_words(self) -> list[str]:
        raw = await self.settings_service.get("blocked_words", "[]")
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []

    async def set_blocked_words(self, words: list[str]) -> None:
        await self.settings_service.set("blocked_words", json.dumps(words))

    async def get_header(self) -> str:
        return await self.settings_service.get("header_text", "")

    async def set_header(self, text: str) -> None:
        await self.settings_service.set("header_text", text)

    async def clear_header(self) -> None:
        await self.settings_service.set("header_text", "")

    async def get_footer(self) -> str:
        return await self.settings_service.get("footer_text", "")

    async def set_footer(self, text: str) -> None:
        await self.settings_service.set("footer_text", text)

    async def clear_footer(self) -> None:
        await self.settings_service.set("footer_text", "")

    async def get_delay(self) -> int:
        raw = await self.settings_service.get("forward_delay", "0")
        try:
            return max(0, int(raw))
        except (ValueError, TypeError):
            return 0

    async def set_delay(self, seconds: int) -> None:
        await self.settings_service.set("forward_delay", str(max(0, seconds)))

    async def is_paused(self) -> bool:
        return await self.settings_service.get("is_paused", "false") == "true"

    async def set_paused(self, paused: bool) -> None:
        await self.settings_service.set("is_paused", "true" if paused else "false")

    async def is_blocked(self, text: str) -> bool:
        if not text:
            return False
        words = await self.get_blocked_words()
        if not words:
            return False
        lower_text = text.lower()
        return any(w.lower() in lower_text for w in words if w)

    async def apply_replacements(self, text: str) -> str:
        if not text:
            return text
        replacements = await self.get_replacements()
        if not replacements:
            return text
        result = text
        for item in replacements:
            old = item.get("old", "")
            new = item.get("new", "")
            if old:
                result = result.replace(old, new)
        return result

    async def apply_header_footer(self, text: str) -> str:
        header = await self.get_header()
        footer = await self.get_footer()
        parts = []
        if header:
            parts.append(header)
        parts.append(text)
        if footer:
            parts.append(footer)
        return "\n".join(parts)

    async def customize(self, text: str) -> str | None:
        if await self.is_blocked(text):
            logger.info("Message blocked by word filter")
            return None
        text = await self.apply_replacements(text)
        text = await self.apply_header_footer(text)
        return text
