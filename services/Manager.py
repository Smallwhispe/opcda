import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional
from models.DataView import DataView
from services.DataViewService import DataViewService
from config.Config import Config
from vo.ResultEntity import ErrorCode


class Manager:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

        # 配置参数
        self.cache_frequency = Config.CACHE_FREQUENCY  # 缓存刷新频率（秒）
        self.database_frequency = Config.DATABASE_FREQUENCY  # 数据库保存频率（秒）

        # 线程池 schedule有两个一个是缓存的一个是数据库的
        self.scheduler_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="Manager-Scheduler")
        self.task_executor = ThreadPoolExecutor(max_workers=Config.CACHE_TASK_THREADS, thread_name_prefix="Manager-Task")

        # 控制标志
        self._running = False

    def start(self):
        """启动服务"""
        if self._running:
            self.logger.warning("服务已经在运行中")
            return

        self._running = True
        self.logger.info("启动Manager服务")

        # # 使用线程池启动定时任务
        self.scheduler_executor.submit(self._schedule_cache_refresh)

        self.logger.info("Manager服务启动完成")

    def _schedule_cache_refresh(self):
        """定时刷新缓存"""
        while self._running:
            try:
                # 使用任务线程池执行缓存刷新
                self.task_executor.submit(self.refresh_cache)
                time.sleep(self.cache_frequency)
            except Exception as e:
                self.logger.error(f"缓存刷新调度异常: {e}")
                time.sleep(1)

    def refresh_cache(self):
        """缓存刷新主函数"""
        self.logger.info("[opc缓存刷新] - opc数据缓存刷新中")
        try:
            data_view = self.catch_data_from_opc_client()
            data_view.dataType = ErrorCode.COLLECT.get_msg()
            self.logger.info(f"[opc缓存刷新] - 获取数据dataView为: {data_view}")
            if data_view and data_view.time:
                self.save_to_cache(data_view.time, data_view)
        except Exception as e:
            self.logger.error(f"[opc缓存刷新] - opc数据缓存刷新失败: {e}")
        self.logger.info("[opc缓存刷新] - opc数据缓存刷新结束")

    def catch_data_from_opc_client(self) -> Optional[DataView]:
        """从OPC服务器获取数据"""
        try:
            data_view = DataView()
            data_view.time = int(time.time())
            # TODO 模拟数据获取
            time.sleep(0.1)
            return data_view
        except Exception as e:
            self.logger.error(f"[opc缓存刷新] - opc获取数据异常: {e}")
            return None

    def save_to_cache(self, key: datetime, data_view: DataView) -> Optional[bool]:
        """存入缓存"""
        if key is None or data_view is None:
            return False

        try:
            if data_view.id is None:
                self.logger.warning("[opc缓存刷新] - 尝试保存空数据")
                return False
            result = DataViewService.save(data_view)
            if result:
                self.logger.debug(f"[opc缓存刷新] - 数据成功保存到数据库，key: {key}")
            else:
                self.logger.warning(f"[opc缓存刷新] - 数据保存到数据库失败，key: {key}")
            return result
        except Exception as e:
            self.logger.error(f"保存数据到缓存失败，key: {key}, 错误: {e}")
            return False

    def shutdown(self):
        """关闭服务"""
        if not self._running:
            return

        self.logger.info("Manager服务关闭中...")
        self._running = False

        # 关闭线程池
        self.scheduler_executor.shutdown(wait=False, cancel_futures=True)
        self.task_executor.shutdown(wait=False, cancel_futures=True)

        self.logger.info("Manager服务已关闭")

    @property
    def running(self):
        return self._running