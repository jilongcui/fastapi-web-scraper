from fastapi import FastAPI
import asyncio
import uvicorn
import signal
from contextlib import asynccontextmanager
# from app.tasks_interview import periodic_scraping_task  # 导入省考爬虫任务
from app.tasks_interview_shiyebian import periodic_scraping_interview_task  # 导入事业单位面试爬虫任务
# from app.tasks_discussion import periodic_scraping_task  # 导入申论爬虫任务
# from app.tasks import periodic_scraping_task  # 导入国考爬虫任务
# from app.tasks_discussion import process_discussion_types # 导入申论类型检查
from app.tasks_question_shiyebian import periodic_scraping_question_task # 导入申论类型检查
from app.logs import get_logger
from app.database import close_database_connection


logger = get_logger(__name__)

# 定义全局变量以控制停止信号（如果需要）
shutdown_event = asyncio.Event()

# Define a global event for managing shutdown signals.

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 生命周期管理"""
    logger.info("FastAPI application is starting up...")
    
    # 获取当前事件循环
    loop = asyncio.get_running_loop()
    
    # 启动后台任务，确保在当前事件循环中运行
    scraping_task = loop.create_task(start_scraping_task())
    
    yield
    
    # 优雅关闭
    logger.info("FastAPI application is shutting down...")
    shutdown_event.set()
    
    # 等待后台任务完成
    try:
        await asyncio.wait_for(scraping_task, timeout=30)
    except asyncio.TimeoutError:
        logger.warning("Background task did not finish within timeout, cancelling...")
        scraping_task.cancel()
        try:
            await scraping_task
        except asyncio.CancelledError:
            logger.info("Scraping task cancelled or timed out during shutdown")
        except Exception as e:
            logger.error(f"Error during task shutdown: {e}")
    
    # 关闭数据库连接
    try:
        await close_database_connection()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error closing database connection: {e}")

async def start_scraping_task():
    try:
        while not shutdown_event.is_set():
            logger.info("Starting scraping task...")

            try:
                # 确保在当前事件循环中执行任务
                # await periodic_scraping_interview_task()  
                
                await periodic_scraping_question_task()
            except Exception as e:
                logger.error(f"Error in periodic scraping task: {e}")
                # 遇到错误时等待一段时间再重试
                await asyncio.sleep(10)
            
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
        raise
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
