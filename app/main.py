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
        
        # 设置停止信号并取消任务
        shutdown_event.set()
        
        # 取消任务并等待完成
        if not scraping_task.done():
            scraping_task.cancel()
            try:
                await asyncio.wait_for(scraping_task, timeout=10.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                logger.info("Scraping task cancelled or timed out during shutdown")
            except Exception as e:
                logger.error(f"Error during task shutdown: {e}")

async def start_scraping_task():
    try:
        while not shutdown_event.is_set():
            logger.info("Starting scraping task...")

            # 假设此函数是你实际执行的抓取任务
            await periodic_scraping_task()  
            
            # 检查是否应该继续运行
            if shutdown_event.is_set():
                break
                
            # 使用可中断的睡眠
            try:
                await asyncio.wait_for(asyncio.sleep(5), timeout=1)
            except asyncio.TimeoutError:
                continue  # 继续检查shutdown_event
                
    except asyncio.CancelledError:
        logger.info("Scraping task was cancelled")
    except Exception as e:
        logger.error(f"Error in scraping task: {e}")
    finally:
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
def signal_handler():
    """信号处理函数"""
    logger.info("Received shutdown signal, setting shutdown event...")
    shutdown_event.set()

# 注册信号处理器
signal.signal(signal.SIGINT, lambda s, f: signal_handler())
signal.signal(signal.SIGTERM, lambda s, f: signal_handler())

if __name__ == "__main__":
    print("Running app...")
    # 移除 reload=True 以避免信号处理冲突
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
