"""Affiliate credential provider abstraction."""

from __future__ import annotations

from typing import Protocol

from services.link_engine.models import AffiliateCredentials, PipelineContext


class AffiliateCredentialsProvider(Protocol):
    """
    Resolve provider credentials for a pipeline without coupling the engine to storage.

    Implementations may load from user settings, team settings, a database,
    environment variables, a secrets manager, or an external affiliate API.
    """

    async def get_credentials(
        self, context: PipelineContext, provider_id: str
    ) -> AffiliateCredentials | None:
        """Return credentials for the requested provider and context."""
        ...


class StaticAffiliateCredentialsProvider:
    """In-memory credentials provider for tests and simple wiring."""

    def __init__(self, credentials: dict[str, AffiliateCredentials]):
        self._credentials = credentials

    async def get_credentials(
        self, context: PipelineContext, provider_id: str
    ) -> AffiliateCredentials | None:
        if (
            context.affiliate_credentials
            and context.affiliate_credentials.provider_id == provider_id
        ):
            return context.affiliate_credentials
        return self._credentials.get(provider_id)
