import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional, Any
from cachetools import TTLCache

from models.DataView import DataView
from services.DataViewService import DataViewService


class Manager:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

        # 配置参数
        self.cache_frequency = 10  # 缓存刷新频率（秒）
        self.database_frequency = 20  # 数据库保存频率（秒）

        # 线程池
        self.scheduler_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="Manager-Scheduler")
        self.task_executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="Manager-Task")

        # 缓存
        self.user_cache = TTLCache(maxsize=100, ttl=3600)

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
        self.scheduler_executor.submit(self._schedule_database_save)

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

    def _schedule_database_save(self):
        """定时保存到数据库"""
        while self._running:
            try:
                # 使用任务线程池执行数据库保存
                self.task_executor.submit(self.scheduled_batch_save)
                time.sleep(self.database_frequency)
            except Exception as e:
                self.logger.error(f"数据库保存调度异常: {e}")
                time.sleep(1)

    def refresh_cache(self):
        """缓存刷新主函数"""
        self.logger.info("[opc缓存刷新] - opc数据缓存刷新中")
        try:
            data_view = self.catch_data_from_opc_client()
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
            # 模拟数据获取
            time.sleep(0.1)
            return data_view
        except Exception as e:
            self.logger.error(f"[opc缓存刷新] - opc获取数据异常: {e}")
            return None

    def save_to_cache(self, key: int, data_view: DataView):
        """存入缓存"""
        if key is None or data_view is None:
            return

        try:
            if data_view.id is None:
                self.logger.warning("[opc缓存刷新] - 尝试保存空数据")
                return
            self.user_cache[key] = data_view
            self.logger.debug(f"数据成功保存到缓存，key: {key}")
        except Exception as e:
            self.logger.error(f"保存数据到缓存失败，key: {key}, 错误: {e}")

    def scheduled_batch_save(self):
        """定时批量保存到数据库"""
        self.logger.info("[opc缓存刷新] - 开始保存缓存数据至数据库")
        if len(self.user_cache) > 0:
            self.logger.info(f"[opc缓存刷新] - 定时任务开始批量保存缓存数据，当前缓存大小: {len(self.user_cache)}")
            cache_copy = dict(self.user_cache)
            self.batch_save_to_database(cache_copy)

        # 清理过期缓存
        self.user_cache.expire()

    def batch_save_to_database(self, data_map: Dict[int, DataView]):
        """批量存入数据库"""
        if not data_map:
            self.logger.warning("[opc缓存刷新] - opc缓存为空")
            return

        try:
            success_count = 0
            for key, data_view in data_map.items():
                if self.save_to_database(key, data_view):
                    success_count += 1

            self.logger.info(f"[opc缓存刷新] - 批量保存完成，共保存 {success_count}/{len(data_map)} 条数据")
        except Exception as e:
            self.logger.error(f"[opc缓存刷新] - 批量保存数据失败: {e}")

    def save_to_database(self, key: int, data_view: DataView) -> bool:
        """存入数据库"""
        if key is None or data_view is None:
            return False

        try:
            result = DataViewService.save(data_view)
            if result:
                self.logger.debug(f"[opc缓存刷新] - 数据成功保存到数据库，key: {key}")
            else:
                self.logger.warning(f"[opc缓存刷新] - 数据保存到数据库失败，key: {key}")
            return result
        except Exception as e:
            self.logger.error(f"[opc缓存刷新] - 保存数据到数据库失败，key: {key}, 错误: {e}")
            return False

    def get_from_cache(self, key: int) -> Optional[DataView]:
        """从缓存获取数据"""
        try:
            return self.user_cache.get(key)
        except Exception as e:
            self.logger.error(f"[opc缓存] - 从缓存获取数据失败，key: {key}, 错误: {e}")
            return None

    def get_cache_status(self) -> Dict[str, Any]:
        """获取缓存状态信息"""
        return {
            "缓存大小": len(self.user_cache),
            "运行状态": "运行中" if self._running else "已停止"
        }

    def shutdown(self):
        """关闭服务"""
        if not self._running:
            return

        self.logger.info("Manager服务关闭中...")
        self._running = False

        # 关闭前保存所有缓存数据到数据库
        if len(self.user_cache) > 0:
            self.logger.info(f"服务关闭前保存剩余缓存数据，数量: {len(self.user_cache)}")
            remaining_data = dict(self.user_cache)
            self.batch_save_to_database(remaining_data)

        # 关闭线程池
        self.scheduler_executor.shutdown(wait=False, cancel_futures=True)
        self.task_executor.shutdown(wait=False, cancel_futures=True)

        self.logger.info("Manager服务已关闭")

    @property
    def running(self):
        return self._running