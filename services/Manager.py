import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional, Any, List, Dict
from models.DataView import DataView, parse_opc_data_to_data_view
# from opc_connector import opc_client
from opc_connector import get_opc_client  # <-- 改为导入这个函数
from services.DataViewService import DataViewService
from config.Config import Config
from services.ModelService import ModelService
from services.OpcUaService import OpcUaService
from vo.ResultEntity import ErrorCode


logger = logging.getLogger(__name__)
logging.getLogger("asyncua.server.address_space").setLevel(logging.WARNING)
logging.getLogger("asyncua.server.internal_server").setLevel(logging.WARNING)
class Manager:
    def __init__(self):
        # 配置参数
        self.database_frequency = Config.DATABASE_FREQUENCY  # 数据保存频率（秒）

        # 线程池 schedule有两个一个是周期的一个是执行的
        self.scheduler_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="Manager-Scheduler")
        self.task_executor = ThreadPoolExecutor(max_workers=Config.CACHE_TASK_THREADS, thread_name_prefix="Manager-Task")

        # --- 新增: OPC UA 服务实例 ---
        self.opc_ua_service = OpcUaService()
        self.ua_thread = None  # 用于持有线程引用

        # 控制标志
        self._running = False

    def start(self):
        """启动服务"""
        if self._running:
            logger.warning("服务已经在运行中")
            return

        self._running = True
        logger.info("启动Manager服务")

        # # 使用线程池启动定时任务
        self.scheduler_executor.submit(self.schedule_database_refresh)
        # self.scheduler_executor.submit(self.schedule_model_predict)

        # 2. 启动 OPC UA Server (新增逻辑)
        # 必须使用独立的 Thread，因为它是 asyncio 的死循环，不能阻塞当前线程
        self.ua_thread = threading.Thread(
            target=self.opc_ua_service.start_in_thread,
            name="OpcUaServer-Thread",
            daemon=True  # 设置为守护线程，主程序退出时它会自动退出
        )
        self.ua_thread.start()
        logger.info("OPC UA Server 线程已启动")

        logger.info("Manager服务启动完成")

    def schedule_model_predict(self):
        """定时预测"""
        while self._running:
            try:
                # 使用任务线程池执行缓存刷新
                result = ModelService.model_predict()
                time.sleep(self.database_frequency)
            except Exception as e:
                logger.error(f"数据刷新调度异常: {e}")
                time.sleep(1)

    def schedule_database_refresh(self):
        """定时写入数据到本地文件"""
        while self._running:
            try:
                # 使用任务线程池执行缓存刷新
                self.task_executor.submit(self.refresh_database)
                time.sleep(self.database_frequency)
            except Exception as e:
                logger.error(f"数据刷新调度异常: {e}")
                time.sleep(1)

    def refresh_database(self):
        logger.info("[opc数据刷新] - opc数据刷新中")
        try:
            # --- 关键修改：每次执行任务时，动态获取(或重连)客户端 ---
            current_client = get_opc_client()

            if current_client is None:
                logger.error("[opc数据刷新] - 无法获取 OPC 客户端连接，跳过本次刷新")
                return

            # 将获取到的 current_client 传入
            data_view = self.catch_data_from_opc_client(current_client)

            logger.info(f"[opc数据刷新] - 获取数据dataView为: {data_view}")
            if data_view and data_view.time:
                self.save_to_database(data_view.time, data_view)
        except Exception as e:
            logger.error(f"[opc数据刷新] - opc数据刷新失败: {e}")
        logger.info("[opc数据刷新] - opc数据刷新结束")

    def catch_data_from_opc_client(self, opc_client: Any) -> Optional['DataView']:
        """
        从 OPC 服务器读取数据 (点位由 .env 配置)，
        直接将原始列表数据传给 DataView 解析器。
        """

        # --- 1. 从环境变量获取配置的点位 ---
        tags_env_str = Config.OPC_TAGS
        logger.info(f"[opc数据刷新] - 从环境变量获取的 OPC_TAGS: {tags_env_str}")
        if tags_env_str:
            tag_list_to_read = [tag.strip() for tag in tags_env_str.split(',') if tag.strip()]
        else:
            logger.error("[opc数据刷新] - .env 文件中未配置 OPC_TAGS")
            return None

        # --- 2. 检查客户端状态 ---
        if opc_client is None:
            logger.error("[opc数据刷新] - OPC 客户端未初始化或连接")
            return None
        # logger.info(
        #     f"[opc数据刷新] - 正在从 OPC 服务器读取数据，点位列表样本: {tag_list_to_read[:5]}...")  # 仅打印前5个点位以防日志过长
        read_data = opc_client.read(tag_list_to_read)
        # logger.info(f"[opc数据刷新] - 读取到的原始数据样本: {read_data}")  # 仅打印前500字符以防日志过长
        try:
            # --- 3. 读取数据 (List[tuple]) ---
            # 返回格式示例: [('TIC1201B...', 12.5, 'Good', '2025-11-27...'), ...]

            if not read_data:
                logger.warning("[opc数据刷新] - 未读取到任何数据")
                return None

            logger.info(f"OPC数据读取成功")

            # --- 4. 直接转换 ---
            # 移除了中间的字典转换循环，直接把 read_data 列表扔给解析器
            # 解析器内部会自动识别 List 类型并处理
            data_view: 'DataView' = parse_opc_data_to_data_view(
                read_data,
                data_type_tag="采样数据"
            )

            return data_view

        except Exception as e:
            logger.error(f"[opc数据刷新] - OPC数据获取或转换异常: {e}", exc_info=True)
            return None

    def save_to_database(self, key: datetime, data_view: DataView) -> Optional[bool]:
        """存入本地文件"""
        if key is None or data_view is None:
            return False

        try:
            if data_view.id is None:
                logger.warning("[opc缓存刷新] - 尝试保存空数据")
                return False
            result = DataViewService.save(data_view)
            if result:
                logger.debug(f"[opc缓存刷新] - 数据成功保存到数据库，key: {key}")
            else:
                logger.warning(f"[opc缓存刷新] - 数据保存到数据库失败，key: {key}")
            return result
        except Exception as e:
            logger.error(f"保存数据到缓存失败，key: {key}, 错误: {e}")
            return False

    def shutdown(self):
        """关闭服务"""
        if not self._running:
            return

        logger.info("Manager服务关闭中...")
        self._running = False

        # 停止 UA 服务标志
        if self.opc_ua_service:
            self.opc_ua_service.stop()

        # 关闭线程池
        self.scheduler_executor.shutdown(wait=False, cancel_futures=True)
        self.task_executor.shutdown(wait=False, cancel_futures=True)

        logger.info("Manager服务已关闭")

    @property
    def running(self):
        return self._running