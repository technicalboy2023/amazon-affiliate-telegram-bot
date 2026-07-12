"""Provider-agnostic link engine facade."""

from __future__ import annotations

from services.link_engine.credentials import AffiliateCredentialsProvider
from services.link_engine.extractor import UrlExtractor
from services.link_engine.models import (
    ExtractedUrl,
    LinkProcessingResult,
    PipelineContext,
    ProductIdentity,
    UrlResolutionResult,
)
from services.link_engine.registry import ProviderRegistry
from services.link_engine.resolver import UrlResolver


class LinkEngine:
    """Provider-agnostic affiliate link engine."""

    def __init__(
        self,
        registry: ProviderRegistry | None = None,
        extractor: UrlExtractor | None = None,
        resolver: UrlResolver | None = None,
        credentials_provider: AffiliateCredentialsProvider | None = None,
    ):
        self.registry = registry or ProviderRegistry()
        self.extractor = extractor or UrlExtractor()
        self.resolver = resolver or UrlResolver()
        self.credentials_provider = credentials_provider

    def extract_links(self, text: str | None) -> list[ExtractedUrl]:
        """Extract URLs from text without provider-specific assumptions."""
        return self.extractor.extract(text)

    async def process_text(
        self,
        context: PipelineContext,
        text: str | None,
        resolve: bool = True,
    ) -> list[LinkProcessingResult]:
        """Extract, resolve, match providers, and generate affiliate URLs."""
        extracted_urls = self.extract_links(text)
        if resolve:
            resolved_urls = await self.resolver.resolve_many(extracted_urls)
        else:
            resolved_urls = [
                UrlResolutionResult(url, url.normalized, "not_required") for url in extracted_urls
            ]
        return [await self.process_resolved_url(context, url) for url in resolved_urls]

    async def process_resolved_url(
        self,
        context: PipelineContext,
        resolved: UrlResolutionResult,
    ) -> LinkProcessingResult:
        """Process one already-resolved URL through the provider registry."""
        matched = self.registry.match(context, resolved)
        if matched is None:
            return LinkProcessingResult(
                extracted=resolved.extracted,
                resolution=resolved,
                provider_match=None,
                affiliate_result=None,
                skipped_reason="no_provider_match",
            )

        provider, provider_match = matched
        if not provider.capabilities.supports_affiliate_tag_replacement:
            return LinkProcessingResult(
                extracted=resolved.extracted,
                resolution=resolved,
                provider_match=provider_match,
                affiliate_result=None,
                skipped_reason="provider_does_not_support_affiliate_generation",
            )

        credentials = await self._get_credentials(context, provider.provider_id)
        if credentials is None:
            return LinkProcessingResult(
                extracted=resolved.extracted,
                resolution=resolved,
                provider_match=provider_match,
                affiliate_result=None,
                skipped_reason="missing_provider_credentials",
            )

        if provider.capabilities.supports_product_identity:
            identity = provider.extract_identity(context, resolved)
        else:
            identity = ProductIdentity(
                provider_id=provider.provider_id,
                product_id=None,
                product_id_kind=None,
                confidence="none",
                canonical_url=resolved.final_url,
            )
        affiliate_result = provider.generate_affiliate_link(
            context, resolved, identity, credentials
        )
        return LinkProcessingResult(
            extracted=resolved.extracted,
            resolution=resolved,
            provider_match=provider_match,
            affiliate_result=affiliate_result,
        )

    async def _get_credentials(self, context: PipelineContext, provider_id: str):
        if (
            context.affiliate_credentials
            and context.affiliate_credentials.provider_id == provider_id
        ):
            return context.affiliate_credentials
        if self.credentials_provider is None:
            return None
        return await self.credentials_provider.get_credentials(context, provider_id)
