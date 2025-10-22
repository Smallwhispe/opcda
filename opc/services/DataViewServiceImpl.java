package org.example.service.impl;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import lombok.extern.slf4j.Slf4j;
import org.example.export.req.DataCollectReq;
import org.example.export.req.DataExportReq;
import org.example.export.res.DataCollectRes;
import org.example.export.res.DataExportRes;
import org.example.export.vo.DataView;
import org.example.mapper.DataViewMapper;
import org.example.service.DataViewService;
import org.example.utils.LogUtil;
import org.example.utils.ResultEntity;
import org.example.utils.enums.ErrorCode;
import org.slf4j.Logger;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

@Slf4j
@Service
public class DataViewServiceImpl extends ServiceImpl<DataViewMapper,DataView> implements DataViewService {
    private static final Logger logger = LogUtil.getLogger(DataViewServiceImpl.class);

    @Autowired
    private DataViewMapper dataViewMapper;

    @Override
    public ResultEntity<DataCollectRes> dataCollect(DataCollectReq request) {
        ResultEntity<DataCollectRes> res = new ResultEntity<>();
        try {
            //queryWrapper为空，因为是全部列表
            List<DataView> resultList = this.dataViewMapper.selectList(null);
            DataCollectRes dataCollectRes = new DataCollectRes();
            dataCollectRes.setDataList(resultList);
            dataCollectRes.setTotal(resultList.size());
            res = ResultEntity.buildSuccessResult(ErrorCode.SUCCESS.getCode(), ErrorCode.SUCCESS.getMsg(), dataCollectRes);
        } catch (Exception e) {
            logger.error("[opc查询] - 数据库查询未知失败", e);
            res = ResultEntity.buildFailedResult(ErrorCode.FAILURE.getCode(), ErrorCode.FAILURE.getMsg(), null);
        }
        return res;
    }

    //数据进行展示
    @Override
    public ResultEntity<DataCollectRes> dataCollectByPage(DataCollectReq request) {
        ResultEntity<DataCollectRes> res = new ResultEntity<>();
        try {
            Page<DataView> dataViewPage = new Page<>(request.getPage(),request.getSize());
            //queryWrapper为空，因为是全部列表
            Page<DataView> resultPage = this.dataViewMapper.selectPage(dataViewPage, null);
            List<DataView> dataViewList = new ArrayList<>(resultPage.getRecords());
            DataCollectRes dataCollectRes = new DataCollectRes();
            dataCollectRes.setDataList(dataViewList);
            dataCollectRes.setTotal(resultPage.getTotal());
            res = ResultEntity.buildSuccessResult(ErrorCode.SUCCESS.getCode(), ErrorCode.SUCCESS.getMsg(), dataCollectRes);
        } catch (Exception e) {
            logger.error("[opc查询] - 数据库查询未知失败", e);
            res = ResultEntity.buildFailedResult(ErrorCode.FAILURE.getCode(), ErrorCode.FAILURE.getMsg(), null);
        }
        return res;
    }

    //数据进行导出
    @Override
    public ResultEntity<DataExportRes> dataExport(DataExportReq request) {
        ResultEntity<DataExportRes> res = new ResultEntity<>();
        try {
            //queryWrapper为空，因为是全部列表
            List<DataView> resultList = this.dataViewMapper.selectList(null);
            DataExportRes dataExportRes = new DataExportRes();
            dataExportRes.setDataList(resultList);
            dataExportRes.setTotal(resultList.size());
            res = ResultEntity.buildSuccessResult(ErrorCode.SUCCESS.getCode(), ErrorCode.SUCCESS.getMsg(), dataExportRes);
        } catch (Exception e) {
            logger.error("[opc查询] - 数据库查询未知失败", e);
            res = ResultEntity.buildFailedResult(ErrorCode.FAILURE.getCode(), ErrorCode.FAILURE.getMsg(), null);
        }
        return res;
    }
}
