import logging
import time
from typing import Dict, List, Any

import requests

from models.PredictResult import PredictResult
from services.predict_result import insert_predict_record
from services.repository_sqlite import get_every_four_pick_thirty
from services.time_utils import dt_to_ts
from vo.ResultEntity import ResultEntityMethod, ResultEntity
from vo.req import ModelPredictReq
from config.Config import Config
from vo.res import ModelPredictRes

logger = logging.getLogger(__name__)
class ModelService:
    @staticmethod
    def model_ip_port_route(request: ModelPredictReq, ip: str, port: str, route: str) -> ResultEntity:
        try:
            url = f"http://{ip}:{port}/{route}"
            response = requests.post(
                url,
                json=request.__dict__,  # 把对象转换为 JSON
                timeout=5
            )
            result = response.json()
            # 将查询结果转换为字典列表
            model_predict_res = {'time': result['time'], 'result': result['result']}
            return ResultEntityMethod.buildSuccessResult(data=model_predict_res)
        except Exception:
            logger.exception("[opc数据导出] - opc数据导出未知异常")
            return ResultEntityMethod.buildFailedResult(message="模型调用失败")

    @staticmethod
    def model_predict_test() -> ResultEntity:
        try:
            sampled = get_every_four_pick_thirty()
            # 给每个 request 添加一个 inputs 字段（如果你 ModelPredictReq 有明确字段可以换掉）
            pressure_inputs = [
    {"ARG2_TI1352A_PV": 165.1853333, "ARG2_TI1329_PV": 54.94228745, "ARG2_TI1328_PV": 117.1959763, "ARG2_PIC1306_PV": 0.882691741, "ARG2_TI1338_PV": 39.38499069, "ARG2_FIC1308_PV": 243.243454, "ARG2_FIC1309_PV": 123.9666519, "ARG2_FIC1310_PV": 62.16095734, "ARG2_FIC1303_PV": 80.86535645, "ARG2_FIC1311_PV": 105.2577057, "ARG2_TI1330_PV": 40.18133163},
    {"ARG2_TI1352A_PV": 165.1853333, "ARG2_TI1329_PV": 54.94228745, "ARG2_TI1328_PV": 117.1959763, "ARG2_PIC1306_PV": 0.882691741, "ARG2_TI1338_PV": 39.38499069, "ARG2_FIC1308_PV": 245.0996857, "ARG2_FIC1309_PV": 122.8337555, "ARG2_FIC1310_PV": 61.8852005, "ARG2_FIC1303_PV": 79.46071625, "ARG2_FIC1311_PV": 107.1070938, "ARG2_TI1330_PV": 40.18133163},
    {"ARG2_TI1352A_PV": 165.149353, "ARG2_TI1329_PV": 55.00192261, "ARG2_TI1328_PV": 116.9217987, "ARG2_PIC1306_PV": 0.883848667, "ARG2_TI1338_PV": 39.24444199, "ARG2_FIC1308_PV": 242.2067719, "ARG2_FIC1309_PV": 123.5773468, "ARG2_FIC1310_PV": 62.02975464, "ARG2_FIC1303_PV": 78.99900818, "ARG2_FIC1311_PV": 109.6832581, "ARG2_TI1330_PV": 40.05932236},
    {"ARG2_TI1352A_PV": 165.149353, "ARG2_TI1329_PV": 55.00192261, "ARG2_TI1328_PV": 116.9217987, "ARG2_PIC1306_PV": 0.883982182, "ARG2_TI1338_PV": 39.24444199, "ARG2_FIC1308_PV": 237.8760986, "ARG2_FIC1309_PV": 123.5063629, "ARG2_FIC1310_PV": 62.22767639, "ARG2_FIC1303_PV": 79.21613312, "ARG2_FIC1311_PV": 109.6910629, "ARG2_TI1330_PV": 40.05932236},
    {"ARG2_TI1352A_PV": 165.1257935, "ARG2_TI1329_PV": 54.94356918, "ARG2_TI1328_PV": 117.208786, "ARG2_PIC1306_PV": 0.883448243, "ARG2_TI1338_PV": 39.18083954, "ARG2_FIC1308_PV": 238.1123962, "ARG2_FIC1309_PV": 125.1079407, "ARG2_FIC1310_PV": 62.1565094, "ARG2_FIC1303_PV": 80.46588135, "ARG2_FIC1311_PV": 107.8327942, "ARG2_TI1330_PV": 40.09264374},
    {"ARG2_TI1352A_PV": 165.1228333, "ARG2_TI1329_PV": 54.93972397, "ARG2_TI1328_PV": 117.1719055, "ARG2_PIC1306_PV": 0.884471655, "ARG2_TI1338_PV": 39.27367783, "ARG2_FIC1308_PV": 245.1147766, "ARG2_FIC1309_PV": 123.8143158, "ARG2_FIC1310_PV": 61.97860336, "ARG2_FIC1303_PV": 81.27519989, "ARG2_FIC1311_PV": 106.48909, "ARG2_TI1330_PV": 40.062397},
    {"ARG2_TI1352A_PV": 165.1427765, "ARG2_TI1329_PV": 55.05578232, "ARG2_TI1328_PV": 117.0853348, "ARG2_PIC1306_PV": 0.884827733, "ARG2_TI1338_PV": 39.2808609, "ARG2_FIC1308_PV": 242.0339355, "ARG2_FIC1309_PV": 123.4181671, "ARG2_FIC1310_PV": 62.18097305, "ARG2_FIC1303_PV": 79.91438293, "ARG2_FIC1311_PV": 108.9739075, "ARG2_TI1330_PV": 40.06598663},
    {"ARG2_TI1352A_PV": 165.1383209, "ARG2_TI1329_PV": 55.01218033, "ARG2_TI1328_PV": 117.1879501, "ARG2_PIC1306_PV": 0.884694219, "ARG2_TI1338_PV": 39.13108063, "ARG2_FIC1308_PV": 236.9189911, "ARG2_FIC1309_PV": 125.5952606, "ARG2_FIC1310_PV": 62.15429306, "ARG2_FIC1303_PV": 79.29006958, "ARG2_FIC1311_PV": 109.8305435, "ARG2_TI1330_PV": 39.99575043},
    {"ARG2_TI1352A_PV": 165.1358185, "ARG2_TI1329_PV": 54.97819901, "ARG2_TI1328_PV": 117.349884, "ARG2_PIC1306_PV": 0.883715153, "ARG2_TI1338_PV": 39.20700073, "ARG2_FIC1308_PV": 241.4611359, "ARG2_FIC1309_PV": 122.8371582, "ARG2_FIC1310_PV": 62.16318512, "ARG2_FIC1303_PV": 81.18074799, "ARG2_FIC1311_PV": 106.1235352, "ARG2_TI1330_PV": 40.06496048},
    {"ARG2_TI1352A_PV": 165.1513519, "ARG2_TI1329_PV": 55.08399582, "ARG2_TI1328_PV": 117.3290405, "ARG2_PIC1306_PV": 0.884560704, "ARG2_TI1338_PV": 39.3029213, "ARG2_FIC1308_PV": 240.271347, "ARG2_FIC1309_PV": 125.1944351, "ARG2_FIC1310_PV": 61.98527908, "ARG2_FIC1303_PV": 81.01316071, "ARG2_FIC1311_PV": 104.3180008, "ARG2_TI1330_PV": 40.02804947},
    {"ARG2_TI1352A_PV": 165.2104187, "ARG2_TI1329_PV": 55.30265045, "ARG2_TI1328_PV": 117.0949631, "ARG2_PIC1306_PV": 0.884471655, "ARG2_TI1338_PV": 39.26393509, "ARG2_FIC1308_PV": 242.5162354, "ARG2_FIC1309_PV": 123.2920151, "ARG2_FIC1310_PV": 62.05866241, "ARG2_FIC1303_PV": 79.19470978, "ARG2_FIC1311_PV": 106.4466095, "ARG2_TI1330_PV": 40.0870018},
    {"ARG2_TI1352A_PV": 165.1812439, "ARG2_TI1329_PV": 55.36484528, "ARG2_TI1328_PV": 117.026001, "ARG2_PIC1306_PV": 0.883982182, "ARG2_TI1338_PV": 39.1054306, "ARG2_FIC1308_PV": 235.7843018, "ARG2_FIC1309_PV": 124.4068451, "ARG2_FIC1310_PV": 62.02975464, "ARG2_FIC1303_PV": 79.19226074, "ARG2_FIC1311_PV": 108.7831039, "ARG2_TI1330_PV": 40.00856781},
    {"ARG2_TI1352A_PV": 165.0952759, "ARG2_TI1329_PV": 55.04616165, "ARG2_TI1328_PV": 117.1927567, "ARG2_PIC1306_PV": 0.884160161, "ARG2_TI1338_PV": 39.18186188, "ARG2_FIC1308_PV": 238.7661591, "ARG2_FIC1309_PV": 123.1958694, "ARG2_FIC1310_PV": 61.98972321, "ARG2_FIC1303_PV": 79.44897461, "ARG2_FIC1311_PV": 109.994873, "ARG2_TI1330_PV": 40.00959396},
    {"ARG2_TI1352A_PV": 165.1206818, "ARG2_TI1329_PV": 54.87111282, "ARG2_TI1328_PV": 117.3290405, "ARG2_PIC1306_PV": 0.883848667, "ARG2_TI1338_PV": 39.22135925, "ARG2_FIC1308_PV": 237.0875092, "ARG2_FIC1309_PV": 125.0165405, "ARG2_FIC1310_PV": 61.97415543, "ARG2_FIC1303_PV": 80.74589539, "ARG2_FIC1311_PV": 105.7458725, "ARG2_TI1330_PV": 39.97063065},
    {"ARG2_TI1352A_PV": 165.1796722, "ARG2_TI1329_PV": 55.1256752, "ARG2_TI1328_PV": 117.2953796, "ARG2_PIC1306_PV": 0.884160161, "ARG2_TI1338_PV": 39.24906158, "ARG2_FIC1308_PV": 244.6882629, "ARG2_FIC1309_PV": 123.7365494, "ARG2_FIC1310_PV": 61.849617, "ARG2_FIC1303_PV": 81.39768219, "ARG2_FIC1311_PV": 102.3694611, "ARG2_TI1330_PV": 40.0147171},
    {"ARG2_TI1352A_PV": 165.2263794, "ARG2_TI1329_PV": 55.12695694, "ARG2_TI1328_PV": 117.0837326, "ARG2_PIC1306_PV": 0.883715153, "ARG2_TI1338_PV": 39.15314102, "ARG2_FIC1308_PV": 245.8745575, "ARG2_FIC1309_PV": 125.4896011, "ARG2_FIC1310_PV": 61.75399017, "ARG2_FIC1303_PV": 78.91344452, "ARG2_FIC1311_PV": 107.0189285, "ARG2_TI1330_PV": 39.95883942},
    {"ARG2_TI1352A_PV": 165.2263794, "ARG2_TI1329_PV": 55.12695694, "ARG2_TI1328_PV": 117.0837326, "ARG2_PIC1306_PV": 0.883715153, "ARG2_TI1338_PV": 39.15314102, "ARG2_FIC1308_PV": 233.4578247, "ARG2_FIC1309_PV": 123.0781174, "ARG2_FIC1310_PV": 61.84517288, "ARG2_FIC1303_PV": 78.81791687, "ARG2_FIC1311_PV": 110.3781967, "ARG2_TI1330_PV": 39.95883942},
    {"ARG2_TI1352A_PV": 165.1738892, "ARG2_TI1329_PV": 54.9480629, "ARG2_TI1328_PV": 117.0548859, "ARG2_PIC1306_PV": 0.884204686, "ARG2_TI1338_PV": 39.18083954, "ARG2_FIC1308_PV": 233.6348877, "ARG2_FIC1309_PV": 125.6759491, "ARG2_FIC1310_PV": 61.77400208, "ARG2_FIC1303_PV": 79.6986618, "ARG2_FIC1311_PV": 110.8288498, "ARG2_TI1330_PV": 40.00087357},
    {"ARG2_TI1352A_PV": 165.1540375, "ARG2_TI1329_PV": 55.10259247, "ARG2_TI1328_PV": 117.4765701, "ARG2_PIC1306_PV": 0.884516239, "ARG2_TI1338_PV": 39.23726273, "ARG2_FIC1308_PV": 243.9329987, "ARG2_FIC1309_PV": 123.5029068, "ARG2_FIC1310_PV": 61.862957, "ARG2_FIC1303_PV": 82.17700195, "ARG2_FIC1311_PV": 103.9466553, "ARG2_TI1330_PV": 40.04445267},
    {"ARG2_TI1352A_PV": 165.1717224, "ARG2_TI1329_PV": 55.10964203, "ARG2_TI1328_PV": 117.3643188, "ARG2_PIC1306_PV": 0.884071171, "ARG2_TI1338_PV": 39.10235977, "ARG2_FIC1308_PV": 243.5648804, "ARG2_FIC1309_PV": 125.1951599, "ARG2_FIC1310_PV": 61.71395874, "ARG2_FIC1303_PV": 80.58223724, "ARG2_FIC1311_PV": 103.0457382, "ARG2_TI1330_PV": 39.95217133},
    {"ARG2_TI1352A_PV": 165.1717224, "ARG2_TI1329_PV": 55.10964203, "ARG2_TI1328_PV": 117.3643188, "ARG2_PIC1306_PV": 0.884738684, "ARG2_TI1338_PV": 39.10235977, "ARG2_FIC1308_PV": 238.0821686, "ARG2_FIC1309_PV": 122.9911423, "ARG2_FIC1310_PV": 61.8985405, "ARG2_FIC1303_PV": 79.41086578, "ARG2_FIC1311_PV": 108.0400467, "ARG2_TI1330_PV": 39.95217133},
    {"ARG2_TI1352A_PV": 165.0573578, "ARG2_TI1329_PV": 55.40460205, "ARG2_TI1328_PV": 117.2424698, "ARG2_PIC1306_PV": 0.884605169, "ARG2_TI1338_PV": 39.09004211, "ARG2_FIC1308_PV": 235.4665375, "ARG2_FIC1309_PV": 125.3996811, "ARG2_FIC1310_PV": 61.72507858, "ARG2_FIC1303_PV": 79.78404236, "ARG2_FIC1311_PV": 109.2069321, "ARG2_TI1330_PV": 40.01574326},
    {"ARG2_TI1352A_PV": 165.0936279, "ARG2_TI1329_PV": 55.2321167, "ARG2_TI1328_PV": 117.3434753, "ARG2_PIC1306_PV": 0.884872198, "ARG2_TI1338_PV": 39.15262604, "ARG2_FIC1308_PV": 240.2620392, "ARG2_FIC1309_PV": 123.4455109, "ARG2_FIC1310_PV": 61.76288223, "ARG2_FIC1303_PV": 81.19271851, "ARG2_FIC1311_PV": 104.4105835, "ARG2_TI1330_PV": 39.95730209},
    {"ARG2_TI1352A_PV": 165.1338654, "ARG2_TI1329_PV": 55.16222763, "ARG2_TI1328_PV": 117.324234, "ARG2_PIC1306_PV": 0.884471655, "ARG2_TI1338_PV": 39.07619476, "ARG2_FIC1308_PV": 248.1434479, "ARG2_FIC1309_PV": 125.5898514, "ARG2_FIC1310_PV": 61.62500381, "ARG2_FIC1303_PV": 80.21601868, "ARG2_FIC1311_PV": 103.329155, "ARG2_TI1330_PV": 39.97473145},
    {"ARG2_TI1352A_PV": 165.1696472, "ARG2_TI1329_PV": 55.04232025, "ARG2_TI1328_PV": 117.1526947, "ARG2_PIC1306_PV": 0.884827733, "ARG2_TI1338_PV": 39.04234314, "ARG2_FIC1308_PV": 244.0059662, "ARG2_FIC1309_PV": 123.4369888, "ARG2_FIC1310_PV": 61.61166382, "ARG2_FIC1303_PV": 79.03797913, "ARG2_FIC1311_PV": 108.6474915, "ARG2_TI1330_PV": 39.9198761},
    {"ARG2_TI1352A_PV": 165.0701752, "ARG2_TI1329_PV": 55.02436447, "ARG2_TI1328_PV": 117.0019608, "ARG2_PIC1306_PV": 0.885183692, "ARG2_TI1338_PV": 39.11671829, "ARG2_FIC1308_PV": 240.4466553, "ARG2_FIC1309_PV": 125.6534805, "ARG2_FIC1310_PV": 61.44709778, "ARG2_FIC1303_PV": 78.92909241, "ARG2_FIC1311_PV": 110.766571, "ARG2_TI1330_PV": 39.92654037},
    {"ARG2_TI1352A_PV": 165.0646667, "ARG2_TI1329_PV": 55.08015442, "ARG2_TI1328_PV": 117.2168121, "ARG2_PIC1306_PV": 0.885317206, "ARG2_TI1338_PV": 39.0669632, "ARG2_FIC1308_PV": 240.2002106, "ARG2_FIC1309_PV": 122.8550339, "ARG2_FIC1310_PV": 61.59831238, "ARG2_FIC1303_PV": 79.75370026, "ARG2_FIC1311_PV": 110.8861542, "ARG2_TI1330_PV": 39.89783096},
    {"ARG2_TI1352A_PV": 165.0041962, "ARG2_TI1329_PV": 55.06412125, "ARG2_TI1328_PV": 117.38517, "ARG2_PIC1306_PV": 0.885139227, "ARG2_TI1338_PV": 39.13210678, "ARG2_FIC1308_PV": 239.9091797, "ARG2_FIC1309_PV": 123.8883591, "ARG2_FIC1310_PV": 61.71395874, "ARG2_FIC1303_PV": 80.85535431, "ARG2_FIC1311_PV": 107.6674652, "ARG2_TI1330_PV": 39.89167786},
    {"ARG2_TI1352A_PV": 165.0198822, "ARG2_TI1329_PV": 55.03718567, "ARG2_TI1328_PV": 117.2136078, "ARG2_PIC1306_PV": 0.885495126, "ARG2_TI1338_PV": 39.2377739, "ARG2_FIC1308_PV": 248.2899933, "ARG2_FIC1309_PV": 125.215126, "ARG2_FIC1310_PV": 61.71840286, "ARG2_FIC1303_PV": 81.30760956, "ARG2_FIC1311_PV": 106.2994232, "ARG2_TI1330_PV": 39.85527802},
    {"ARG2_TI1352A_PV": 165.020462, "ARG2_TI1329_PV": 55.08335495, "ARG2_TI1328_PV": 117.1093826, "ARG2_PIC1306_PV": 0.88580668, "ARG2_TI1338_PV": 39.17775726, "ARG2_FIC1308_PV": 245.6782837, "ARG2_FIC1309_PV": 122.5986404, "ARG2_FIC1310_PV": 61.84738922, "ARG2_FIC1303_PV": 79.38751984, "ARG2_FIC1311_PV": 109.2413635, "ARG2_TI1330_PV": 39.86963654},
    {"ARG2_TI1352A_PV": 164.9863129, "ARG2_TI1329_PV": 55.1019516, "ARG2_TI1328_PV": 116.9891281, "ARG2_PIC1306_PV": 0.885539651, "ARG2_TI1338_PV": 39.1054306, "ARG2_FIC1308_PV": 233.9246368, "ARG2_FIC1309_PV": 125.7707596, "ARG2_FIC1310_PV": 61.63389587, "ARG2_FIC1303_PV": 78.4860611, "ARG2_FIC1311_PV": 111.3698273, "ARG2_TI1330_PV": 39.74967194},
    {"ARG2_TI1352A_PV": 164.9863129, "ARG2_TI1329_PV": 55.1019516, "ARG2_TI1328_PV": 116.9891281, "ARG2_PIC1306_PV": 0.885361612, "ARG2_TI1338_PV": 39.1054306, "ARG2_FIC1308_PV": 239.2580566, "ARG2_FIC1309_PV": 123.1365204, "ARG2_FIC1310_PV": 61.88742065, "ARG2_FIC1303_PV": 79.0190506, "ARG2_FIC1311_PV": 111.8251724, "ARG2_TI1330_PV": 39.74967194},
    {"ARG2_TI1352A_PV": 164.9576569, "ARG2_TI1329_PV": 54.93138885, "ARG2_TI1328_PV": 117.3723297, "ARG2_PIC1306_PV": 0.885450721, "ARG2_TI1338_PV": 39.33318329, "ARG2_FIC1308_PV": 239.0404358, "ARG2_FIC1309_PV": 124.5904083, "ARG2_FIC1310_PV": 61.8985405, "ARG2_FIC1303_PV": 80.50786591, "ARG2_FIC1311_PV": 109.2642288, "ARG2_TI1330_PV": 39.85373688},
    {"ARG2_TI1352A_PV": 164.9994507, "ARG2_TI1329_PV": 54.96408844, "ARG2_TI1328_PV": 117.455719, "ARG2_PIC1306_PV": 0.885762155, "ARG2_TI1338_PV": 39.37011337, "ARG2_FIC1308_PV": 242.6172333, "ARG2_FIC1309_PV": 123.4192963, "ARG2_FIC1310_PV": 61.7806778, "ARG2_FIC1303_PV": 81.32243347, "ARG2_FIC1311_PV": 104.3364258, "ARG2_TI1330_PV": 39.86758804},
    {"ARG2_TI1352A_PV": 165.0783081, "ARG2_TI1329_PV": 55.06412125, "ARG2_TI1328_PV": 117.3258362, "ARG2_PIC1306_PV": 0.885317206, "ARG2_TI1338_PV": 39.16135025, "ARG2_FIC1308_PV": 241.0895386, "ARG2_FIC1309_PV": 123.0246887, "ARG2_FIC1310_PV": 61.64279175, "ARG2_FIC1303_PV": 80.55314636, "ARG2_FIC1311_PV": 103.3304214, "ARG2_TI1330_PV": 39.83631134},
    {"ARG2_TI1352A_PV": 165.0502167, "ARG2_TI1329_PV": 55.19620895, "ARG2_TI1328_PV": 117.1430588, "ARG2_PIC1306_PV": 0.884738684, "ARG2_TI1338_PV": 39.09619904, "ARG2_FIC1308_PV": 232.1345978, "ARG2_FIC1309_PV": 125.5508194, "ARG2_FIC1310_PV": 61.55606461, "ARG2_FIC1303_PV": 79.26834106, "ARG2_FIC1311_PV": 106.8830566, "ARG2_TI1330_PV": 39.91526413},
    {"ARG2_TI1352A_PV": 164.9975281, "ARG2_TI1329_PV": 55.22314453, "ARG2_TI1328_PV": 117.2344589, "ARG2_PIC1306_PV": 0.885139227, "ARG2_TI1338_PV": 39.26290894, "ARG2_FIC1308_PV": 232.9978943, "ARG2_FIC1309_PV": 123.0004349, "ARG2_FIC1310_PV": 61.5916481, "ARG2_FIC1303_PV": 79.86720276, "ARG2_FIC1311_PV": 106.3720551, "ARG2_TI1330_PV": 39.97883224}
]
            c5_inputs = pressure_inputs
            bing_xi_inputs = []
            gan_dian_inputs = []
            # 将 sampled 里的每条记录按字段放到对应模型的输入列表中
            # for rec in sampled:
            #     pressure_inputs.append({"temperature": rec.get("temperature")})
            #     c5_inputs.append({"flow": rec.get("flow")})
            #     bing_xi_inputs.append({"pressure": rec.get("pressure")})
            #     gan_dian_inputs.append({"concentration": rec.get("concentration")})
            latest_ts = int(time.time())
            if sampled:
                latest_ts = sampled[-1].get("ts")  # 最后一条就是最新（升序）
            # 构造模型预测请求值
            request_pressure = ModelPredictReq(produce=pressure_inputs, endTime=latest_ts)
            # request_c5 = ModelPredictReq(produce=c5_inputs, endTime=latest_ts)
            # request_bing_xi = ModelPredictReq(produce=bing_xi_inputs, endTime=latest_ts)
            # request_gan_dian = ModelPredictReq(produce=gan_dian_inputs, endTime=latest_ts)
            # 分别调用四个模型
            result_pressure = ModelService.model_ip_port_route(request_pressure, Config.IP, Config.PORT, "predict")
            # result_c5 = ModelService.model_ip_port_route(request_c5, Config.IP, Config.PORT, "")
            # result_bing_xi = ModelService.model_ip_port_route(request_bing_xi, Config.IP, Config.PORT, "")
            # result_gan_dian = ModelService.model_ip_port_route(request_gan_dian, Config.IP, Config.PORT, "")
            logger.info(result_pressure.data['result'])
            predict_result = PredictResult(
                pressure=str(result_pressure.data['result']) if result_pressure.success else None,  # ← 注意替换字段
                # c5=result_c5.data['result'] if result_c5.success else None,
                # bing_xi=result_bing_xi.data['result'] if result_bing_xi.success else None,
                # gan_dian=result_gan_dian.data['result'] if result_gan_dian.success else None,
            )
            insert_predict_record({
                "time": dt_to_ts(predict_result.time),
                "pressure": predict_result.pressure,
                "c5": predict_result.c5,
                "bing_xi": predict_result.bing_xi,
                "gan_dian": predict_result.gan_dian,
            })
            model_predict_res = ModelPredictRes(
                time=predict_result.time,
                result={
                    "pressure": predict_result.pressure,
                    "c5": predict_result.c5,
                    "bing_xi": predict_result.bing_xi,
                    "gan_dian": predict_result.gan_dian,
                }
            )
            return ResultEntityMethod.buildSuccessResult(data=model_predict_res)
        except Exception:
            logger.error("[opc模型调用] - 模型调用未知错误", exc_info=True)
            return ResultEntityMethod.buildFailedResult(message="模型调用未知错误")

    @staticmethod
    def model_predict() -> ResultEntity:
        try:
            sampled = get_every_four_pick_thirty()
            # 给每个 request 添加一个 inputs 字段（如果你 ModelPredictReq 有明确字段可以换掉）
            pressure_inputs = []
            c5_inputs = []
            bing_xi_inputs = []
            gan_dian_inputs = []
            # 将 sampled 里的每条记录按字段放到对应模型的输入列表中
            for rec in sampled:
                pressure_inputs = ModelService.build_pressure_inputs(rec)
                c5_inputs = ModelService.build_c5_inputs(rec)
                bing_xi_inputs = ModelService.build_bing_xi_inputs(rec)
                gan_dian_inputs = ModelService.build_gan_dian_inputs(rec)
            latest_ts = int(time.time())
            if sampled:
                latest_ts = sampled[-1].get("ts")  # 最后一条就是最新（升序）
            # 构造模型预测请求值
            request_pressure = ModelPredictReq(produce=pressure_inputs, endTime=latest_ts)
            request_c5 = ModelPredictReq(produce=c5_inputs, endTime=latest_ts)
            request_bing_xi = ModelPredictReq(produce=bing_xi_inputs, endTime=latest_ts)
            request_gan_dian = ModelPredictReq(produce=gan_dian_inputs, endTime=latest_ts)
            # 分别调用四个模型
            result_pressure = ModelService.model_ip_port_route(request_pressure, Config.IP, Config.PORT, "")
            result_c5 = ModelService.model_ip_port_route(request_c5, Config.IP, Config.PORT, "")
            result_bing_xi = ModelService.model_ip_port_route(request_bing_xi, Config.IP, Config.PORT, "")
            result_gan_dian = ModelService.model_ip_port_route(request_gan_dian, Config.IP, Config.PORT, "")
            predict_result = PredictResult(
                pressure=str(result_pressure.data['result']) if result_pressure.success else None,  # ← 注意替换字段
                c5=str(result_c5.data['result']) if result_c5.success else None,
                bing_xi=str(result_bing_xi.data['result']) if result_bing_xi.success else None,
                gan_dian=str(result_gan_dian.data['result']) if result_gan_dian.success else None,
            )
            insert_predict_record({
                "time": dt_to_ts(predict_result.time),
                "pressure": predict_result.pressure,
                "c5": predict_result.c5,
                "bing_xi": predict_result.bing_xi,
                "gan_dian": predict_result.gan_dian,
            })
            model_predict_res = ModelPredictRes(
                time=predict_result.time,
                result={
                    "pressure": predict_result.pressure,
                    "c5": predict_result.c5,
                    "bing_xi": predict_result.bing_xi,
                    "gan_dian": predict_result.gan_dian,
                }
            )
            return ResultEntityMethod.buildSuccessResult(data=model_predict_res)
        except Exception:
            logger.error("[opc模型调用] - 模型调用未知错误", exc_info=True)
            return ResultEntityMethod.buildFailedResult(message="模型调用未知错误")

    @staticmethod
    def build_pressure_inputs(rec: Dict[str, Any]) -> List[Dict[str, Any]]:
        pressure_inputs = [{
            "ARG2_TI1352A_PV": rec.get("ARG2_TI1352A_PV"),
            "ARG2_TI1329_PV": rec.get("ARG2_TI1329_PV"),
            "ARG2_TI1328_PV": rec.get("ARG2_TI1328_PV"),
            "ARG2_PIC1306_PV": rec.get("ARG2_PIC1306_PV"),
            "ARG2_TI1338_PV": rec.get("ARG2_TI1338_PV"),
            "ARG2_FIC1308_PV": rec.get("ARG2_FIC1308_PV"),
            "ARG2_FIC1309_PV": rec.get("ARG2_FIC1309_PV"),
            "ARG2_FIC1310_PV": rec.get("ARG2_FIC1310_PV"),
            "ARG2_FIC1303_PV": rec.get("ARG2_FIC1303_PV"),
            "ARG2_FIC1311_PV": rec.get("ARG2_FIC1311_PV"),
            "ARG2_TI1330_PV": rec.get("ARG2_TI1330_PV"),
        }]
        return pressure_inputs

    @staticmethod
    def build_c5_inputs(rec: Dict[str, Any]) -> List[Dict[str, Any]]:
        c5_inputs = [{
            "ARG2_TI1352A_PV": rec.get("ARG2_TI1352A_PV"),
            "ARG2_TI1329_PV": rec.get("ARG2_TI1329_PV"),
            "ARG2_TI1328_PV": rec.get("ARG2_TI1328_PV"),
            "ARG2_PIC1306_PV": rec.get("ARG2_PIC1306_PV"),
            "ARG2_TI1338_PV": rec.get("ARG2_TI1338_PV"),
            "ARG2_FIC1308_PV": rec.get("ARG2_FIC1308_PV"),
            "ARG2_FIC1309_PV": rec.get("ARG2_FIC1309_PV"),
            "ARG2_FIC1310_PV": rec.get("ARG2_FIC1310_PV"),
            "ARG2_FIC1303_PV": rec.get("ARG2_FIC1303_PV"),
            "ARG2_FIC1311_PV": rec.get("ARG2_FIC1311_PV"),
            "ARG2_TI1330_PV": rec.get("ARG2_TI1330_PV"),
        }]
        return c5_inputs

    @staticmethod
    def build_bing_xi_inputs(rec: Dict[str, Any]) -> List[Dict[str, Any]]:
        bing_xi_inputs = [{
            "ARG2_TIC1345_PV": rec.get("ARG2_TIC1345_PV"),
            "ARG2_FIC1303_PV": rec.get("ARG2_FIC1303_PV"),
            "ARG2_FIC1210_PV": rec.get("ARG2_FIC1210_PV"),
            "ARG2_FIC1307_PV": rec.get("ARG2_FIC1307_PV"),
            "ARG2_FIC1306_PV": rec.get("ARG2_FIC1306_PV"),
            "ARG2_FIC1305_PV": rec.get("ARG2_FIC1305_PV"),
            "ARG2_FIC1304_PV": rec.get("ARG2_FIC1304_PV"),
            "ARG2_PI1304_PV": rec.get("ARG2_PI1304_PV"),
            "ARG2_TI1308_PV": rec.get("ARG2_TI1308_PV"),
            "ARG2_TI1310_PV": rec.get("ARG2_TI1310_PV"),
            "ARG2_TI1312_PV": rec.get("ARG2_TI1312_PV"),
            "ARG2_TI1314_PV": rec.get("ARG2_TI1314_PV"),
            "ARG2_FI1314_PV": rec.get("ARG2_FI1314_PV"),
            "ARG2_TI1341_PV": rec.get("ARG2_TI1341_PV"),
            "ARG2_TI1347_PV": rec.get("ARG2_TI1347_PV"),
            "ARG2_TI1304_PV": rec.get("ARG2_TI1304_PV"),
            "ARG2_TIC1101_PV": rec.get("ARG2_TIC1101_PV"),
            "ARG2_TIC1103_PV": rec.get("ARG2_TIC1103_PV"),
            "ARG2_TI1233C_PV": rec.get("ARG2_TI1233C_PV"),
            "ARG2_TI1306_PV": rec.get("ARG2_TI1306_PV"),
        }]
        return bing_xi_inputs

    @staticmethod
    def build_gan_dian_inputs(rec: Dict[str, Any]) -> List[Dict[str, Any]]:
        gan_dian_inputs = [{
            "ARG2_TIC1201B_PV": rec.get("ARG2_TIC1201B_PV"),
            "ARG2_PI1204_PV": rec.get("ARG2_PI1204_PV"),
            "ARG2_FIC1214_PV": rec.get("ARG2_FIC1214_PV"),
            "ARG2_FI1160_PV": rec.get("ARG2_FI1160_PV"),
            "ARG2_FIC1210_PV": rec.get("ARG2_FIC1210_PV"),
            "ARG2_FIC1203_PV": rec.get("ARG2_FIC1203_PV"),
            "ARG2_FI1405_PV": rec.get("ARG2_FI1405_PV"),
            "ARG2_FI1314_PV": rec.get("ARG2_FI1314_PV"),
            "ARG2_FI1312_PV": rec.get("ARG2_FI1312_PV"),
            "ARG2_PI1308_PV": rec.get("ARG2_PI1308_PV"),
            "ARG2_TI1304_PV": rec.get("ARG2_TI1304_PV"),
        }]
        return gan_dian_inputs