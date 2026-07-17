import re
import aiohttp
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from utils.logger import get_logger

logger = get_logger(__name__)

AMAZON_DOMAINS = {
    "amazon.in", "www.amazon.in",
    "amazon.com", "www.amazon.com",
    "amazon.ae", "www.amazon.ae",
    "amazon.co.uk", "www.amazon.co.uk",
    "amazon.ca", "www.amazon.ca",
    "amazon.de", "www.amazon.de",
    "amazon.fr", "www.amazon.fr",
    "amazon.it", "www.amazon.it",
    "amazon.es", "www.amazon.es",
    "amazon.com.au", "www.amazon.com.au"
}
SHORT_DOMAINS = {"amzn.to", "www.amzn.to", "amzn.in", "www.amzn.in"}

ASIN_RE = re.compile(r"(?<![A-Z0-9])([A-Z0-9]{10})(?![A-Z0-9])", re.IGNORECASE)
URL_RE = re.compile(r"https?://[^\s<>\"']+")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0"


async def resolve_url(url: str) -> str:
    """Resolve redirect for shortlinks."""
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        headers = {"User-Agent": USER_AGENT}
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url, allow_redirects=True) as response:
                return str(response.url)
    except Exception as e:
        logger.warning("Failed to resolve %s: %s", url, e)
        return url


def extract_asin(url: str) -> str | None:
    parsed = urlparse(url)
    path = parsed.path
    query = parsed.query
    
    path_patterns = [
        r"/dp/([A-Z0-9]{10})",
        r"/gp/product/([A-Z0-9]{10})",
        r"/exec/obidos/ASIN/([A-Z0-9]{10})",
    ]
    for pattern in path_patterns:
        match = re.search(pattern, path, re.IGNORECASE)
        if match:
            return match.group(1).upper()

    for key, value in parse_qsl(query, keep_blank_values=True):
        if key.lower() == "asin" and ASIN_RE.fullmatch(value):
            return value.upper()
            
    return None

def build_affiliate_url(asin: str, tag: str, domain: str = "amazon.in") -> str:
    return f"https://www.{domain}/dp/{asin}?tag={tag}"

async def process_amazon_links(text: str, affiliate_tag: str, default_domain: str = "amazon.in") -> tuple[str, list[str]]:
    """
    Find all amazon links, resolve them, extract ASINs, and replace them with affiliate links.
    Returns (new_text, list_of_asins).
    """
    if not text or not affiliate_tag:
        return text, []
        
    urls = URL_RE.findall(text)
    if not urls:
        return text, []

    new_text = text
    found_asins = []

    for url in urls:
        try:
            parsed = urlparse(url)
            host = parsed.netloc.lower()
            
            final_url = url
            is_amazon = False
            
            if host in SHORT_DOMAINS:
                final_url = await resolve_url(url)
                is_amazon = True
            elif host in AMAZON_DOMAINS:
                is_amazon = True
                
            if is_amazon:
                asin = extract_asin(final_url)
                if asin:
                    found_asins.append(asin)
                    new_url = build_affiliate_url(asin, affiliate_tag, default_domain)
                    new_text = new_text.replace(url, new_url)
        except Exception as e:
            logger.error("Error processing link %s: %s", url, e)
            
    return new_text, found_asins
