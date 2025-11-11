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
def data_get():
    """
    从 OPC 服务器读取数据并以 JSON 格式返回。
    """
    tag_temp = 'Bucket Brigade.Real8'
    tag_press = 'Bucket Brigade.Real4'
    tag_flow = 'Bucket Brigade.Int4'
    tag_conc = 'Bucket Brigade.String'
    tag_quality = 'Bucket Brigade.Bool'

    tag_list_to_read = [
        tag_temp, tag_press, tag_flow, tag_conc, tag_quality
    ]
    if opc_client is None:
        return jsonify({"error": "OPC 客户端未初始化"}), 500

    try:
        read_data = opc_client.read(tag_list_to_read)
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
        logger.exception("[opc服务器连接] - 服务器连接未知异常")
        return jsonify({"error": str(e)}), 500
@dataViewBp.route('/modelPredict', methods=['POST'])
def model_predict():
    try:
        data = request.get_json()
        if not data:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.NO_PARAM.get_code(), ErrorCode.NO_PARAM.get_msg(), None)), 400
        model_predict_req = ModelPredictReq.model_validate(data)

        # 调用业务逻辑
        result_data = DataViewService.model_predict(model_predict_req)

        if result_data.success:
            # 构建响应
            response = ModelPredictRes(
                version=result_data.data['version'],
                startTime=result_data.data['startTime'],
                endTime=result_data.data['endTime'],
                produce=result_data.data['produce']
            )
            return jsonify(ResultEntityMethod.buildSuccessResult(ErrorCode.SUCCESS.get_code(), ErrorCode.SUCCESS.get_msg(),response.model_dump())), 200
        else:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.SERVICE_FAILURE.get_code(), ErrorCode.SERVICE_FAILURE.get_msg(),None)), 500
    except ValidationError as e:
        logger.error("[opc数据获取] - 参数传输错误:%s",e)
        return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.VALID_FAILURE.get_code(), ErrorCode.VALID_FAILURE.get_msg(), None)), 400
    except Exception:
        logger.exception("[opc模型预测] - opc模型预测未知失败")
        return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.FAILURE.get_code(), ErrorCode.FAILURE.get_msg(), None)), 500


