"""Provider registry for affiliate plugins."""

from __future__ import annotations

from services.link_engine.models import PipelineContext, ProviderMatch, UrlResolutionResult
from services.link_engine.providers.base import AffiliateProvider


class ProviderRegistry:
    """Registry that keeps the core engine closed for provider extension."""

    def __init__(self, providers: list[AffiliateProvider] | None = None):
        self._providers: dict[str, AffiliateProvider] = {}
        for provider in providers or []:
            self.register(provider)

    def register(self, provider: AffiliateProvider) -> None:
        """Register a provider plugin."""
        self._providers[provider.provider_id] = provider

    def get(self, provider_id: str) -> AffiliateProvider | None:
        """Return a provider by id."""
        return self._providers.get(provider_id)

    def all(self) -> list[AffiliateProvider]:
        """Return all registered providers."""
        return list(self._providers.values())

    def match(
        self, context: PipelineContext, resolved: UrlResolutionResult
    ) -> tuple[AffiliateProvider, ProviderMatch] | None:
        """Return the best provider match for a resolved URL."""
        best: tuple[AffiliateProvider, ProviderMatch] | None = None
        rank = {"none": 0, "low": 1, "medium": 2, "high": 3}

        for provider in self._providers.values():
            match = provider.match(context, resolved)
            if not match:
                continue
            if best is None or rank[match.confidence] > rank[best[1].confidence]:
                best = (provider, match)

        return best
