import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional, Any, List, Dict
from models.DataView import DataView, parse_opc_data_to_data_view
from opc_connector import opc_client
from services.DataViewService import DataViewService
from config.Config import Config
from vo.ResultEntity import ErrorCode


class Manager:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

        # 配置参数
        self.database_frequency = Config.DATABASE_FREQUENCY  # 数据保存频率（秒）

        # 线程池 schedule有两个一个是周期的一个是执行的
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
        self.scheduler_executor.submit(self.schedule_database_refresh)

        self.logger.info("Manager服务启动完成")

    def schedule_database_refresh(self):
        """定时写入数据到本地文件"""
        while self._running:
            try:
                # 使用任务线程池执行缓存刷新
                self.task_executor.submit(self.refresh_database)
                time.sleep(self.database_frequency)
            except Exception as e:
                self.logger.error(f"数据刷新调度异常: {e}")
                time.sleep(1)

    def refresh_database(self):
        self.logger.info("[opc数据刷新] - opc数据刷新中")
        try:
            # 从服务器获取数据
            data_view = self.catch_data_from_opc_client(opc_client)
            data_view.dataType = ErrorCode.COLLECT.get_msg()
            self.logger.info(f"[opc数据刷新] - 获取数据dataView为: {data_view}")
            if data_view and data_view.time:
                self.save_to_database(data_view.time, data_view)
        except Exception as e:
            self.logger.error(f"[opc数据刷新] - opc数据刷新失败: {e}")
        self.logger.info("[opc数据刷新] - opc数据刷新结束")

    def catch_data_from_opc_client(self, opc_client: Any) -> Optional['DataView']:
        """
        从 OPC 服务器读取数据，将其转换为 DataView 模型，并返回。

        Args:
            opc_client: 已经连接好的 OpenOPC 客户端对象。

        Returns:
            Optional[DataView]: 成功时返回 DataView 实例，失败时返回 None。
        """
        """
        从 OPC 服务器读取数据并以 JSON 格式返回。
        """
        tag_temp = 'Bucket Brigade.Real8'
        tag_press = 'Bucket Brigade.Real4'
        tag_flow = 'Bucket Brigade.Int4'
        tag_conc = 'Bucket Brigade.String'
        tag_quality = 'Bucket Brigade.Bool'

        tag_list_to_read = [
            tag_temp, tag_press, tag_flow, tag_conc, tag_quality
        ]
        # 确保客户端已连接
        if opc_client is None:
            self.logger.error("[opc数据刷新] - OPC 客户端未初始化或连接")
            return None

        try:
            # 1. 从 OPC 服务器读取数据 (使用 dataGet 的逻辑)
            # 假设 opc_client.read 返回一个元组列表: [(tag_name, value, quality, timestamp), ...]
            read_data: List[tuple] = opc_client.read(tag_list_to_read)

            # 2. 转换为原始字典格式 (将列表转为键值对字典，便于解析函数处理)
            opc_raw_data: Dict[str, Dict[str, Any]] = {}
            for tag_name, value, quality, timestamp in read_data:
                opc_raw_data[tag_name] = {
                    "value": value,
                    "quality": quality,
                    "timestamp": timestamp
                }

            self.logger.info("OPC数据读取成功，开始转换。原始数据: %s", opc_raw_data)

            # 3. 调用之前编写的转换函数，生成 DataView 实例
            # 假设 data_type_tag 为 "opc_data"
            data_view: 'DataView' = parse_opc_data_to_data_view(
                opc_raw_data,
                data_type_tag="opc_data"  # 可根据业务需求设定或从配置中读取
            )

            # 4. 成功返回 DataView 实例
            return data_view

        except Exception as e:
            # 如果 OPC 服务死掉、连接断开或数据转换失败，会在这里捕获到异常
            self.logger.error(f"[opc数据刷新] - OPC数据获取或转换异常: {e}", exc_info=True)
            return None

    def save_to_database(self, key: datetime, data_view: DataView) -> Optional[bool]:
        """存入本地文件"""
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