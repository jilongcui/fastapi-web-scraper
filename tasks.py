# tasks.py

import aiohttp
from bs4 import BeautifulSoup

async def fetch_html(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()

async def scrape(url):
    html_content = await fetch_html(url)
    soup = BeautifulSoup(html_content, 'lxml')
    # Example: Find all links on the page
    links = [a['href'] for a in soup.find_all('a', href=True)]
    print(f"Scraped links from {url}: {links}")
    return links

async def periodic_scraping_task():
    while True:
        await scrape('https://example.com')  # Replace with your target URL
        await asyncio.sleep(3600)  # 每小时运行一次任务

