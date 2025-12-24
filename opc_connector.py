# opc_connector.py

import OpenOPC
import sys
import atexit
import logging
import time
from config.Config import config

logger = logging.getLogger(__name__)

# --- 配置 ---
OPC_SERVER_NAME = config.SERVER_NAME
GATEWAY_HOST = config.GATEWAY_HOST

# 全局变量，用于缓存客户端实例
_opc_client_instance = None


def create_connection():
    """创建一个新的 OPC 连接"""
    try:
        logger.info(f"OPC 连接器: 正在连接到 OpenOPC Gateway ({GATEWAY_HOST})...")
        client = OpenOPC.open_client(GATEWAY_HOST)

        logger.info(f"OPC 连接器: 已连接网关，正在连接 OPC Server '{OPC_SERVER_NAME}'...")
        client.connect(OPC_SERVER_NAME)

        logger.info("OPC 连接器: 连接建立成功！")
        return client
    except Exception as e:
        logger.error(f"OPC 连接器: 连接创建失败: {e}")
        return None


def get_opc_client():
    """
    获取可用的 OPC Client 实例。
    如果当前连接失效，会自动尝试重连。
    """
    global _opc_client_instance

    # 1. 如果没有实例，尝试创建
    if _opc_client_instance is None:
        _opc_client_instance = create_connection()
        return _opc_client_instance

    # 2. 如果有实例，检查心跳 (Ping)
    try:
        # ping() 方法在 OpenOPC.py 中已定义，它会检查 CurrentTime 是否变化
        if not safe_ping(_opc_client_instance):
            logger.warning("OPC 连接器: 心跳检测失败 (Ping return False)，正在重连...")
            raise Exception("Ping failed")

        # 心跳正常，直接返回
        return _opc_client_instance

    except Exception as e:
        logger.warning(f"OPC 连接器: 连接检测到异常 ({e})，正在执行重置和重连...")

        # 尝试清理旧连接
        try:
            _opc_client_instance.close()
        except:
            pass

        # 销毁旧对象
        _opc_client_instance = None

        # 重新创建
        _opc_client_instance = create_connection()
        return _opc_client_instance


def safe_ping(client):
    """
    安全的 Ping 操作。
    专门处理 'float() argument must be a string...' 这种库 Bug。
    """
    try:
        # 尝试调用原生 ping
        return client.ping()
    except Exception as e:
        err_str = str(e)

        # 核心修复逻辑：
        # 如果捕获到 pywintypes.datetime 类型转换错误，说明服务端其实是通的（否则连时间对象都拿不到）
        # 返回 True (连接正常)
        # 优化：使用 lower() 忽略大小写，且只要包含关键字即视为该错误，防止报错文本差异
        err_lower = err_str.lower()
        if "pywintypes" in err_lower or "float" in err_lower and "datetime" in err_lower:
            # logger.debug(f"已忽略 OpenOPC 兼容性错误，视为连接正常: {err_str}")
            return True

        # 如果是真正的连接错误（如 Socket closed, Timeout），则继续抛出
        raise e
def close_connection():
    """手动关闭连接（供程序退出使用）"""
    global _opc_client_instance
    if _opc_client_instance:
        try:
            _opc_client_instance.close()
            logger.info("OPC 连接器: 连接已关闭")
        except Exception as e:
            logger.error(f"OPC 连接器: 关闭连接时出错: {e}")
        finally:
            _opc_client_instance = None


# 注册退出时的清理
atexit.register(close_connection)

# 初始化时不再直接创建连接，而是让第一次调用 get_opc_client 时去创建
# opc_client = initialize_opc()  <-- 删除这行