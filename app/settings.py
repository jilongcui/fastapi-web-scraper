import os

class Settings:
    log_dir: str = "logs"
    log_level: str = "info"

# 创建 logs 目录（如果不存在）
if not os.path.exists("logs"):
    os.makedirs("logs")

settings = Settings()