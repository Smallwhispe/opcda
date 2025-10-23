package org.example.export.vo.server;

import lombok.Data;

import java.util.Map;

@Data
public class WriteResult {
    private boolean success;
    private String error;
    private Map<String, Boolean> results;

    // getters and setters
}
