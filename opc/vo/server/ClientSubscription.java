package org.example.export.vo.server;

import java.util.Date;
import java.util.List;

// 客户端订阅信息
public class ClientSubscription {
    private String clientId;
    private List<String> itemIds;
    private int updateRate;
    private Date createdTime;

    public ClientSubscription(String clientId, List<String> itemIds, int updateRate) {
        this.clientId = clientId;
        this.itemIds = itemIds;
        this.updateRate = updateRate;
        this.createdTime = new Date();
    }

    // getters and setters
}