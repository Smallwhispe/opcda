import logging
from flask import Blueprint, request, jsonify
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


@dataViewBp.route('/dataCollect', methods=['GET'])
def dataCollect():
    """
    数据查询接口：简化版。
    """
    try:
        # 1. 获取 URL 查询参数
        data = request.args.to_dict()

        # 检查是否有参数（保持原逻辑）
        if not data and not request.args:
            return jsonify(ResultEntityMethod.buildFailedResult(
                ErrorCode.NO_PARAM.get_code(),
                "缺少必要的查询参数",
                None)), 400

        # 2. Pydantic 校验 (只用于请求参数)
        dataCollectReq = DataCollectReq.model_validate(data)

        # 3. 调用业务逻辑
        # result_data 是 ResultEntity 实例
        result_data = DataCollectService.data_collect(dataCollectReq)

        # ----------------------------------------------------
        # 4. 响应处理：最简化逻辑
        # ----------------------------------------------------
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

@dataViewBp.route('/dataCollectByPage', methods=['GET'])
def dataCollectByPage():
    try:
        if not request.args:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.NO_REQUEST.get_code(), ErrorCode.NO_REQUEST.get_msg(),None)), 400
        data = request.get_json()
        if not data:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.NO_PARAM.get_code(), ErrorCode.NO_PARAM.get_msg(), None)), 400
        dataCollectReq = DataCollectReq.model_validate(data)

        # 调用业务逻辑
        result_data = DataCollectService.data_collect_by_page(dataCollectReq)

        if result_data.success:
            # 构建响应
            response = DataCollectRes(
                total=result_data.data.total,
                dataList=result_data.data.dataList,
            )
            return jsonify(ResultEntityMethod.buildSuccessResult(ErrorCode.SUCCESS.get_code(), ErrorCode.SUCCESS.get_msg(),response)), 200
        else:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.SERVICE_FAILURE.get_code(), ErrorCode.SERVICE_FAILURE.get_msg(),None)), 500
    except ValidationError as e:
        return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.VALID_FAILURE.get_code(), ErrorCode.VALID_FAILURE.get_msg(), None)), 400
    except Exception as e:
        logger.error("[opc数据获取] - opc数据获取未知失败", e)
        return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.FAILURE.get_code(), ErrorCode.FAILURE.get_msg(), None)), 500

@dataViewBp.route('/dataExport', methods=['POST'])
def dataExport():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.NO_PARAM.get_code(), ErrorCode.NO_PARAM.get_msg(), None)), 400
        dataExportReq = DataExportReq.model_validate(data)

        # 调用业务逻辑
        result_data = DataViewService.dataExport(dataExportReq)

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

@dataViewBp.route('/qrQuery', methods=['GET'])
def QrQuery():
    try:
        if not request.args:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.NO_REQUEST.get_code(), ErrorCode.NO_REQUEST.get_msg(),None)), 400
        data = request.get_json()
        if not data:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.NO_PARAM.get_code(), ErrorCode.NO_PARAM.get_msg(), None)), 400
        qrQueryReq = QrQueryReq.model_validate(data)

        # 调用业务逻辑
        result_data = DataViewService.qrQuery(qrQueryReq)

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
        if not request.args:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.NO_REQUEST.get_code(), ErrorCode.NO_REQUEST.get_msg(),None)), 400
        data = request.get_json()
        if not data:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.NO_PARAM.get_code(), ErrorCode.NO_PARAM.get_msg(), None)), 400
        qrExportReq = QrExportReq.model_validate(data)

        # 调用业务逻辑
        result_data = DataViewService.qrExport(qrExportReq)

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