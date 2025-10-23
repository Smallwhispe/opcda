package org.example.export.vo.server;

import lombok.Data;

import java.util.Map;

@Data
public class ReadResult {
    private boolean success;
    private String error;
    private Map<String, OpcItemValue> values;

    // getters and setters
}
