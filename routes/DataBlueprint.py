import logging
import os

from flask import Blueprint, request, jsonify, send_from_directory, current_app
from pydantic import ValidationError

from services.DataCollectService import DataCollectService
from services.DataViewService import DataViewService
from vo.QrExport import QrExportReq, QrExportRes
from vo.ResultEntity import ResultEntityMethod, ErrorCode
from vo.req import ModelPredictReq, DataCollectReq, DataExportReq, QrQueryReq
from vo.res import ModelPredictRes, DataCollectRes, DataExportRes, QrQueryRes
from opc_connector import opc_client  # <-- 导入我们共享的客户端
dataViewBp = Blueprint('dataViewBp', __name__, url_prefix='/data')

logger = logging.getLogger()
@dataViewBp.route('/dataGet', methods=['GET'])
def dataGet():
    """
    从 OPC 服务器读取数据并以 JSON 格式返回。
    """
    TAG_TEMP = 'Bucket Brigade.Real8'
    TAG_PRESS = 'Bucket Brigade.Real4'
    TAG_FLOW = 'Bucket Brigade.Int4'
    TAG_CONC = 'Bucket Brigade.String'
    TAG_QUALITY = 'Bucket Brigade.Bool'

    TAG_LIST_TO_READ = [
        TAG_TEMP, TAG_PRESS, TAG_FLOW, TAG_CONC, TAG_QUALITY
    ]
    if opc_client is None:
        return jsonify({"error": "OPC 客户端未初始化"}), 500

    try:
        read_data = opc_client.read(TAG_LIST_TO_READ)
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

