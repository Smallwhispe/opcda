import logging
import threading
import sys  # <--- 新增：系统路径处理
import os  # <--- 新增：文件路径处理
import webview  # <--- 新增：桌面窗口库
from dotenv import load_dotenv  # <--- 新增：加载环境变量

from config.logging_config import setup_logging
from flask import Flask, send_from_directory, jsonify  # <--- 修改：增加 send_from_directory
from flask_cors import CORS
from routes.DataBlueprint import dataViewBp
from services.Manager import Manager
from services.predict_result import init_predict_db
from services.repository_sqlite import init_opc_db
import sys
import ctypes


# --- 1. 配置加载逻辑 (必须在最前面) ---
def load_user_config():
    """
    加载 .env 配置文件。
    如果是打包后的 exe，优先去 exe 所在目录寻找 .env
    """
    if getattr(sys, 'frozen', False):
        # 打包环境：sys.executable 是 exe 的绝对路径
        base_path = os.path.dirname(sys.executable)
    else:
        # 开发环境
        base_path = os.path.abspath(".")

    env_path = os.path.join(base_path, '.env')

    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"[System] 外部配置文件已加载: {env_path}")
    else:
        print(f"[System] 未找到外部配置文件: {env_path}，使用默认设置")


# 初始化配置（在导入其他依赖环境变量的模块前执行）
load_user_config()


# --- 2. 静态资源路径逻辑 ---
def get_static_folder():
    """获取前端构建文件(dist)的路径"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 解压后的临时目录
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, 'dist')


manager_stop_event = threading.Event()


def create_app():
    setup_logging(log_dir="logs", basename="myflask.log", level=logging.INFO)

    # --- 修改：指定静态文件夹路径 ---
    app = Flask(__name__, static_folder=get_static_folder())


    # CORS 配置 (打包为桌面应用后其实不再受跨域限制，但保留也没问题)
    cors = CORS(app, resources={r"/*": {"origins": "*", "supports_credentials": True,
                                        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE", "HEAD",
                                                    "PATCH"],
                                        "allow_headers": ["Content-Type", "Authorization"]}})

    app.register_blueprint(dataViewBp)

    # 数据库初始化
    init_opc_db()
    init_predict_db()

    # --- 新增：Vue 前端路由托管 ---
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        """
        处理前端静态文件和Vue路由
        """
        if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        else:
            # 所有的前端路由（如 /dashboard）都返回 index.html
            return send_from_directory(app.static_folder, 'index.html')

    return app


def run_manager():
    """在单独线程中运行Manager"""
    manager = Manager()
    try:
        manager.start()
        logging.info("Manager服务启动成功")
        # 保持Manager运行
        manager_stop_event.wait()
    except Exception as e:
        logging.error(f"Manager运行异常: {e}")
    finally:
        if manager.running:
            manager.shutdown()
        logging.info("Manager服务已关闭")


if __name__ == '__main__':
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    log = logging.getLogger('werkzeug')
    # log.setLevel(logging.WARNING)

    # 1. 启动后台业务线程
    manager_thread = threading.Thread(target=run_manager, daemon=True)
    manager_thread.start()
    logging.info("Manager服务线程已启动")

    try:
        # 2. 初始化 Flask 应用
        logging.info("正在初始化 Flask 应用...")
        app = create_app()

        # 3. 启动 PyWebView 窗口
        # 注意：这里不再调用 app.run()，而是将 app 传给 webview
        logging.info("启动桌面窗口...")

        window = webview.create_window(
            '智能控制系统',  # 窗口标题
            app,  # Flask app 实例
            width=1280,
            height=800,
            resizable=True
        )

        # 4. 开始运行 (这将阻塞主线程，直到窗口关闭)
        # debug=True 允许在窗口中右键检查元素（生产环境建议设为 False）
        webview.start(debug=False)

    except KeyboardInterrupt:
        logging.info("接收到中断信号")
        manager_stop_event.set()
    except Exception as e:
        logging.error(f"应用运行异常: {e}")
        manager_stop_event.set()  # 发生异常也确保后台线程停止
    finally:
        # 5. 清理资源
        logging.info("窗口已关闭，正在停止后台服务...")
        manager_stop_event.set()

        manager_thread.join(timeout=1.0)  # 稍微增加超时时间
        if manager_thread.is_alive():
            logging.warning("Manager线程强制退出")
        else:
            logging.info("Manager线程已正常结束")

        logging.info("应用完全退出")