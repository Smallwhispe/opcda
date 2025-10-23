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