@dataViewBp.route('/dataCollect', methods=['POST'])
def dataCollect():
    """
    数据查询接口：简化版。
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.NO_PARAM.get_code(), ErrorCode.NO_PARAM.get_msg(),None)), 400
        dataCollectReq = DataCollectReq.model_validate(data)

        # 调用业务逻辑
        result_data = DataCollectService.data_collect(dataCollectReq)

        if result_data.success:

            # 直接使用业务层返回的数据字典作为构造 DataCollectRes 的输入
            # 注意：这里 ResultEntityMethod.buildSuccessResult 必须能处理 DataCollectRes 实例

            # 重新实例化 DataCollectRes，同时解决 Attribute Error
            response_data = DataCollectRes(
                total=result_data.data['total'],
                dataList=result_data.data['dataList'],
            )

            return jsonify(ResultEntityMethod.buildSuccessResult(
                ErrorCode.SUCCESS.get_code(),
                ErrorCode.SUCCESS.get_msg(),
                # 关键：手动转换为字典，解决 JSON 序列化问题
                response_data.model_dump()
            )), 200
        else:
            # 业务失败直接返回 ResultEntity 的 JSON 封装
            return jsonify(result_data.data.model_dump()), 500

    except ValidationError as e:
        # Pydantic 校验失败
        return jsonify(ResultEntityMethod.buildFailedResult(
            ErrorCode.VALID_FAILURE.get_code(),
            f"请求参数格式校验失败",
            None)), 400

    except Exception as e:
        # 未知服务器错误
        logger.error("[opc数据获取] - opc数据获取未知失败: %s", e, exc_info=True)
        return jsonify(ResultEntityMethod.buildFailedResult(
            ErrorCode.FAILURE.get_code(),
            "服务器内部错误",
            None)), 500

@dataViewBp.route('/dataCollectByPage', methods=['POST'])
def dataCollectByPage():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.NO_PARAM.get_code(), ErrorCode.NO_PARAM.get_msg(), None)), 400
        dataCollectReq = DataCollectReq.model_validate(data)

        # 调用业务逻辑
        result_data = DataCollectService.data_collect_by_page(dataCollectReq)

        if result_data.success:
            # 构建响应
            response = DataCollectRes(
                total=result_data.data['total'],
                dataList=result_data.data['dataList'],
            )
            return jsonify(ResultEntityMethod.buildSuccessResult(ErrorCode.SUCCESS.get_code(), ErrorCode.SUCCESS.get_msg(),response.model_dump())), 200
        else:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.SERVICE_FAILURE.get_code(), ErrorCode.SERVICE_FAILURE.get_msg(),None)), 500
    except ValidationError as e:
        return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.VALID_FAILURE.get_code(), ErrorCode.VALID_FAILURE.get_msg(), None)), 400
    except Exception as e:
        logger.error("[opc数据获取] - opc数据获取未知失败", e)
        return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.FAILURE.get_code(), ErrorCode.FAILURE.get_msg(), None)), 500

@dataViewBp.route('/dataPreview', methods=['POST'])
def dataPreview():
    try:
        logger.info("Received data preview request with args: %s", request.args)
        data = request.get_json(silent=True)
        if not data:
            return jsonify(
                ResultEntityMethod.buildFailedResult(ErrorCode.NO_PARAM.get_code(), ErrorCode.NO_PARAM.get_msg(),
                                                     None)), 400

        # 复用 DataExportReq，因为筛选条件（日期、类型）是一样的
        dataExportReq = DataExportReq.model_validate(data)

        # 1. 调用业务逻辑 (变为 data_preview)
        result_data = DataViewService.data_preview(dataExportReq)

        if result_data.success:
            # 2. 构建响应
            # 注意：这里不再使用 DataExportRes，因为预览不需要 fileName 和 filePath
            # 如果你有定义 DataPreviewRes (Pydantic Model)，可以在这里使用
            response_payload = {
                "total": result_data.data['total'],
                "dataList": result_data.data['dataList']
            }

            return jsonify(ResultEntityMethod.buildSuccessResult(
                ErrorCode.SUCCESS.get_code(),
                ErrorCode.SUCCESS.get_msg(),
                response_payload
            )), 200
        else:
            return jsonify(ResultEntityMethod.buildFailedResult(
                ErrorCode.SERVICE_FAILURE.get_code(),
                ErrorCode.SERVICE_FAILURE.get_msg(),
                None
            )), 500

    except ValidationError as e:
        return jsonify(
            ResultEntityMethod.buildFailedResult(ErrorCode.VALID_FAILURE.get_code(), ErrorCode.VALID_FAILURE.get_msg(),
                                                 None)), 400
    except Exception as e:
        logger.error("[opc数据预览] - opc数据预览未知失败", e)
        return jsonify(
            ResultEntityMethod.buildFailedResult(ErrorCode.FAILURE.get_code(), ErrorCode.FAILURE.get_msg(), None)), 500

@dataViewBp.route('/dataExport', methods=['POST'])
def dataExport():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.NO_PARAM.get_code(), ErrorCode.NO_PARAM.get_msg(), None)), 400
        dataExportReq = DataExportReq.model_validate(data)

        # 调用业务逻辑
        result_data = DataViewService.data_export(dataExportReq)

        if result_data.success:
            # 构建响应
            response = DataExportRes(
                total=result_data.data['total'],
                dataList=result_data.data['dataList'],
                fileName=result_data.data['fileName'],
                filePath=result_data.data['filePath'],
            )
            return jsonify(ResultEntityMethod.buildSuccessResult(ErrorCode.SUCCESS.get_code(), ErrorCode.SUCCESS.get_msg(),response.model_dump())), 200
        else:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.SERVICE_FAILURE.get_code(), ErrorCode.SERVICE_FAILURE.get_msg(),None)), 500
    except ValidationError as e:
        return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.VALID_FAILURE.get_code(), ErrorCode.VALID_FAILURE.get_msg(), None)), 400
    except Exception as e:
        logger.error("[opc数据导出] - opc数据导出未知失败", e)
        return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.FAILURE.get_code(), ErrorCode.FAILURE.get_msg(), None)), 500


@dataViewBp.route('/download', methods=['GET'])
def download_file():
    """
    安全地从 'export' 目录下载文件。
    """

    # ----------------------------------------------------
    # !!! 关键安全修复:
    # 永远不要接受客户端传入的 'filePath' (绝对路径)。
    # 必须只接受 'fileName' (文件名)，然后在后端拼接安全路径。
    # ----------------------------------------------------

    # 1. 从 URL 参数中获取 *文件名*
    filename = request.args.get('fileName')

    if not filename:
        return jsonify({"error": "缺少 'fileName' 参数"}), 400

    # 2. 定义安全的文件目录
    #    我们使用从 DataViewService 导入的 EXPORT_DIR 常量
    #    并获取其相对于当前应用实例的绝对路径
    safe_directory = os.path.join(current_app.root_path, "export")

    logger.info(f"请求下载文件: {filename} 从目录: {safe_directory}")

    try:
        # 3. 使用 send_from_directory 安全地发送文件
        #    as_attachment=True 会触发浏览器的“另存为”对话框
        return send_from_directory(
            directory=safe_directory,
            path=filename,  # 注意：在 Flask 2.x+ 中，推荐使用 'path' 参数
            as_attachment=True
        )
    except FileNotFoundError:
        logger.error(f"文件未找到: {filename} in {safe_directory}")
        return jsonify({"error": "文件未找到或无法访问"}), 404
    except Exception as e:
        logger.error(f"[文件下载] - 未知失败: {e}", exc_info=True)
        return jsonify({"error": "服务器发送文件时出错"}), 500

@dataViewBp.route('/modelPredict', methods=['POST'])
def modelPredict():
    try:
        if not request.args:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.NOT_REQUEST.get_code(), ErrorCode.NOT_REQUEST.get_msg(),None)), 400
        data = request.get_json()
        if not data:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.NO_PARAM.get_code(), ErrorCode.NO_PARAM.get_msg(), None)), 400
        modelPredictReq = ModelPredictReq.model_validate(data)

        # 调用业务逻辑
        result_data = DataViewService.modelPredict(modelPredictReq)

        if result_data.success:
            # 构建响应
            response = ModelPredictRes(
                version=result_data['version'],
                startTime=result_data['startTime'],
                endTime=result_data['endTime'],
                produce=result_data['produce']
            )
            return jsonify(ResultEntityMethod.buildSuccessResult(ErrorCode.SUCCESS.get_code(), ErrorCode.SUCCESS.get_msg(),response)), 200
        else:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.SERVICE_FAILURE.get_code(), ErrorCode.SERVICE_FAILURE.get_msg(),None)), 500
    except ValidationError as e:
        return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.VALID_FAILURE.get_code(), ErrorCode.VALID_FAILURE.get_msg(), None)), 400
    except Exception as e:
        logger.error("[opc模型预测] - opc模型预测未知失败", e)
        return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.FAILURE.get_code(), ErrorCode.FAILURE.get_msg(), None)), 500

@dataViewBp.route('/qrQuery', methods=['POST'])
def qr_query():
    try:
        if not request.args:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.NO_REQUEST.get_code(), ErrorCode.NO_REQUEST.get_msg(),None)), 400
        data = request.get_json()
        if not data:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.NO_PARAM.get_code(), ErrorCode.NO_PARAM.get_msg(), None)), 400
        qrQueryReq = QrQueryReq.model_validate(data)

        # 调用业务逻辑
        result_data = DataViewService.qr_query(qrQueryReq)

        if result_data.success:
            # 构建响应
            response = QrQueryRes(
                message = result_data['message'],
                type = result_data['type']
            )
            return jsonify(ResultEntityMethod.buildSuccessResult(ErrorCode.SUCCESS.get_code(), ErrorCode.SUCCESS.get_msg(),response)), 200
        else:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.SERVICE_FAILURE.get_code(), ErrorCode.SERVICE_FAILURE.get_msg(),None)), 500
    except ValidationError as e:
        return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.VALID_FAILURE.get_code(), ErrorCode.VALID_FAILURE.get_msg(), None)), 400
    except Exception as e:
        logger.error("[opc qr查询] - opc lims查询未知失败", e)
        return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.FAILURE.get_code(), ErrorCode.FAILURE.get_msg(), None)), 500

@dataViewBp.route('/qrExport', methods=['GET'])
def QrExport():
    try:
        data = request.get_json()
        if not data:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.NO_PARAM.get_code(), ErrorCode.NO_PARAM.get_msg(), None)), 400
        qrExportReq = QrExportReq.model_validate(data)

        # 调用业务逻辑
        result_data = DataViewService.qr_export(qrExportReq)

        if result_data.success and result_data['data']:
            # 构建响应
            response = QrExportRes(
                exportSuccess = result_data['exportSuccess'],
            )
            return jsonify(ResultEntityMethod.buildSuccessResult(ErrorCode.SUCCESS.get_code(), ErrorCode.SUCCESS.get_msg(),response)), 200
        else:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.SERVICE_FAILURE.get_code(), ErrorCode.SERVICE_FAILURE.get_msg(),None)), 500
    except ValidationError as e:
        return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.VALID_FAILURE.get_code(), ErrorCode.VALID_FAILURE.get_msg(), None)), 400
    except Exception as e:
        logger.error("[opc qr查询] - opc lims查询未知失败", e)
        return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.FAILURE.get_code(), ErrorCode.FAILURE.get_msg(), None)), 500