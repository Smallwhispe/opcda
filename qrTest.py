import logging
import os

import qrcode

from vo import ResultEntity
from vo.QrExport import QrExportReq, QrExportRes
from vo.ResultEntity import ResultEntityMethod

logger = logging.getLogger()
def qrExport(request: QrExportReq) -> ResultEntity:
    try:

        # 带自定义选项但无文本的二维码生成
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=request.size,
                border=request.border,
            )
            data = request.to_qr_data()  # 返回过滤后的字典
            qr.add_data(data)
            qr.make(fit=True)

            # 创建 export 目录（如果不存在）
            export_dir = "export"
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
                logger.info(f"[qr 导出] - 创建目录: {export_dir}")

            # 设置文件路径到 export 目录
            filename = request.filename
            unique_filename, filepath = get_unique_filename(export_dir, filename)

            # img可导出返回
            img = qr.make_image(fill_color=request.fill_color, back_color=request.back_color)
            img.save(filepath)
            logger.info(f"[qr 导出] - 二维码已成功生成并保存为: {filepath}")
            logger.info(f"[qr 导出] - 编码的数据: {data}")
            qrExportRes = QrExportRes(
                exportSuccess=True
            )
            return ResultEntityMethod.buildSuccessResult(data=qrExportRes)
        except Exception as e:
            logger.error("[qr 导出] - 生成二维码时出错:", e)
            ResultEntityMethod.buildFailedResult(message="opc qr导出生成二维码出错")
    except Exception as e:
        logger.error("[qr 导出] - opc qr导出未知失败", e)
        return ResultEntityMethod.buildFailedResult(message="opc qr导出未知失败")

def get_unique_filename(export_dir, filename):
    #生成唯一的文件名，如果存在相同文件名则自动递增数字

    # 分离文件名和扩展名
    name, ext = os.path.splitext(filename)
    counter = 1
    new_filename = filename
    filepath = os.path.join(export_dir, new_filename)

    # 检查文件是否存在，如果存在则递增数字
    while os.path.exists(filepath):
        new_filename = f"{name}_{counter}{ext}"
        filepath = os.path.join(export_dir, new_filename)
        counter += 1

    return new_filename, filepath

if __name__ == "__main__":
    request = QrExportReq(
        filename='example.jpg',
        size=4,
        border=4,
        fill_color="black",
        back_color="white",
        # 取样日期
        sampled_date="2025/10/29 0:00:00",
        # 取样点
        sampling_point="A2烟气",
        # 名称
        name="氧气",
        # 单位显示
        units_display=" %(体积分数)",
        # 格式化输入
        formatted_entry="4.82",
        # 取样时间
        drawtime="08:00:00",
    )
    qrExport(request)