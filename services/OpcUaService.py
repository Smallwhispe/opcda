# services/OpcUaService.py
import asyncio
import logging
import sys
import os
from concurrent.futures import ThreadPoolExecutor

from services.repository_sqlite import get_recent_n, DB_PATH

# 防止导入错误
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from asyncua import Server
from config.Config import config

# 使用 logger 确保日志不被吞
logger = logging.getLogger("OPC_UA_Service")
logger.setLevel(logging.INFO)  # 确保 INFO 级别能显示


class OpcUaService:
    def __init__(self):
        self.server = None
        self._running = False
        self.tag_list = [tag.strip() for tag in config.OPC_TAGS.split(',') if tag.strip()]
        self.opc_nodes = {}
        # 创建一个线程池专门用来读数据库，防止卡死主循环
        self.db_executor = ThreadPoolExecutor(max_workers=1)

    async def run_server(self):
        """主 Asyncio 循环"""
        logger.info(f"--- [启动] 初始化 UA Server, 点位: {len(self.tag_list)} 个 ---")

        # 打印当前数据库绝对路径，请检查它是否与 Manager 写入的路径一致
        abs_db_path = os.path.abspath(DB_PATH)
        logger.warning(f"--- [检查] 正在读取的数据库路径: {abs_db_path} ---")

        self.server = Server()
        await self.server.init()

        endpoint = "opc.tcp://0.0.0.0:4840/opcua/server/"
        self.server.set_endpoint(endpoint)
        self.server.set_server_name("Integrated_OPC_UA_Server")

        uri = "http://your-company.org/opc-bridge"
        idx = await self.server.register_namespace(uri)

        objects = self.server.nodes.objects
        my_folder = await objects.add_object(idx, "ProcessData")

        for tag_name in self.tag_list:
            clean_name = tag_name.replace('.', '_')
            node_id_str = f"ns={idx};s={clean_name}"
            node = await my_folder.add_variable(node_id_str, clean_name, 0.0)
            await node.set_writable(False)
            self.opc_nodes[tag_name] = node

        logger.info(f"--- [启动] Server 就绪: {endpoint} ---")
        self._running = True

        # 获取当前事件循环
        loop = asyncio.get_running_loop()

        async with self.server:
            while self._running:
                try:
                    # =======================================================
                    # 关键修改：将阻塞的数据库读取放到线程池执行
                    # =======================================================
                    # 这里的 lambda 是为了传参 n=1
                    recent_data = await loop.run_in_executor(
                        self.db_executor,
                        lambda: get_recent_n(n=1)
                    )

                    if not recent_data:
                        # 这是一个高频错误，证明读到了空列表
                        # 此时请检查 repository 目录下是否有 history.db
                        logger.warning("!!! [警告] 数据库返回空！请检查 history.db 是否存在且有数据 !!!")
                    else:
                        latest_record = recent_data[0]
                        values_dict = latest_record.get('values', {})

                        # logger.info(f"--- [调试] 读到数据时间: {latest_record.get('time')} ---") # 调试用，确认读到了

                        count = 0
                        for tag, node in self.opc_nodes.items():
                            # ============================================
                            # 修复核心：将配置的点号名转换为数据库的下划线名
                            # TI1352A.DACA.PV -> TI1352A_DACA_PV
                            # ============================================
                            db_key = tag.replace('.', '_')

                            # 使用转换后的 key 去字典取值
                            val = values_dict.get(db_key)

                            if val is not None:
                                try:
                                    await node.write_value(float(val))
                                    count += 1
                                except Exception as e:
                                    logger.error(f"写入节点 {tag} 失败: {e}")

                        # 如果 count 为 0，说明数据库里的 key 和 tag_list 没对上
                        if count == 0 and values_dict:
                            logger.warning(
                                f"!!! [警告] 数据库有数据，但没有匹配到任何点位！DB Keys: {list(values_dict.keys())[:3]}... !!!")

                    await asyncio.sleep(1)

                except Exception as e:
                    logger.error(f"UA 循环异常: {e}")
                    await asyncio.sleep(2)

    def start_in_thread(self):
        if sys.platform.lower() == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(self.run_server())

    def stop(self):
        self._running = False
        self.db_executor.shutdown(wait=False)