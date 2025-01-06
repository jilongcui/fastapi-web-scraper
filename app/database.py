from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()  # 加载 .env 文件中的所有内容
MONGO_USER = os.getenv("MONGO_USER")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGO_DETAILS = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@1.117.145.247"
print(MONGO_DETAILS)
client = AsyncIOMotorClient(MONGO_DETAILS)
database = client.get_database('mianshitest')   # 数据库名称：test_database
# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You have successfully connected to MongoDB!")
except Exception as e:
    print(e) 
# interview_collection = database.interviews  # 集合名称：users
async def get_interview_collection():
    return database.get_collection('interviews')

async def get_discussion_collection():
    return database.get_collection('discussions')