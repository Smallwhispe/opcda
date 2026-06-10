import sys
import asyncio
import logging
import socket
import os
from unittest.mock import MagicMock

# =========================================================================
# 第一步：环境模拟 (Mock)
# 在导入你的 OpcUaService 之前，先把它依赖的 config 和数据库模块“伪造”出来
# 这样你不需要真实的数据库也能跑通代码。
# =========================================================================
#
# print(">>> [1/5] 正在初始化模拟环境...")
#
# # 1. 模拟 config.Config
# mock_config_module = MagicMock()
# # 设置模拟的 URL (端口 4840)
# mock_config_module.config.OPC_UA_URL = "opc.tcp://0.0.0.0:4840/opcua/server/"
# mock_config_module.config.OPC_UA_NAMESPACE_URI = "http://test.org/predict"
# sys.modules["config.Config"] = mock_config_module
# sys.modules["config"] = mock_config_module
#
# # 2. 模拟 services.predict_result (数据库读取)
# mock_db_module = MagicMock()
# mock_db_module.DB_PATH = "mock_test.db"
# # 让它永远返回一条固定的测试数据
# mock_db_module.get_recent_n.return_value = [{
#     'pressure': '101.325',
#     'c5': '50.5',
#     'bing_xi': '12.3',
#     'gan_dian': '99.9'
# }]
# sys.modules["services.predict_result"] = mock_db_module
# sys.modules["predict_result"] = mock_db_module
#
# print(">>> [1/5] 模拟环境初始化完成。")

# =========================================================================
# 第二步：导入你的服务端代码
# =========================================================================
try:
    from services.OpcUaService import OpcUaService
    from asyncua import Client
except ImportError:
    # 尝试直接导入（如果文件在根目录）
    try:
        from OpcUaService import OpcUaService
        from asyncua import Client
    except ImportError as e:
        print(f"❌ 错误：找不到 OpcUaService.py 文件。请确保此脚本与 services 文件夹在同一级。\n详细错误: {e}")
        sys.exit(1)

# 配置日志输出到控制台
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Test_Script")


async def main_test():
    # =========================================================================
    # 第三步：启动服务端
    # =========================================================================
    print(">>> [2/5] 正在启动 OPC UA 服务端...")

    # 实例化服务
    service = OpcUaService()

    # 在后台任务中启动服务器（因为 run_server 是死循环）
    # 我们不直接 await run_server，而是用 create_task 让它在后台跑
    server_task = asyncio.create_task(service.run_server())

    # 给服务器 5 秒钟时间启动和生成证书
    print(">>> [等待] 等待服务器启动和证书生成 (5秒)...")
    await asyncio.sleep(5)

    # =========================================================================
    # 第四步：启动测试客户端进行连接
    # =========================================================================

    # 获取本机真实 IP (为了模拟 PACE 的连接方式)
    hostname = socket.gethostname()
    real_ip = socket.gethostbyname(hostname)
    # 构造连接地址
    endpoint_url = f"opc.tcp://{real_ip}:48400/opcua/server/"

    print(f">>> [3/5] 尝试使用客户端连接: {endpoint_url} ...")

    client = Client(url=endpoint_url)

    try:
        # 连接服务端
        await client.connect()
        print(">>> ✅ [成功] 客户端已连接！")

        # =========================================================================
        # 第五步：验证数据
        # =========================================================================
        print(">>> [4/5] 正在读取节点数据...")

        # 获取命名空间索引
        ns_idx = await client.get_namespace_index("http://test.org/predict")
        print(f"    -> 获取到命名空间 Index: {ns_idx}")

        # 构造 NodeID (根据你的代码逻辑: start_id=50001, 第一个是 pressure)
        # pressure 的 ID 应该是 ns=Index;i=50001
        pressure_node_id = f"ns={ns_idx};i=50001"
        var_node = client.get_node(pressure_node_id)

        # 读取值
        val = await var_node.read_value()
        print(f"    -> 读取到 'pressure' (i=50001) 的值: {val}")

        # 验证值是否是我们在第一步模拟的 '101.325'
        if abs(val - 101.325) < 0.001:
            print(">>> ✅ [测试通过] 读取到的数值与模拟数据库一致！")
        else:
            print(f">>> ❌ [测试失败] 数值不匹配！期望 101.325，实际 {val}")

    except Exception as e:
        print(f">>> ❌ [连接失败] 无法连接或读取数据: {e}")
        print("    提示：请检查防火墙是否关闭，或者证书是否生成正确。")
    finally:
        # =========================================================================
        # 收尾：断开连接并停止服务
        # =========================================================================
        print(">>> [5/5] 测试结束，正在清理资源...")
        try:
            await client.disconnect()
        except:
            pass

        # 停止服务端
        service.stop()
        # 等待服务端任务退出
        try:
            await asyncio.wait_for(server_task, timeout=2)
        except asyncio.TimeoutError:
            print("    -> 服务端已强制停止")
        except Exception:
            pass

        print(">>> 测试脚本运行完毕。")


if __name__ == "__main__":
    # Windows 下必须使用的 EventLoop 策略
    if sys.platform.lower() == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main_test())