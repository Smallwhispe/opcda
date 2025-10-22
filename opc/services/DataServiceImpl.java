package org.example.service.impl;

import lombok.extern.slf4j.Slf4j;
import org.example.export.req.LimsQueryReq;
import org.example.export.req.ModelPredictReq;
import org.example.export.res.LimsQueryRes;
import org.example.export.res.ModelPredictRes;

import org.example.service.DataService;
import org.example.utils.LogUtil;
import org.example.utils.ResultEntity;
import org.slf4j.Logger;
import org.springframework.stereotype.Service;

@Slf4j
@Service
public class DataServiceImpl implements DataService {
    private static final Logger logger = LogUtil.getLogger(DataServiceImpl.class);

    //获取信息并传送给模型预测模块
    @Override
    public ResultEntity<ModelPredictRes> modelPredict(ModelPredictReq request) {
        return null;
    }

    //lims
    @Override
    public ResultEntity<LimsQueryRes> limsQuery(LimsQueryReq request) {
        return null;
    }
}
