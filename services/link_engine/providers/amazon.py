"""Amazon affiliate provider plugin."""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from services.link_engine.models import (
    AffiliateCredentials,
    AffiliateLinkResult,
    PipelineContext,
    ProductIdentity,
    ProviderCapabilities,
    ProviderMatch,
    UrlResolutionResult,
)

ASIN_RE = re.compile(r"(?<![A-Z0-9])([A-Z0-9]{10})(?![A-Z0-9])", re.IGNORECASE)


class AmazonProvider:
    """Amazon provider supporting Amazon marketplace and short-link domains."""

    provider_id = "amazon"
    display_name = "Amazon"
    capabilities = ProviderCapabilities(
        supports_short_links=True,
        supports_affiliate_tag_replacement=True,
        supports_product_lookup=False,
        supports_product_identity=True,
        supports_media_metadata=False,
    )

    amazon_domains = {
        "amazon.in",
        "www.amazon.in",
        "amazon.com",
        "www.amazon.com",
        "amazon.ae",
        "www.amazon.ae",
        "amazon.co.uk",
        "www.amazon.co.uk",
        "amazon.ca",
        "www.amazon.ca",
        "amazon.de",
        "www.amazon.de",
        "amazon.fr",
        "www.amazon.fr",
        "amazon.it",
        "www.amazon.it",
        "amazon.es",
        "www.amazon.es",
        "amazon.com.au",
        "www.amazon.com.au",
    }
    short_domains = {"amzn.to", "www.amzn.to", "amzn.in", "www.amzn.in"}

    def match(
        self, context: PipelineContext, resolved: UrlResolutionResult
    ) -> ProviderMatch | None:
        if context.provider and context.provider != self.provider_id:
            return None
        parsed = urlparse(resolved.final_url)
        host = parsed.netloc.lower()
        if host in self.amazon_domains:
            return ProviderMatch(self.provider_id, "high", "amazon domain")
        if host in self.short_domains:
            return ProviderMatch(self.provider_id, "medium", "amazon short domain")
        return None

    def extract_identity(
        self, context: PipelineContext, resolved: UrlResolutionResult
    ) -> ProductIdentity:
        parsed = urlparse(resolved.final_url)
        asin = self._extract_asin(parsed.path, parsed.query)
        if asin:
            canonical_url = self._canonical_product_url(parsed, asin)
            return ProductIdentity(
                provider_id=self.provider_id,
                product_id=asin.upper(),
                product_id_kind="asin",
                confidence="high",
                canonical_url=canonical_url,
            )
        return ProductIdentity(
            provider_id=self.provider_id,
            product_id=None,
            product_id_kind=None,
            confidence="none",
            canonical_url=resolved.final_url,
        )

    def generate_affiliate_link(
        self,
        context: PipelineContext,
        resolved: UrlResolutionResult,
        identity: ProductIdentity,
        credentials: AffiliateCredentials,
    ) -> AffiliateLinkResult:
        parsed = urlparse(resolved.final_url)
        query_pairs = parse_qsl(parsed.query, keep_blank_values=True)

        preserved: list[tuple[str, str]] = []
        removed_params: list[str] = []
        for key, value in query_pairs:
            if key.lower() == "tag":
                removed_params.append(key)
                continue
            preserved.append((key, value))

        preserved.append(("tag", credentials.tag))
        new_query = urlencode(preserved, doseq=True)
        affiliate_url = urlunparse(parsed._replace(query=new_query))

        return AffiliateLinkResult(
            provider_id=self.provider_id,
            original_url=resolved.extracted.original,
            final_url=resolved.final_url,
            affiliate_url=affiliate_url,
            identity=identity,
            changed=affiliate_url != resolved.extracted.original,
            removed_params=removed_params,
            preserved_params=[key for key, _ in preserved if key.lower() != "tag"],
        )

    def _extract_asin(self, path: str, query: str) -> str | None:
        path_patterns = [
            r"/dp/([A-Z0-9]{10})",
            r"/gp/product/([A-Z0-9]{10})",
            r"/exec/obidos/ASIN/([A-Z0-9]{10})",
        ]
        for pattern in path_patterns:
            match = re.search(pattern, path, re.IGNORECASE)
            if match:
                return match.group(1)

        for key, value in parse_qsl(query, keep_blank_values=True):
            if key.lower() == "asin" and ASIN_RE.fullmatch(value):
                return value
        return None

    @staticmethod
    def _canonical_product_url(parsed, asin: str) -> str:
        return urlunparse((parsed.scheme, parsed.netloc, f"/dp/{asin.upper()}", "", "", ""))
