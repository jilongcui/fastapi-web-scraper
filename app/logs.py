# logs.py
import logging
import sys

# 配置根 logger
# if not logging.getLogger().hasHandlers():
#     logging.basicConfig(
#         level=logging.INFO,
#         format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#         handlers=[
#             logging.FileHandler('app.log'),
#             # logging.StreamHandler()   # 也可以输出到控制台
#         ]
#     )
# logging.basicConfig(
#     level=logging.DEBUG,
#     format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
#     handlers=[
#         logging.StreamHandler()
#     ]
# )
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# StreamHandler für die Konsole
stream_handler = logging.StreamHandler(sys.stdout)
log_formatter = logging.Formatter("%(asctime)s [%(processName)s: %(process)d] [%(threadName)s: %(thread)d] [%(levelname)s] %(name)s: %(message)s")
stream_handler.setFormatter(log_formatter)
logger.addHandler(stream_handler)

file_handler = logging.FileHandler('app.log')
file_handler.setFormatter(log_formatter)
logger.addHandler(file_handler)

logging.getLogger(__name__).info('API is starting up')

# 可选：封装获取 logger 的功能
def get_logger(name):
    logger = logging.getLogger(name)
    # logger.setLevel(logging.DEBUG)

    # # StreamHandler für die Konsole
    # stream_handler = logging.StreamHandler(sys.stdout)
    # log_formatter = logging.Formatter("%(asctime)s [%(processName)s: %(process)d] [%(threadName)s: %(thread)d] [%(levelname)s] %(name)s: %(message)s")
    # stream_handler.setFormatter(log_formatter)
    # logger.addHandler(stream_handler)
    return logger