from fastapi import FastAPI
import asyncio
import uvicorn
import signal
from contextlib import asynccontextmanager
# from app.tasks_interview import periodic_scraping_task  # 导入省考爬虫任务
from app.tasks_interview_shiyebian import periodic_scraping_task  # 导入事业单位面试爬虫任务
# from app.tasks_discussion import periodic_scraping_task  # 导入申论爬虫任务
# from app.tasks import periodic_scraping_task  # 导入国考爬虫任务
# from app.tasks_discussion import process_discussion_types # 导入申论类型检查
from app.logs import get_logger


logger = get_logger(__name__)

# 定义全局变量以控制停止信号（如果需要）
shutdown_event = asyncio.Event()

# Define a global event for managing shutdown signals.

@asynccontextmanager
async def lifespan(app: FastAPI):
    

    # 这部分将在应用启动时运行（等同于 startup）
    # logger.info("Starting up...")
    print("Starting up...")
    
    # 启动爬虫定时任务在后台协程中运行
    scraping_task = asyncio.create_task(start_scraping_task())

    # 启动爬虫定时任务在后台协程中运行
    # scraping_task = asyncio.create_task(start_process_types_task())

    try:
        yield
    finally:
        # 这部分将在应用关闭时运行（等同于 shutdown）
        logger.info("Shutting down...")
        
        # 设置停止信号并等待异步任务完成清理工作
        shutdown_event.set()
        await scraping_task

async def start_scraping_task():
    while not shutdown_event.is_set():
        logger.info("Starting scraping task...")

        # 假设此函数是你实际执行的抓取任务
        await periodic_scraping_task()  
        shutdown_event.set()
        # 每分钟运行一次任务
        await asyncio.sleep(5)
    # 在退出主循环之前进行一些清理
    logger.info("Scraping task is shutting down.")

# async def start_process_types_task():
#     while not shutdown_event.is_set():
#         logger.info("Starting scraping task...")

#         # 假设此函数是你实际执行的抓取任务
#         await process_discussion_types()  
#         shutdown_event.set()
#         # 每分钟运行一次任务
#         await asyncio.sleep(1)
#     # 在退出主循环之前进行一些清理
#     logger.info("Scraping task is shutting down.")

# 将 lifespan 函数连接到 FastAPI 应用上
app = FastAPI(lifespan=lifespan)

@app.get("/")
async def read_root():
    return {"status": "Running web scraper service"}

# 注册信号以处理程序终止请求
# loop = asyncio.get_event_loop()
# loop.add_signal_handler(signal.SIGINT, shutdown_event.set)
# # 可选：也可以注册其他信号，如SIGTERM
# loop.add_signal_handler(signal.SIGTERM, shutdown_event.set)

if __name__ == "__main__":
    print("Running app...")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
