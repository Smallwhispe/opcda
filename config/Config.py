import os
from typing import Dict, Any


class Config:
    """配置类"""

    # 线程配置
    CACHE_FREQUENCY = int(os.getenv('CACHE_FREQUENCY', 10))  # 缓存刷新频率（秒）
    DATABASE_FREQUENCY = int(os.getenv('DATABASE_FREQUENCY', 20))  # 数据库保存频率（秒）

    # 缓存配置
    CACHE_MAX_SIZE = int(os.getenv('CACHE_MAX_SIZE', 100))
    CACHE_TTL = int(os.getenv('CACHE_TTL', 3600))  # 缓存过期时间（秒）

    # 线程池配置
    SCHEDULER_THREADS = int(os.getenv('SCHEDULER_THREADS', 1))
    CACHE_TASK_THREADS = int(os.getenv('CACHE_TASK_THREADS', 5))

    # OPC配置
    OPC_SERVER_URL = os.getenv('OPC_SERVER_URL', 'opc.tcp://localhost:4840')
    OPC_TIMEOUT = int(os.getenv('OPC_TIMEOUT', 30))

    # 日志配置
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """将配置转换为字典"""
        return {
            key: value for key, value in cls.__dict__.items()
            if not key.startswith('_') and not callable(value)
        }


# 创建配置实例
config = Config()