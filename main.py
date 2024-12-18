from fastapi import FastAPI
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from tasks import periodic_scraping_task  # 导入你定义的爬虫任务

app = FastAPI()

@app.on_event("startup")
async def start_scraping_task():
    while True:
	# 启动爬虫定时任务，确保它们不会阻塞主事件循环
        print("Starting scraping task...")
    	asyncio.create_task(periodic_scraping_task())

@app.get("/")
async def read_root():
    return {"status": "Running web scraper service"}
