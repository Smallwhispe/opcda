package org.example.export.vo.server;

import lombok.Data;

import java.util.Map;

@Data
public class SubscribeResult {
    private boolean success;
    private String error;
    private int updateRate;
    private Map<String, OpcItemValue> initialValues;

    // getters and setters
}
