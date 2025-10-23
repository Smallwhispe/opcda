package org.example.export.vo.server;

public class OpcItemDefinition {
    private String itemId;
    private String description;
    private String dataType;

    public OpcItemDefinition(String itemId, String description, String dataType) {
        this.itemId = itemId;
        this.description = description;
        this.dataType = dataType;
    }

    // getters and setters
}
