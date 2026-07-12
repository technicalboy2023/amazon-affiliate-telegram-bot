import pytest

from services.link_engine.credentials import StaticAffiliateCredentialsProvider
from services.link_engine.engine import LinkEngine
from services.link_engine.models import (
    AffiliateCredentials,
    AffiliateLinkResult,
    ExtractedUrl,
    PipelineContext,
    ProductIdentity,
    ProviderCapabilities,
    ProviderMatch,
    UrlResolutionResult,
)
from services.link_engine.providers.amazon import AmazonProvider
from services.link_engine.registry import ProviderRegistry


def resolved(url: str) -> UrlResolutionResult:
    extracted = ExtractedUrl(original=url, normalized=url)
    return UrlResolutionResult(extracted=extracted, final_url=url, status="not_required")


def context(
    provider: str | None = None, credentials: AffiliateCredentials | None = None
) -> PipelineContext:
    return PipelineContext(
        user_id=1,
        pipeline_id=10,
        telegram_account_id=20,
        provider=provider,
        country="IN",
        affiliate_credentials=credentials,
        duplicate_policy="skip",
        publishing_mode="auto",
        destination_channel_id=30,
        language="en",
    )


def test_amazon_provider_replaces_existing_affiliate_tag_and_preserves_params() -> None:
    provider = AmazonProvider()
    url = resolved("https://www.amazon.in/dp/B0FDWHFS68?th=1&tag=old-21")

    identity = provider.extract_identity(context("amazon"), url)
    result = provider.generate_affiliate_link(
        context("amazon"),
        url,
        identity,
        AffiliateCredentials(provider_id="amazon", tag="new-21"),
    )

    assert identity.product_id == "B0FDWHFS68"
    assert result.affiliate_url == "https://www.amazon.in/dp/B0FDWHFS68?th=1&tag=new-21"
    assert result.removed_params == ["tag"]
    assert result.preserved_params == ["th"]


def test_amazon_provider_supports_gp_product_urls() -> None:
    provider = AmazonProvider()
    url = resolved("https://amazon.com/gp/product/B0ABCDEF12?psc=1")

    identity = provider.extract_identity(context("amazon"), url)

    assert identity.product_id == "B0ABCDEF12"
    assert identity.product_id_kind == "asin"
    assert identity.confidence == "high"


@pytest.mark.asyncio
async def test_engine_depends_on_provider_interface_not_amazon_specific_code() -> None:
    class FakeProvider:
        provider_id = "fake_store"
        display_name = "Fake Store"
        capabilities = ProviderCapabilities(
            supports_affiliate_tag_replacement=True,
            supports_product_identity=True,
        )

        def match(
            self, context: PipelineContext, resolved: UrlResolutionResult
        ) -> ProviderMatch | None:
            if "fake.example" in resolved.final_url:
                return ProviderMatch(self.provider_id, "high", "fake domain")
            return None

        def extract_identity(
            self, context: PipelineContext, resolved: UrlResolutionResult
        ) -> ProductIdentity:
            return ProductIdentity(
                provider_id=self.provider_id,
                product_id="SKU123",
                product_id_kind="sku",
                confidence="high",
                canonical_url=resolved.final_url,
            )

        def generate_affiliate_link(
            self,
            context: PipelineContext,
            resolved: UrlResolutionResult,
            identity: ProductIdentity,
            credentials: AffiliateCredentials,
        ) -> AffiliateLinkResult:
            return AffiliateLinkResult(
                provider_id=self.provider_id,
                original_url=resolved.extracted.original,
                final_url=resolved.final_url,
                affiliate_url=f"{resolved.final_url}?ref={credentials.tag}",
                identity=identity,
                changed=True,
            )

    registry = ProviderRegistry([FakeProvider()])
    engine = LinkEngine(
        registry=registry,
        credentials_provider=StaticAffiliateCredentialsProvider(
            {"fake_store": AffiliateCredentials(provider_id="fake_store", tag="user-ref")}
        ),
    )
    result = await engine.process_resolved_url(
        context("fake_store"),
        resolved("https://fake.example/products/sku123"),
    )

    assert result.provider_match is not None
    assert result.provider_match.provider_id == "fake_store"
    assert result.affiliate_result is not None
    assert (
        result.affiliate_result.affiliate_url == "https://fake.example/products/sku123?ref=user-ref"
    )


@pytest.mark.asyncio
async def test_engine_skips_unknown_provider_without_error() -> None:
    engine = LinkEngine(registry=ProviderRegistry([AmazonProvider()]))
    result = await engine.process_resolved_url(
        context(),
        resolved("https://example.com/product/123"),
    )

    assert result.provider_match is None
    assert result.affiliate_result is None
    assert result.skipped_reason == "no_provider_match"


@pytest.mark.asyncio
async def test_engine_reports_missing_provider_credentials() -> None:
    engine = LinkEngine(registry=ProviderRegistry([AmazonProvider()]))
    result = await engine.process_resolved_url(
        context("amazon"),
        resolved("https://amazon.in/dp/B0FDWHFS68"),
    )

    assert result.provider_match is not None
    assert result.affiliate_result is None
    assert result.skipped_reason == "missing_provider_credentials"


@pytest.mark.asyncio
async def test_engine_uses_context_affiliate_credentials_without_global_state() -> None:
    engine = LinkEngine(registry=ProviderRegistry([AmazonProvider()]))
    result = await engine.process_resolved_url(
        context("amazon", AffiliateCredentials(provider_id="amazon", tag="ctx-21")),
        resolved("https://amazon.in/dp/B0FDWHFS68?tag=old-21"),
    )

    assert result.affiliate_result is not None
    assert result.affiliate_result.affiliate_url == "https://amazon.in/dp/B0FDWHFS68?tag=ctx-21"


def test_provider_capabilities_are_declared() -> None:
    provider = AmazonProvider()

    assert provider.capabilities.supports_short_links is True
    assert provider.capabilities.supports_affiliate_tag_replacement is True
    assert provider.capabilities.supports_product_identity is True
