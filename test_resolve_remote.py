import paramiko
import time

host = "ssh-achal.alwaysdata.net"
user = "achal"
password = "Aman@4899"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=password, timeout=10)

script = """
import asyncio
import aiohttp
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
import re

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0"

async def resolve_url(url: str) -> str:
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        headers = {"User-Agent": USER_AGENT}
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url, allow_redirects=True) as response:
                return str(response.url)
    except Exception as e:
        print("Failed to resolve:", e)
        return url

async def main():
    url = "https://amzn.to/4wXhe4U"
    final_url = await resolve_url(url)
    print(f"Final URL: {final_url}")

asyncio.run(main())
"""

client.exec_command(f"cat << 'INNER_EOF' > /home/achal/test_aiohttp.py\n{script}\nINNER_EOF")
stdin, stdout, stderr = client.exec_command("source /home/achal/bot/venv/bin/activate && python3 /home/achal/test_aiohttp.py")
print("STDOUT:", stdout.read().decode().strip())
print("STDERR:", stderr.read().decode().strip())
client.close()
