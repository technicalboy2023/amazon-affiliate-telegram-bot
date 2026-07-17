import asyncio
import aiohttp
from userbot.link_engine import resolve_url, extract_asin

async def main():
    url = "https://amzn.to/4wXhe4U"
    final_url = await resolve_url(url)
    print(f"Final URL: {final_url}")
    asin = extract_asin(final_url)
    print(f"ASIN: {asin}")

asyncio.run(main())
