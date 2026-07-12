# services/OpcUaService.py
import asyncio
import logging
import sys
import os
from concurrent.futures import ThreadPoolExecutor
import socket
import ipaddress
from cryptography import x509
from cryptography.hazmat._oid import NameOID
from cryptography.hazmat.primitives.asymmetric import rsa
import datetime
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from urllib.parse import urlparse  # 新增：用于解析配置文件的 URL
# =========================================================
# 修改点 1: 导入 predict_result 中的方法和路径
# 请确保 predict_result.py 在 Python 的搜索路径中
# 如果文件位于 services 文件夹下，请保持如下导入：
try:
    from services.predict_result import get_recent_n, DB_PATH
except ImportError:
    # 如果文件在根目录
    from predict_result import get_recent_n, DB_PATH
# =========================================================

from asyncua import Server,ua

from config.Config import config

# 使用 logger 确保日志不被吞
logger = logging.getLogger("OPC_UA_Service")
logger.setLevel(logging.INFO)


class OpcUaService:
    def __init__(self):
        self.server = None
        self._running = False
        # 要暴露的预测字段
        self.target_fields = ['pressure', 'c5', 'bing_xi', 'gan_dian']
        self.opc_nodes = {}
        # 数据库读取线程池
        self.db_executor = ThreadPoolExecutor(max_workers=1)

    @staticmethod
    def generate_self_signed_cert(endpoint_ip, cert_file, key_file):
        """
        使用 cryptography 库生成自签名证书和私钥
        :param endpoint_ip: 服务器的真实 IP 地址 (如 192.168.57.235)
        :param cert_file: 证书保存路径 (.pem)
        :param key_file: 私钥保存路径 (.pem)
        """
        logger.info(f"正在为 IP: {endpoint_ip} 生成新的自签名证书...")

        # 1. 生成私钥
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # 2. 构建证书信息
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, u"CN"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Shanghai"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"PredictModel"),
            x509.NameAttribute(NameOID.COMMON_NAME, u"Predict_Result_OPC_Server"),
        ])

        # 3. 添加 IP 地址到 SAN (Subject Alternative Name)
        # 这一步非常关键！PACE 等工业软件会严格校验 IP 是否在证书允许列表中
        alt_names = [
            x509.DNSName(u"localhost"),
            x509.IPAddress(ipaddress.ip_address(socket.gethostbyname(socket.gethostname()))),
            x509.UniformResourceIdentifier(u"urn:Predict_Result_OPC_Server")  # 与 Server Name 匹配
        ]
        # 尝试添加传入的真实 IP
        try:
            alt_names.append(x509.IPAddress(ipaddress.ip_address(endpoint_ip)))
        except ValueError:
            logger.warning(f"IP {endpoint_ip} 格式无效，未添加到证书 SAN 中")

        # 4. 签署证书
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            subject
        ).public_key(
            key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            # 有效期 10 年
            datetime.datetime.utcnow() + datetime.timedelta(days=3650)
        ).add_extension(
            x509.SubjectAlternativeName(alt_names),
            critical=False,
        ).sign(key, hashes.SHA256())

        # 5. 写入文件
        with open(key_file, "wb") as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            ))

        with open(cert_file, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        logger.info(f"证书已生成: {cert_file}, {key_file}")

    async def run_server(self):
        """主 Asyncio 循环"""
        logger.info(f"--- [启动] 初始化 UA Server, 预测字段: {self.target_fields} ---")

        abs_db_path = os.path.abspath(DB_PATH)
        logger.warning(f"--- [检查] 正在读取的数据库路径: {abs_db_path} ---")

        # 初始化服务器
        self.server = Server()
        await self.server.init()
        cert_file = "certificate.pem"
        key_file = "private_key.pem"
        endpoint = config.OPC_UA_URL
        # ------------------------------------------------------------
        # 智能解析配置：处理 0.0.0.0 和真实 IP 的关系
        # ------------------------------------------------------------
        # 解析 Config 中的 URL: opc.tcp://0.0.0.0:4840/opcua/server/
        parsed_url = urlparse(endpoint)
        conf_port = parsed_url.port if parsed_url.port else 4840
        conf_path = parsed_url.path  # /opcua/server/

        # 获取本机真实 IP (用于证书和 PACE 连接)
        # 获取 hostname 对应的 IP，通常是 192.168.x.x
        hostname = socket.gethostname()
        real_ip = socket.gethostbyname(hostname)
        logger.info(f"检测到本机真实 IP: {real_ip}, 配置端口: {conf_port}")

        # 构造最终使用的 Endpoint
        # 虽然 Config 写的是 0.0.0.0，但我们告诉服务器 endpoint 是真实 IP
        # 这样客户端发现服务时，拿到的是能连通的 IP，而不是无法连接的 0.0.0.0
        final_endpoint = f"opc.tcp://{real_ip}:{conf_port}{conf_path}"

        self.server.set_endpoint(final_endpoint)
        self.server.set_server_name("Predict_Result_OPC_Server")
        logger.info(f"设置 Endpoint 为: {final_endpoint}")

        # ------------------------------------------------------------
        # 证书处理 (解决 BadCertificateInvalid 问题)
        # ------------------------------------------------------------
        cert_file = "certificate.pem"
        key_file = "private_key.pem"

        # 如果证书不存在，或者我们要强制刷新(建议先手动删一次)，则生成
        if not os.path.exists(cert_file) or not os.path.exists(key_file):
            try:
                # 传入 real_ip，确保证书里写的是 192.168.x.x
                self.generate_self_signed_cert(real_ip, cert_file, key_file)
            except Exception as e:
                logger.error(f"证书生成失败: {e}")

        # 【关键】先加载证书
        if os.path.exists(cert_file) and os.path.exists(key_file):
            logger.info("正在加载服务端证书...")
            await self.server.load_certificate(cert_file)
            await self.server.load_private_key(key_file)
        self.server.set_security_policy([ua.SecurityPolicyType.NoSecurity])
        self.server.set_security_IDs(["Anonymous"])  # 仅允许匿名访问


        self.server.set_endpoint(endpoint)
        self.server.set_server_name("Predict_Result_OPC_Server")

        # 注册命名空间
        uri = config.OPC_UA_NAMESPACE_URI
        idx = await self.server.register_namespace(uri)

        # 创建对象文件夹
        objects = self.server.nodes.objects
        my_folder = await objects.add_object(idx, "PredictData")

        # >>>>>>>>>>>>>>>>>> 关键修复 2：使用 Numeric NodeId <<<<<<<<<<<<<<<<<<
        start_id = 50001  # 起始 ID，Honeywell 常用范围
        for i, field_name in enumerate(self.target_fields):
            node_id = ua.NodeId(start_id + i, idx)  # ns=2;i=50001, 50002...
            node = await my_folder.add_variable(node_id, field_name, 0.0)
            await node.set_writable(False)  # 只读
            self.opc_nodes[field_name] = node
            logger.info(f"创建节点: {node_id} -> {field_name}")
        # >>>>>>>>>>>>>>>>>> 结束 <<<<<<<<<<<<<<<<<<

        logger.info(f"--- [启动] OPC UA 服务器就绪: {endpoint} ---")
        self._running = True

        # 主循环：每秒更新数据
        loop = asyncio.get_running_loop()
        async with self.server:
            while self._running:
                try:
                    recent_data = await loop.run_in_executor(
                        self.db_executor,
                        lambda: get_recent_n(n=1)
                    )

                    if not recent_data:
                        logger.warning("!!! [警告] 数据库 predict 表返回空！请检查是否已写入数据 !!!")
                    else:
                        latest_record = recent_data[0]
                        success_count = 0
                        for field, node in self.opc_nodes.items():
                            val_str = latest_record.get(field)
                            if val_str is not None:
                                try:
                                    val_float = float(val_str)
                                    await node.write_value(val_float)
                                    success_count += 1
                                except ValueError:
                                    logger.warning(f"字段 {field} 的值 '{val_str}' 无法转换为浮点数")
                                except Exception as e:
                                    logger.error(f"写入节点 {field} 失败: {e}")

                        if success_count == 0:
                            logger.warning(
                                f"!!! [警告] 读到了记录，但没有成功写入任何点位。记录内容: {latest_record} !!!")

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
