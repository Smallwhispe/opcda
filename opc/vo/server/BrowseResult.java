package org.example.export.vo.server;

import lombok.Data;

import java.util.List;

@Data
public class BrowseResult {
    private boolean success;
    private String error;
    private List<OpcItemDefinition> items;

    // getters and setters
}
