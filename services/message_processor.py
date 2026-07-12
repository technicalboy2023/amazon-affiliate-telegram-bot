import logging

from services.link_engine.engine import LinkEngine
from services.link_engine.models import AffiliateCredentials, PipelineContext

logger = logging.getLogger(__name__)


class MessageProcessor:
    def __init__(self, link_engine: LinkEngine):
        self.link_engine = link_engine

    async def process(self, text: str | None, affiliate_tag: str = "", amazon_domain: str = "amazon.in") -> tuple[str | None, list[str], int]:
        if not text:
            return text, [], 0

        context = PipelineContext(
            user_id=1,
            pipeline_id=1,
            telegram_account_id=1,
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
