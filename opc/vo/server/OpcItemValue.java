package org.example.export.vo.server;

import lombok.Data;

import java.util.Date;

@Data
public class OpcItemValue {
    private Object value;
    private Date timestamp;
    private short quality;
    private short limitStatus;

    // getters and setters
}
