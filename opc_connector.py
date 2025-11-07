import OpenOPC
import sys
import atexit  # 用于在程序退出时自动关闭连接

# --- 配置 ---
OPC_SERVER_NAME = 'Matrikon.OPC.Simulation.1'
# 必须：填入您的 OpenOPCService.py 所在虚拟机的 IP 地址
GATEWAY_HOST = '192.168.133.128'
opc_client = None


def initialize_opc():
    """
    在 Flask 应用启动时，只调用一次此函数。
    此版本已修改为使用 OpenOPC 网关模式。
    """
    global opc_client

    # (注：在网关模式下，此客户端不需要在 Windows 上运行，
    #  因为它只使用 Pyro4。只有网关服务才需要 Windows。)
    # if sys.platform != 'win32':
    #     print("致命错误: OPC DA 只能在 Windows 上运行。")
    #     return None

    try:
        print(f"OPC 连接器: 正在连接到 OpenOPC Gateway Service (网关) at {GATEWAY_HOST}...")

        # -------------------------------------------------------------
        # !! 关键改动 !!
        # -------------------------------------------------------------
        # 原 DCOM 模式: client = OpenOPC.client()
        # 新 网关模式:
        client = OpenOPC.open_client(GATEWAY_HOST)
        # -------------------------------------------------------------

        print(f"OPC 连接器: 已连接到网关。正在通过网关连接到 OPC 服务器 '{OPC_SERVER_NAME}'...")
        # 2. 连接到 Matrikon 服务器（此调用不变，但现在是通过网关执行）
        client.connect(OPC_SERVER_NAME)

        print("OPC 连接器: 初始化并连接成功！")

        # 3. 注册一个清理函数，以便在 Flask 关闭时断开连接
        atexit.register(client.close)

        return client

    except Exception as e:
        print(f"OPC 连接器: 初始化失败: {e}")
        return None


# -----------------------------------------------------------------
# 关键：当这个模块被导入时，立即初始化客户端。
# -----------------------------------------------------------------
print(f"客户端: 正在初始化 OpenOPC 客户端 (网关模式)...")
opc_client = initialize_opc()