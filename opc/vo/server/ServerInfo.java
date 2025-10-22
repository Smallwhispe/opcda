package org.example.export.vo.server;

import lombok.Data;

import java.util.List;

// 数据模型类
@Data
public class ServerInfo {
    private String serverName;
    private String serverVersion;
    private String vendorInfo;
    private int serverState;
    private List<String> supportedInterfaces;

    // getters and setters
}
