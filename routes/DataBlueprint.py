import logging
from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from services.DataViewService import DataViewService
from vo.ResultEntity import ResultEntityMethod, ErrorCode
from vo.req import ModelPredictReq, DataCollectReq, DataExportReq, LimsQueryReq
from vo.res import ModelPredictRes, DataCollectRes, DataExportRes, LimsQueryRes

dataViewBp = Blueprint('dataViewBp', __name__, url_prefix='/data')

logger = logging.getLogger()

@dataViewBp.route('/modelPredict', methods=['POST'])
def modelPredict():
    try:
        data = request.get_json()

        if not data:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.NOT_PARAM.get_code(), ErrorCode.NOT_PARAM.get_msg(), None)), 400
        modelPredictReq = ModelPredictReq.model_validate(data)

        # 调用业务逻辑
        result_data = DataViewService.modelPredict(modelPredictReq)

        if not result_data.success:
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
    try:
        if not request.args:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.NOT_REQUEST.get_code(), ErrorCode.NOT_REQUEST.get_msg(),None)), 400
        data = request.get_json()
        if not data:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.NOT_PARAM.get_code(), ErrorCode.NOT_PARAM.get_msg(), None)), 400
        dataCollectReq = DataCollectReq.model_validate(data)

        # 调用业务逻辑
        result_data = DataViewService.dataCollect(dataCollectReq)

        if not result_data.success:
            # 构建响应
            response = DataCollectRes(
                total=result_data['total'],
                dataList=result_data['dataList'],
            )
            return jsonify(ResultEntityMethod.buildSuccessResult(ErrorCode.SUCCESS.get_code(), ErrorCode.SUCCESS.get_msg(),response)), 200
        else:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.SERVICE_FAILURE.get_code(), ErrorCode.SERVICE_FAILURE.get_msg(),None)), 500
    except ValidationError as e:
        return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.VALID_FAILURE.get_code(), ErrorCode.VALID_FAILURE.get_msg(), None)), 400
    except Exception as e:
        logger.error("[opc数据获取] - opc数据获取未知失败", e)
        return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.FAILURE.get_code(), ErrorCode.FAILURE.get_msg(), None)), 500

@dataViewBp.route('/dataCollectByPage', methods=['GET'])
def dataCollectByPage():
    try:
        if not request.args:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.NOT_PARAM.get_code(), ErrorCode.NOT_PARAM.get_msg(),None)), 400
        data = request.get_json()
        if not data:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.NOT_PARAM.get_code(), ErrorCode.NOT_PARAM.get_msg(), None)), 400
        dataCollectReq = DataCollectReq.model_validate(data)

        # 调用业务逻辑
        result_data = DataViewService.dataCollectByPage(dataCollectReq)

        if not result_data.success:
            # 构建响应
            response = DataCollectRes(
                total=result_data['total'],
                dataList=result_data['dataList'],
            )
            return jsonify(ResultEntityMethod.buildSuccessResult(ErrorCode.SUCCESS.get_code(), ErrorCode.SUCCESS.get_msg(),response)), 200
        else:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.SERVICE_FAILURE.get_code(), ErrorCode.SERVICE_FAILURE.get_msg(),None)), 500
    except ValidationError as e:
        return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.VALID_FAILURE.get_code(), ErrorCode.VALID_FAILURE.get_msg(), None)), 400
    except Exception as e:
        logger.error("[opc数据获取] - opc数据获取未知失败", e)
        return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.FAILURE.get_code(), ErrorCode.FAILURE.get_msg(), None)), 500

@dataViewBp.route('/dataExport', methods=['GET'])
def dataExport():
    try:
        if not request.args:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.NOT_PARAM.get_code(), ErrorCode.NOT_PARAM.get_msg(),None)), 400
        data = request.get_json()
        if not data:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.NOT_PARAM.get_code(), ErrorCode.NOT_PARAM.get_msg(), None)), 400
        dataExportReq = DataExportReq.model_validate(data)

        # 调用业务逻辑
        result_data = DataViewService.dataExport(dataExportReq)

        if not result_data.success:
            # 构建响应
            response = DataExportRes(
                total=result_data['total'],
                dataList=result_data['dataList'],
            )
            return jsonify(ResultEntityMethod.buildSuccessResult(ErrorCode.SUCCESS.get_code(), ErrorCode.SUCCESS.get_msg(),response)), 200
        else:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.SERVICE_FAILURE.get_code(), ErrorCode.SERVICE_FAILURE.get_msg(),None)), 500
    except ValidationError as e:
        return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.VALID_FAILURE.get_code(), ErrorCode.VALID_FAILURE.get_msg(), None)), 400
    except Exception as e:
        logger.error("[opc数据导出] - opc数据导出未知失败", e)
        return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.FAILURE.get_code(), ErrorCode.FAILURE.get_msg(), None)), 500

@dataViewBp.route('/lims', methods=['GET'])
def limsQuery():
    try:
        if not request.args:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.NOT_PARAM.get_code(), ErrorCode.NOT_PARAM.get_msg(),None)), 400
        data = request.get_json()
        if not data:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.NOT_PARAM.get_code(), ErrorCode.NOT_PARAM.get_msg(), None)), 400
        limsQueryReq = LimsQueryReq.model_validate(data)

        # 调用业务逻辑
        result_data = DataViewService.limsQuery(limsQueryReq)

        if not result_data.success:
            # 构建响应
            response = LimsQueryRes(
                #TODO 二维码查询
            )
            return jsonify(ResultEntityMethod.buildSuccessResult(ErrorCode.SUCCESS.get_code(), ErrorCode.SUCCESS.get_msg(),response)), 200
        else:
            return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.SERVICE_FAILURE.get_code(), ErrorCode.SERVICE_FAILURE.get_msg(),None)), 500
    except ValidationError as e:
        return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.VALID_FAILURE.get_code(), ErrorCode.VALID_FAILURE.get_msg(), None)), 400
    except Exception as e:
        logger.error("[opc lims查询] - opc lims查询未知失败", e)
        return jsonify(ResultEntityMethod.buildFailedResult(ErrorCode.FAILURE.get_code(), ErrorCode.FAILURE.get_msg(), None)), 500