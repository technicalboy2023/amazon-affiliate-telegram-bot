"""Provider-agnostic data models for affiliate link processing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

UrlSource = Literal["text", "caption", "entity"]
ResolutionStatus = Literal["not_required", "resolved", "failed"]
IdentityConfidence = Literal["high", "medium", "low", "none"]
DuplicatePolicy = Literal["skip", "allow"]
PublishingMode = Literal["bot_api", "telethon", "auto"]


@dataclass(frozen=True)
class ExtractedUrl:
    """A URL found in message text, caption, or Telegram entities."""

    original: str
    normalized: str
    start: int | None = None
    end: int | None = None
    source: UrlSource = "text"
    entity_index: int | None = None


@dataclass(frozen=True)
class UrlResolutionResult:
    """Result of resolving redirects for an extracted URL."""

    extracted: ExtractedUrl
    final_url: str
    status: ResolutionStatus
    redirect_chain: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass(frozen=True)
class ProviderMatch:
    """Provider recognition result for a resolved URL."""

    provider_id: str
    confidence: IdentityConfidence
    reason: str | None = None


@dataclass(frozen=True)
class ProductIdentity:
    """Provider-specific product identity in provider-agnostic form."""

    provider_id: str
    product_id: str | None
    product_id_kind: str | None
    confidence: IdentityConfidence
    canonical_url: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class AffiliateCredentials:
    """Provider-specific affiliate credentials supplied by a user/pipeline."""

    provider_id: str
    tag: str
    country_code: str | None = None
    domain: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderCapabilities:
    """Feature declaration for a provider plugin."""

    supports_short_links: bool = False
    supports_affiliate_tag_replacement: bool = True
    supports_product_lookup: bool = False
    supports_product_identity: bool = True
    supports_media_metadata: bool = False


@dataclass(frozen=True)
class PipelineContext:
    """Strongly typed context for one pipeline processing request."""

    user_id: int
    pipeline_id: int
    telegram_account_id: int
    provider: str | None
    country: str | None
    duplicate_policy: DuplicatePolicy
    publishing_mode: PublishingMode
    destination_channel_id: int
    language: str | None = None
    affiliate_credentials: AffiliateCredentials | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class AffiliateLinkResult:
    """Generated affiliate URL for a matched provider URL."""

    provider_id: str
    original_url: str
    final_url: str
    affiliate_url: str
    identity: ProductIdentity
    changed: bool
    removed_params: list[str] = field(default_factory=list)
    preserved_params: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass(frozen=True)
class LinkProcessingResult:
    """Provider-agnostic result for one input URL."""

    extracted: ExtractedUrl
    resolution: UrlResolutionResult
    provider_match: ProviderMatch | None
    affiliate_result: AffiliateLinkResult | None
    skipped_reason: str | None = None
