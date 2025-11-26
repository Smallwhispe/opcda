import os
import sys
from typing import Dict, Any
from dotenv import load_dotenv

# ⬅ 在定义 Config 之前就加载 .env
def get_base_dir():
    if getattr(sys, "frozen", False):
        # exe 运行时，sys.executable 指向 exe 的路径
        return os.path.dirname(sys.executable)
    # 开发运行时，使用项目根（根据你项目调整）
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)


class Config:
    """配置类"""

    # 线程配置
    DATABASE_FREQUENCY = int(os.getenv('DATABASE_FREQUENCY'))  # 数据库保存频率（秒）

    # 缓存配置
    CACHE_MAX_SIZE = int(os.getenv('CACHE_MAX_SIZE', 100))
    CACHE_TTL = int(os.getenv('CACHE_TTL', 3600))  # 缓存过期时间（秒）

    # 线程池配置
    CACHE_TASK_THREADS = int(os.getenv('CACHE_TASK_THREADS', 5))

    # OPC配置
    SERVER_NAME = os.getenv('SERVER_NAME', 'SpringOPCServer')
    PROG_ID = os.getenv('PROG_ID', 'YourCompany.OPCServer')
    READ = os.getenv('READ', 'read')
    UPDATE_RATE = int(os.getenv('UPDATE_RATE', 1000))
    CLASS_ID = os.getenv('CLASS_ID', '10000')

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """将配置转换为字典"""
        return {
            key: value for key, value in cls.__dict__.items()
            if not key.startswith('_') and not callable(value)
        }

# 创建配置实例
config = Config()