@dataViewBp.route('/dataCollect', methods=['POST'])
def data_collect():
    """
    数据查询接口：简化版。
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.NO_PARAM.get_code(), ErrorCode.NO_PARAM.get_msg(), None)), 400
        data_collect_req = DataCollectReq.model_validate(data)

        # 调用业务逻辑
        # result_data 是 ResultEntity 实例
        result_data = DataCollectService.data_collect(data_collect_req)

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
            return jsonify(ResultEntityMethod.buildSuccessResult(ErrorCode.SUCCESS.get_code(),ErrorCode.SUCCESS.get_msg(),response_data.model_dump())), 200
        else:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.SERVICE_FAILURE.get_code(), ErrorCode.SERVICE_FAILURE.get_msg(),None)), 500
    except ValidationError as e:
        logger.error("[opc数据获取] - 参数传输错误:%s",e)
        return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.VALID_FAILURE.get_code(), ErrorCode.VALID_FAILURE.get_msg(),None)), 400
    except Exception:
        # 未知服务器错误
        logger.exception("[opc数据获取] - opc数据获取未知失败")
        return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.FAILURE.get_code(),ErrorCode.FAILURE.get_msg(),None)), 500

@dataViewBp.route('/dataCollectByPage', methods=['POST'])
def data_collect_by_page():
    try:
        if not request.args:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.NO_REQUEST.get_code(), ErrorCode.NO_REQUEST.get_msg(),None)), 400
        data = request.get_json()
        if not data:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.NO_PARAM.get_code(), ErrorCode.NO_PARAM.get_msg(), None)), 400
        data_collect_req = DataCollectReq.model_validate(data)

        # 调用业务逻辑
        result_data = DataCollectService.data_collect_by_page(data_collect_req)

        if result_data.success:
            # 构建响应
            response = DataCollectRes(
                total=result_data.data['total'],
                dataList=result_data.data['dataList'],
            )
            return jsonify(ResultEntityMethod.buildSuccessResult(ErrorCode.SUCCESS.get_code(), ErrorCode.SUCCESS.get_msg(),response)), 200
        else:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.SERVICE_FAILURE.get_code(), ErrorCode.SERVICE_FAILURE.get_msg(),None)), 500
    except ValidationError as e:
        logger.error("[opc数据获取] - 参数传输错误: %s",e)
        return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.VALID_FAILURE.get_code(), ErrorCode.VALID_FAILURE.get_msg(), None)), 400
    except Exception:
        logger.exception("[opc数据获取] - opc数据获取未知失败")
        return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.FAILURE.get_code(), ErrorCode.FAILURE.get_msg(), None)), 500

@dataViewBp.route('/dataExport', methods=['POST'])
def data_export():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.NO_REQUEST.get_code(), ErrorCode.NO_REQUEST.get_msg(), None)), 400
        data_export_req = DataExportReq.model_validate(data)

        # 调用业务逻辑
        result_data = DataViewService.data_export(data_export_req)

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
        logger.error("[opc数据导出] - 参数传输错误: %s",e)
        return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.VALID_FAILURE.get_code(), ErrorCode.VALID_FAILURE.get_msg(), None)), 400
    except Exception:
        logger.exception("[opc数据导出] - opc数据导出未知失败")
        return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.FAILURE.get_code(), ErrorCode.FAILURE.get_msg(), None)), 500

@dataViewBp.route('/qrQuery', methods=['POST'])
def qr_query():
    try:
        data = request.get_json()
        if not data:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.NO_REQUEST.get_code(), ErrorCode.NO_REQUEST.get_msg(),None)), 400
        qr_query_req = QrQueryReq.model_validate(data)

        # 调用业务逻辑
        result_data = DataViewService.qr_query(qr_query_req)

        if result_data.success:
            # 构建响应
            response = QrQueryRes(
                message = result_data.data['message'],
                type = result_data.data['type']
            )
            return jsonify(ResultEntityMethod.buildSuccessResult(ErrorCode.SUCCESS.get_code(), ErrorCode.SUCCESS.get_msg(),response)), 200
        else:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.SERVICE_FAILURE.get_code(), ErrorCode.SERVICE_FAILURE.get_msg(),None)), 500
    except ValidationError as e:
        logger.error("[opc qr查询] - opc lims查询参数传输错误: %s",e)
        return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.VALID_FAILURE.get_code(), ErrorCode.VALID_FAILURE.get_msg(), None)), 400
    except Exception:
        logger.exception("[opc qr查询] - opc lims查询未知失败")
        return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.FAILURE.get_code(), ErrorCode.FAILURE.get_msg(), None)), 500

@dataViewBp.route('/qrExport', methods=['POST'])
def qr_export():
    try:
        data = request.get_json()
        if not data:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.NO_REQUEST.get_code(), ErrorCode.NO_REQUEST.get_msg(),None)), 400
        qr_export_req = QrExportReq.model_validate(data)

        # 调用业务逻辑
        result_data = DataViewService.qr_export(qr_export_req)

        if result_data.success and result_data.data['data']:
            # 构建响应
            response = QrExportRes(
                exportSuccess = result_data.data['exportSuccess'],
            )
            return jsonify(ResultEntityMethod.buildSuccessResult(ErrorCode.SUCCESS.get_code(), ErrorCode.SUCCESS.get_msg(),response)), 200
        else:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.SERVICE_FAILURE.get_code(), ErrorCode.SERVICE_FAILURE.get_msg(),None)), 500
    except ValidationError as e:
        logger.error("[opc qr导出] - opc lims导出参数传输错误: %s",e)
        return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.VALID_FAILURE.get_code(), ErrorCode.VALID_FAILURE.get_msg(), None)), 400
    except Exception:
        logger.exception("[opc qr导出] - opc lims导出未知失败")
        return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.FAILURE.get_code(), ErrorCode.FAILURE.get_msg(), None)), 500