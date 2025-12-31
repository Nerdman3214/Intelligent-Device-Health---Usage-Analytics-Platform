package com.apple.telemetry.exception;

import java.util.Map;

/**
 * Thrown when request validation fails.
 * 
 * Apple principle: Validation failures are NOT internal errors.
 * They are client errors (4xx) with clear explanations.
 */
public class ValidationException extends RuntimeException {
    
    private final ErrorCode errorCode;
    private final Map<String, Object> context;
    
    public ValidationException(String message, ErrorCode errorCode) {
        this(message, errorCode, Map.of());
    }
    
    public ValidationException(
        String message,
        ErrorCode errorCode,
        Map<String, Object> context
    ) {
        super(message);
        this.errorCode = errorCode;
        this.context = context;
    }
    
    public ErrorCode getErrorCode() {
        return errorCode;
    }
    
    public Map<String, Object> getContext() {
        return context;
    }
}
