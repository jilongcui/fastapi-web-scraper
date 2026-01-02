from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()  # 加载 .env 文件中的所有内容
MONGO_USER = os.getenv("MONGO_USER")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
# MONGO_DETAILS = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@1.117.145.247"
MONGO_DETAILS = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@1.117.145.247"
print(MONGO_DETAILS)

# 全局变量来缓存客户端和数据库连接
_client = None
_database = None

async def get_database():
    """获取数据库连接，确保在正确的事件循环中创建"""
    global _client, _database
    
    if _client is None or _database is None:
        try:
            # 在当前事件循环中创建客户端
            _client = AsyncIOMotorClient(MONGO_DETAILS)
            _database = _client.get_database('mianshitest')  # 数据库名称：test_database
            
            # Send a ping to confirm a successful connection
            await _client.admin.command('ping')
            print("Pinged your deployment. You have successfully connected to MongoDB!")
        except Exception as e:
            print(f"Database connection error: {e}")
            raise
    
    return _database

# interview_collection = database.interviews  # 集合名称：users
async def get_interview_collection():
    database = await get_database()
    return database.get_collection('interviews')

async def get_discussion_collection():
    database = await get_database()
    return database.get_collection('discussions')

async def get_question_collection():
    database = await get_database()
    return database.get_collection('questions')

async def close_database_connection():
    """关闭数据库连接"""
    global _client, _database
    if _client:
        _client.close()
        _client = None
        _database = None
