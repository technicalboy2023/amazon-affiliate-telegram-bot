"""Provider-agnostic URL redirect resolver."""

from __future__ import annotations

import aiohttp

from services.link_engine.models import ExtractedUrl, UrlResolutionResult

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0"


class UrlResolver:
    """Resolve redirects for extracted URLs."""

    def __init__(self, timeout_seconds: int = 10):
        self.timeout_seconds = timeout_seconds

    async def resolve(self, extracted: ExtractedUrl) -> UrlResolutionResult:
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
            headers = {"User-Agent": USER_AGENT}
            async with (
                aiohttp.ClientSession(timeout=timeout, headers=headers) as session,
                session.get(extracted.normalized, allow_redirects=True) as response,
            ):
                final_url = str(response.url)
                redirect_chain = [str(item.url) for item in response.history]
                if final_url != extracted.normalized or redirect_chain:
                    return UrlResolutionResult(
                        extracted=extracted,
                        final_url=final_url,
                        status="resolved",
                        redirect_chain=redirect_chain,
                    )
        except Exception as exc:
            return UrlResolutionResult(
                extracted=extracted,
                final_url=extracted.normalized,
                status="failed",
                error=str(exc),
            )

        return UrlResolutionResult(
            extracted=extracted,
            final_url=extracted.normalized,
            status="not_required",
        )

    async def resolve_many(self, urls: list[ExtractedUrl]) -> list[UrlResolutionResult]:
        return [await self.resolve(url) for url in urls]
