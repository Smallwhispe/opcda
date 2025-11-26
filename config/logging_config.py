import logging
import os
import re
from logging.handlers import TimedRotatingFileHandler

def setup_logging(
    log_dir: str = "logs",
    basename: str = "app.log",
    level: int = logging.WARNING,   # 默认把文件日志等级设为 WARNING，可传 logging.ERROR / logging.INFO ...
    when: str = "midnight",
    backup_count: int = 7
):
    """
    初始化全局 logging。调用一次即可（在 Flask app 启动处）。
    - level: 要写入文件的最低日志级别（logger 会接收更低级别，但 handler 只输出 >= level 的）
    - when: 'midnight' 表示每天零点分割；也可用 'D' 等
    """

    # 确保目录存在
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, basename)

    # 获取 root logger 并先清空已有 handlers（避免重复输出）
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)  # 一般把 root 设为 DEBUG，然后由 handler 控制输出级别

    # 移除已存在 handler（通常在热重载/测试环境中需要）
    for h in root.handlers[:]:
        root.removeHandler(h)

    # 统一的日志格式
    fmt = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    formatter = logging.Formatter(fmt)

    # 控制台输出（可设需要的级别）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)  # 控制台输出 INFO 及以上
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    # 文件按天切分
    file_handler = TimedRotatingFileHandler(
        filename=log_path,
        when=when,
        interval=1,
        backupCount=backup_count,
        encoding="utf-8",
        utc=False  # 如果想按本地时间分割就用 False，按 UTC 用 True
    )
    # 让文件 handler 只记录指定级别及以上
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    # 设置文件名后缀格式（旋转后文件名示例： app.log.20251126 ）
    # 注意：直接赋值 suffix 常用且能工作，但不同 Python 版本行为略有差别。
    file_handler.suffix = "%Y%m%d"
    # 为了保证 can find old log files when using suffix，设置 extMatch（可选）
    file_handler.extMatch = re.compile(r"^\d{8}$")

    root.addHandler(file_handler)

    # 可选：返回 root，方便测试或进一步配置
    return root
