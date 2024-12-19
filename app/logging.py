import os
import logging
from logging.handlers import RotatingFileHandler

from uvicorn.config import LOG_LEVELS

from settings import settings

# 创建一个RotatingFileHandler，最多备份5个日志文件，每个日志文件最大5M
file_handler = RotatingFileHandler(os.path.join(settings.log_dir, "uvicorn.log"), encoding='UTF-8', maxBytes=5*1024*1024, backupCount=5)
file_handler.setLevel(LOG_LEVELS[settings.log_level])
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s  %(message)s'))

logging.basicConfig(handlers=[file_handler])

# 获取Uvicorn的logger并添加文件处理器
logger = logging.getLogger("uvicorn")
logger.setLevel(LOG_LEVELS[settings.log_level])
# logger.addHandler(file_handler)  # 没打印日志到文件中，还没找到原因

