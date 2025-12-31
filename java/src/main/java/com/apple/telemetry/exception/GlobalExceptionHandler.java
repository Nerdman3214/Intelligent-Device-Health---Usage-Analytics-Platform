package com.apple.telemetry.exception;

import jakarta.servlet.http.HttpServletRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.Map;
import java.util.UUID;

/**
 * Global exception handler for API.
 * 
 * Apple principle: Never let exceptions bubble to generic handlers.
 * Every exception must produce a structured, debuggable response.
 * 
 * This replaces Spring's default "Whitelabel Error Page" with
 * structured JSON errors.
 */
@RestControllerAdvice
public class GlobalExceptionHandler {
    
    private static final Logger logger = LoggerFactory.getLogger(GlobalExceptionHandler.class);
    
    /**
     * Handle validation exceptions (client errors)
     */
    @ExceptionHandler(ValidationException.class)
    public ResponseEntity<ApiError> handleValidationException(
        ValidationException ex,
        HttpServletRequest request
    ) {
        String requestId = generateRequestId();
        
        logger.warn(
            "Validation failed [requestId={}] [errorCode={}] [message={}] [context={}]",
            requestId,
            ex.getErrorCode().getCode(),
            ex.getMessage(),
            ex.getContext()
        );
        
        ApiError error = ApiError.from(
            ex.getErrorCode(),
            ex.getMessage(),
            requestId,
            request.getRequestURI(),
            ex.getContext()
        );
        
        return ResponseEntity
            .status(ex.getErrorCode().getHttpStatus())
            .body(error);
    }
    
    /**
     * Handle analytics exceptions (system errors)
     */
    @ExceptionHandler(AnalyticsException.class)
    public ResponseEntity<ApiError> handleAnalyticsException(
        AnalyticsException ex,
        HttpServletRequest request
    ) {
        String requestId = generateRequestId();
        
        logger.error(
            "Analytics failure [requestId={}] [errorCode={}] [message={}] [context={}]",
            requestId,
            ex.getErrorCode().getCode(),
            ex.getMessage(),
            ex.getContext(),
            ex
        );
        
        ApiError error = ApiError.from(
            ex.getErrorCode(),
            ex.getMessage(),
            requestId,
            request.getRequestURI(),
            ex.getContext()
        );
        
        return ResponseEntity
            .status(ex.getErrorCode().getHttpStatus())
            .body(error);
    }
    
    /**
     * Catch-all for unexpected exceptions
     * 
     * Apple principle: This should NEVER happen in production.
     * If it does, we log aggressively and return a safe error.
     */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiError> handleGenericException(
        Exception ex,
        HttpServletRequest request
    ) {
        String requestId = generateRequestId();
        
        logger.error(
            "UNEXPECTED EXCEPTION [requestId={}] [type={}] [message={}]",
            requestId,
            ex.getClass().getName(),
            ex.getMessage(),
            ex
        );
        
        ApiError error = ApiError.from(
            ErrorCode.INTERNAL_ERROR,
            "An unexpected error occurred. Please contact support with request ID: " + requestId,
            requestId,
            request.getRequestURI(),
            Map.of("exceptionType", ex.getClass().getName())
        );
        
        return ResponseEntity
            .status(HttpStatus.INTERNAL_SERVER_ERROR)
            .body(error);
    }
    
    private String generateRequestId() {
        return "req-" + UUID.randomUUID().toString().substring(0, 8);
    }
}
