import logging
import threading

# 导入Flask框架，用于创建Web应用；导入jsonify函数，用于生成JSON响应。
from flask import Flask
from flask_cors import CORS
from models.DataView import db
from routes.DataBlueprint import dataViewBp
from routes.OpcBlueprint import opcBp
from services.Manager import Manager

app = Flask(__name__)
# 创建一个Flask应用实例。`__name__`是当前模块的名称，Flask使用它来找到应用的位置，从而知道在哪里可以找到资源文件（如模板和静态文件）。

# 配置数据库URI
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:sfzhm130928@localhost:3306/data'
# 设置SQLAlchemy的配置选项，指定数据库URI。
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# 禁用SQLAlchemy的事件系统，减少不必要的内存开销。这是一个推荐的做法，特别是在生产环境中。

db.init_app(app)
with app.app_context():
    db.create_all()
# 使用Flask应用上下文来确保能够正确地与数据库交互。`db.create_all()`方法会检查数据库中是否存在所有定义的模型表，如果不存在，则根据模型定义创建它们。

cors = CORS(app, resources={r"/*": {"origins": "*", "supports_credentials": True,
                                                    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE", "HEAD", "PATCH"],
                                    "allow_headers": ["Content-Type", "Authorization"]}})

app.register_blueprint(dataViewBp)
app.register_blueprint(opcBp)

manager_stop_event = threading.Event()
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

    # 在后台线程中启动Manager
    manager_thread = threading.Thread(target=run_manager, daemon=True)
    manager_thread.start()
    logging.info("Manager服务线程已启动")

    try:
        # 启动Flask应用（主线程）
        logging.info("启动Flask应用...")
        app.run(debug=False, port=8181)
    except KeyboardInterrupt:
        logging.info("接收到中断信号")
        manager_stop_event.set()
    except Exception as e:
        logging.error(f"Flask应用异常: {e}")
    finally:
        # 设置停止事件
        manager_stop_event.set()

        # 等待Manager线程结束
        manager_thread.join(timeout=0.5)
        if manager_thread.is_alive():
            logging.warning("Manager线程未在超时时间内结束")
        else:
            logging.info("Manager线程已正常结束")

        logging.info("应用关闭完成")