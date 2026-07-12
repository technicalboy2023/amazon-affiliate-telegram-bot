"""Provider interface for affiliate link generation plugins."""

from __future__ import annotations

from typing import Protocol

from services.link_engine.models import (
    AffiliateCredentials,
    AffiliateLinkResult,
    PipelineContext,
    ProductIdentity,
    ProviderCapabilities,
    ProviderMatch,
    UrlResolutionResult,
)


class AffiliateProvider(Protocol):
    """
    Provider plugin contract.

    Core pipeline code depends only on this protocol. New providers such as
    Flipkart, Myntra, Ajio, Cuelinks, EarnKaro, or Admitad should implement this
    interface and register with ProviderRegistry without changing the engine.
    """

    provider_id: str
    display_name: str
    capabilities: ProviderCapabilities

    def match(
        self, context: PipelineContext, resolved: UrlResolutionResult
    ) -> ProviderMatch | None:
        """Return provider match information if this provider owns the URL."""
        ...

    def extract_identity(
        self, context: PipelineContext, resolved: UrlResolutionResult
    ) -> ProductIdentity:
        """Extract provider-specific product identity from a URL."""
        ...

    def generate_affiliate_link(
        self,
        context: PipelineContext,
        resolved: UrlResolutionResult,
        identity: ProductIdentity,
        credentials: AffiliateCredentials,
    ) -> AffiliateLinkResult:
        """Generate a provider-specific affiliate URL."""
        ...
