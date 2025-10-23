// OpcDaSimulatorController.java
package org.example.controller;

import lombok.extern.slf4j.Slf4j;
import org.example.service.OpcDaRequestService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;


import java.util.*;
@Slf4j
@RestController
@RequestMapping("/opc/server")
@CrossOrigin(origins = "*")
public class OpcController {

    @Autowired
    private OpcDaRequestService requestService;

    /**
     * 模拟OPC客户端连接
     */
    @PostMapping("/connect")
    public Object connect(@RequestParam String clientId,
                          @RequestParam(defaultValue = "Spring.OPC.DA.Simulator.1") String progId) {
        return requestService.handleConnectRequest(clientId, progId);
    }

    /**
     * 模拟浏览请求
     */
    @GetMapping("/browse")
    public Object browse(@RequestParam String clientId,
                         @RequestParam(defaultValue = "") String branch) {
        return requestService.handleBrowseRequest(clientId, branch);
    }

    /**
     * 模拟同步读取
     */
    @PostMapping("/read")
    public Object syncRead(@RequestParam String clientId,
                           @RequestBody List<String> itemIds) {
        return requestService.handleSyncRead(clientId, itemIds);
    }

    /**
     * 模拟同步写入
     */
    @PostMapping("/write")
    public Object syncWrite(@RequestParam String clientId,
                            @RequestBody Map<String, Object> writeValues) {
        return requestService.handleSyncWrite(clientId, writeValues);
    }

    /**
     * 模拟订阅请求
     */
    @PostMapping("/subscribe")
    public Object subscribe(@RequestParam String clientId,
                            @RequestParam int updateRate,
                            @RequestBody List<String> itemIds) {
        return requestService.handleSubscribe(clientId, itemIds, updateRate);
    }

    /**
     * 模拟取消订阅
     */
    @PostMapping("/unsubscribe")
    public Object unsubscribe(@RequestParam String clientId) {
        return Collections.singletonMap("success", requestService.handleUnsubscribe(clientId));
    }

    /**
     * 获取服务器状态
     */
    @GetMapping("/status")
    public Object getStatus() {
        return requestService.getActiveClients();
    }

    /**
     * 健康检查
     */
    @GetMapping("/health")
    public String health() {
        return "OPC DA Simulator is running!";
    }
}