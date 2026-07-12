"""Provider-based affiliate link engine."""

from services.link_engine.credentials import (
    AffiliateCredentialsProvider,
    StaticAffiliateCredentialsProvider,
)
from services.link_engine.engine import LinkEngine
from services.link_engine.models import (
    AffiliateCredentials,
    AffiliateLinkResult,
    ExtractedUrl,
    LinkProcessingResult,
    PipelineContext,
    ProductIdentity,
    ProviderCapabilities,
    ProviderMatch,
    UrlResolutionResult,
)
from services.link_engine.providers.base import AffiliateProvider
from services.link_engine.registry import ProviderRegistry

__all__ = [
    "AffiliateCredentials",
    "AffiliateCredentialsProvider",
    "AffiliateLinkResult",
    "AffiliateProvider",
    "ExtractedUrl",
    "LinkEngine",
    "LinkProcessingResult",
    "PipelineContext",
    "ProductIdentity",
    "ProviderCapabilities",
    "ProviderMatch",
    "ProviderRegistry",
    "StaticAffiliateCredentialsProvider",
    "UrlResolutionResult",
]
