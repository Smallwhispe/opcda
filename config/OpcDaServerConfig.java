package org.example.utils;

import lombok.Data;
import org.springframework.beans.factory.annotation.Value;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableAsync;

@Slf4j
@Configuration
@EnableAsync
@Data
public class OpcDaServerConfig {

    //服务器名称
    @Value("${opc.server.name}")
    private String serverName;

    @Value("${opc.server.progid}")
    private String progId;

    //读取方式
    @Value("${opc.server.read}")
    private String read;

    //更新频率
    @Value("${opc.server.rate}")
    private int updateRate;

    //位号
    @Value("${opc.server.clsid}")
    private String clsid;
}