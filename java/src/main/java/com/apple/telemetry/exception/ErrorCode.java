package com.apple.telemetry.exception;

/**
 * Typed error codes for explicit error handling.
 * 
 * Apple principle: Never throw generic exceptions.
 * Every error must be categorizable and actionable.
 */
public enum ErrorCode {
    // Validation errors (4xx)
    INVALID_REQUEST("INVALID_REQUEST", 400),
    MISSING_REQUIRED_FIELD("MISSING_REQUIRED_FIELD", 400),
    INVALID_FIELD_VALUE("INVALID_FIELD_VALUE", 400),
    MALFORMED_JSON("MALFORMED_JSON", 400),
    DEVICE_ID_INVALID("DEVICE_ID_INVALID", 400),
    
    // Analytics errors (5xx - but explicit)
    ANALYTICS_UNAVAILABLE("ANALYTICS_UNAVAILABLE", 503),
    MODEL_INFERENCE_FAILED("MODEL_INFERENCE_FAILED", 500),
    FEATURE_EXTRACTION_FAILED("FEATURE_EXTRACTION_FAILED", 500),
    PYTHON_PROCESS_TIMEOUT("PYTHON_PROCESS_TIMEOUT", 504),
    PYTHON_PROCESS_CRASHED("PYTHON_PROCESS_CRASHED", 500),
    
    // Data errors
    INSUFFICIENT_TELEMETRY("INSUFFICIENT_TELEMETRY", 422),
    TELEMETRY_VALIDATION_FAILED("TELEMETRY_VALIDATION_FAILED", 422),
    
    // System errors
    INTERNAL_ERROR("INTERNAL_ERROR", 500);
    
    private final String code;
    private final int httpStatus;
    
    ErrorCode(String code, int httpStatus) {
        this.code = code;
        this.httpStatus = httpStatus;
    }
    
    public String getCode() {
        return code;
    }
    
    public int getHttpStatus() {
        return httpStatus;
    }
}
