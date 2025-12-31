package com.apple.telemetry.exception;

import java.util.Map;

/**
 * Thrown when analytics layer (Python) fails.
 * 
 * Apple principle: Distinguish between validation errors (client fault)
 * and system errors (our fault).
 * 
 * This is a system error (5xx) but with explicit categorization.
 */
public class AnalyticsException extends RuntimeException {
    
    private final ErrorCode errorCode;
    private final Map<String, Object> context;
    
    public AnalyticsException(String message, ErrorCode errorCode) {
        this(message, errorCode, Map.of());
    }
    
    public AnalyticsException(
        String message,
        ErrorCode errorCode,
        Map<String, Object> context
    ) {
        super(message);
        this.errorCode = errorCode;
        this.context = context;
    }
    
    public AnalyticsException(
        String message,
        ErrorCode errorCode,
        Throwable cause
    ) {
        this(message, errorCode, Map.of(), cause);
    }
    
    public AnalyticsException(
        String message,
        ErrorCode errorCode,
        Map<String, Object> context,
        Throwable cause
    ) {
        super(message, cause);
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
