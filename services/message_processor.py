import logging

from config.settings import get_settings
from services.link_engine.engine import LinkEngine
from services.link_engine.models import AffiliateCredentials, PipelineContext

logger = logging.getLogger(__name__)


class MessageProcessor:
    def __init__(self, link_engine: LinkEngine, user_id: int | None = None, pipeline_id: int | None = None, telegram_account_id: int | None = None):
        self.link_engine = link_engine
        _s = get_settings()
        self._user_id = user_id if user_id is not None else _s.default_user_id
        self._pipeline_id = pipeline_id if pipeline_id is not None else _s.default_pipeline_id
        self._telegram_account_id = telegram_account_id if telegram_account_id is not None else _s.default_telegram_account_id

    async def process(self, text: str | None, affiliate_tag: str = "", amazon_domain: str = "amazon.in") -> tuple[str | None, list[str], int]:
        if not text:
            return text, [], 0

        context = PipelineContext(
            user_id=self._user_id,
            pipeline_id=self._pipeline_id,
            telegram_account_id=self._telegram_account_id,
            provider="amazon",
            country="IN",
            duplicate_policy="allow",
            publishing_mode="telethon",
            destination_channel_id=0,
            affiliate_credentials=AffiliateCredentials(
                provider_id="amazon",
                tag=affiliate_tag,
                domain=amazon_domain,
            ),
        )

        results = await self.link_engine.process_text(context, text, resolve=True)

        asins = []
        links_replaced = 0
        replacements = []

        for result in results:
            if result.affiliate_result and result.affiliate_result.changed:
                replacements.append((
                    result.extracted.original,
                    result.affiliate_result.affiliate_url,
                ))
                links_replaced += 1
                if result.affiliate_result.identity.product_id:
                    asins.append(result.affiliate_result.identity.product_id)
            elif result.affiliate_result and not result.affiliate_result.changed:
                replacements.append((
                    result.extracted.original,
                    result.affiliate_result.affiliate_url,
                ))
                links_replaced += 1

        modified = text
        for original, affiliate_url in replacements:
            modified = modified.replace(original, affiliate_url, 1)

        return modified, asins, links_replaced
