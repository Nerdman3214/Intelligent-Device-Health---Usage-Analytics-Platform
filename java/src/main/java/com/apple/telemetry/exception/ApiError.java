package com.apple.telemetry.exception;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.Data;
import lombok.Builder;

import java.time.Instant;
import java.util.Map;

/**
 * Structured API error response.
 * 
 * Apple principle: Errors must be machine-readable and debuggable.
 * 
 * Never return:
 *   {"error": "Something went wrong"}
 * 
 * Always return:
 *   {
 *     "errorCode": "MODEL_INFERENCE_FAILED",
 *     "message": "Device health prediction failed",
 *     "timestamp": "2025-12-31T10:30:00Z",
 *     "requestId": "req-12345",
 *     "details": { "modelVersion": "v1.2.0", "deviceId": "ABC123" }
 *   }
 */
@Data
@Builder
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ApiError {
    
    private String errorCode;
    private String message;
    private Instant timestamp;
    private String requestId;
    private String path;
    private Map<String, Object> details;
    
    /**
     * Create error from exception context
     */
    public static ApiError from(
        ErrorCode errorCode,
        String message,
        String requestId,
        String path,
        Map<String, Object> details
    ) {
        return ApiError.builder()
            .errorCode(errorCode.getCode())
            .message(message)
            .timestamp(Instant.now())
            .requestId(requestId)
            .path(path)
            .details(details)
            .build();
    }
}
