from flask import Flask, render_template, jsonify
from flask_cors import CORS  # <-- 添加CORS支持
from opc_connector import opc_client  # <-- 导入我们共享的客户端
import sys

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000"])
# 检查客户端是否成功初始化
if opc_client is None:
    print("警告: OPC 客户端未初始化。API 路由将失败。")

# -----------------------------------------------------------------
# 1. 从你的客户端脚本中复制所有标签定义
# -----------------------------------------------------------------
TAG_TEMP = 'Bucket Brigade.Real8'
TAG_PRESS = 'Bucket Brigade.Real4'
TAG_FLOW = 'Bucket Brigade.Int4'
TAG_CONC = 'Bucket Brigade.String'
TAG_QUALITY = 'Bucket Brigade.Bool'
TAG_ALARM_TEMP = 'Bucket Brigade.Byte'
TAG_ALARM_PRESS = 'Bucket Brigade.Word'
TAG_ALARM_CONC = 'Bucket Brigade.Short'

TAG_LIST_TO_READ = [
    TAG_TEMP, TAG_PRESS, TAG_FLOW, TAG_CONC,
    TAG_QUALITY, TAG_ALARM_TEMP, TAG_ALARM_PRESS, TAG_ALARM_CONC
]


# 路由 1: 主页
@app.route('/')
def index():
    """
    提供显示数据的前端 HTML 页面。
    """
    return render_template('index.html')


# 路由 2: API 端点 (供前端 JavaScript 调用)
@app.route('/get_opc_data')
def get_opc_data():
    """
    从 OPC 服务器读取数据并以 JSON 格式返回。
    这替换了你脚本中的 "while True" 循环。
    """
    if opc_client is None:
        return jsonify({"error": "OPC 客户端未初始化"}), 500

    try:
        # -----------------------------------------------------------------
        # 2. 这是你 "while True" 循环中的核心读取逻辑
        # -----------------------------------------------------------------
        read_data = opc_client.read(TAG_LIST_TO_READ)

        # -----------------------------------------------------------------
        # 3. 这是你 "while True" 循环中的字典转换逻辑
        #    我们将其转换为更适合 JSON 的格式
        # -----------------------------------------------------------------
        results = {}
        for tag_name, value, quality, timestamp in read_data:
            results[tag_name] = {
                "value": value,
                "quality": quality,
                "timestamp": timestamp
            }

        # 将完整的字典作为 JSON 发送给前端
        return jsonify(results)

    except Exception as e:
        # 如果 OPC 服务死掉或连接断开，会在这里捕获到异常
        print(f"API 错误: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':

    print("正在启动 Flask OPC DA Web 应用...")
    print("在浏览器中打开: http://127.0.0.1:5000")

    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False, threaded=False)