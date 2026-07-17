import asyncio
from userbot.link_engine import process_amazon_links

async def main():
    text = "KUHL Prima A3-DUO 1200mm BEE 5-Star BLDC Ceiling Fan @2999\nhttps://amzn.to/4wXhe4U"
    new_text, asins = await process_amazon_links(text, "ankushdeals0a-21", "amazon.in")
    print("New text:")
    print(new_text)
    print("ASINs:", asins)

asyncio.run(main())
