import os
import logging
from logging.handlers import RotatingFileHandler
from uvicorn.config import LOGGING_CONFIG

from .settings import settings

# 使用 uvicorn 的日志级别配置
LOG_LEVELS = {
    "critical": logging.CRITICAL,
    "error": logging.ERROR, 
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG,
}

# 创建一个RotatingFileHandler，最多备份5个日志文件，每个日志文件最大5M
file_handler = RotatingFileHandler(
    os.path.join(settings.log_dir, "app.log"), 
    encoding='UTF-8', 
    maxBytes=5*1024*1024, 
    backupCount=5
)
file_handler.setLevel(LOG_LEVELS[settings.log_level.lower()])
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))

logging.basicConfig(handlers=[file_handler], level=LOG_LEVELS[settings.log_level.lower()])

# 获取根logger
logger = logging.getLogger()
logger.setLevel(LOG_LEVELS[settings.log_level.lower()])

