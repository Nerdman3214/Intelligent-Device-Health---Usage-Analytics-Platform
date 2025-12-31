package com.apple.telemetry.validation;

import com.apple.telemetry.exception.ErrorCode;
import com.apple.telemetry.exception.ValidationException;
import com.apple.telemetry.model.DeviceHealthRequest;
import com.apple.telemetry.model.TelemetryRecord;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Map;

/**
 * Request validation layer.
 * 
 * Apple principle: Validate twice, fail once.
 * 
 * Spring's @Valid handles basic validation.
 * This class handles business logic validation:
 * - Minimum telemetry samples required
 * - Timestamp sanity checks
 * - Device ID format
 * - Data consistency
 */
@Component
public class RequestValidator {
    
    private static final Logger logger = LoggerFactory.getLogger(RequestValidator.class);
    
    private static final int MIN_TELEMETRY_SAMPLES = 10;
    private static final int MAX_TELEMETRY_SAMPLES = 10000;
    private static final long MAX_TIMESTAMP_FUTURE_HOURS = 24;
    private static final long MAX_TIMESTAMP_PAST_DAYS = 365;
    
    /**
     * Validate device health analysis request.
     * 
     * Throws ValidationException with specific error codes if validation fails.
     */
    public void validateHealthRequest(DeviceHealthRequest request) {
        logger.debug("Validating health request for device: {}", request.getDeviceId());
        
        // Device ID validation
        validateDeviceId(request.getDeviceId());
        
        // Telemetry size validation
        int sampleCount = request.getTelemetry().size();
        if (sampleCount < MIN_TELEMETRY_SAMPLES) {
            throw new ValidationException(
                String.format(
                    "Insufficient telemetry data: %d samples provided, minimum %d required",
                    sampleCount,
                    MIN_TELEMETRY_SAMPLES
                ),
                ErrorCode.INSUFFICIENT_TELEMETRY,
                Map.of(
                    "providedSamples", sampleCount,
                    "requiredSamples", MIN_TELEMETRY_SAMPLES
                )
            );
        }
        
        if (sampleCount > MAX_TELEMETRY_SAMPLES) {
            throw new ValidationException(
                String.format(
                    "Too many telemetry samples: %d provided, maximum %d allowed",
                    sampleCount,
                    MAX_TELEMETRY_SAMPLES
                ),
                ErrorCode.INVALID_REQUEST,
                Map.of(
                    "providedSamples", sampleCount,
                    "maxSamples", MAX_TELEMETRY_SAMPLES
                )
            );
        }
        
        // Timestamp validation
        validateTimestamps(request.getTelemetry(), request.getDeviceId());
        
        logger.debug("Validation passed for device: {}", request.getDeviceId());
    }
    
    /**
     * Validate device ID format.
     * 
     * Apple principle: Device IDs should not be empty or just whitespace.
     */
    private void validateDeviceId(String deviceId) {
        if (deviceId == null || deviceId.trim().isEmpty()) {
            throw new ValidationException(
                "Device ID cannot be empty",
                ErrorCode.DEVICE_ID_INVALID
            );
        }
        
        if (deviceId.length() > 100) {
            throw new ValidationException(
                "Device ID too long (max 100 characters)",
                ErrorCode.DEVICE_ID_INVALID,
                Map.of("length", deviceId.length())
            );
        }
    }
    
    /**
     * Validate timestamps are reasonable.
     * 
     * Apple principle: Reject data from the future or ancient past.
     */
    private void validateTimestamps(java.util.List<TelemetryRecord> telemetry, String deviceId) {
        Instant now = Instant.now();
        Instant maxFuture = now.plus(MAX_TIMESTAMP_FUTURE_HOURS, ChronoUnit.HOURS);
        Instant maxPast = now.minus(MAX_TIMESTAMP_PAST_DAYS, ChronoUnit.DAYS);
        
        for (int i = 0; i < telemetry.size(); i++) {
            TelemetryRecord record = telemetry.get(i);
            Instant timestamp = record.getTimestamp();
            
            if (timestamp.isAfter(maxFuture)) {
                throw new ValidationException(
                    String.format(
                        "Telemetry timestamp is too far in the future at index %d",
                        i
                    ),
                    ErrorCode.TELEMETRY_VALIDATION_FAILED,
                    Map.of(
                        "index", i,
                        "timestamp", timestamp.toString(),
                        "maxFuture", maxFuture.toString()
                    )
                );
            }
            
            if (timestamp.isBefore(maxPast)) {
                throw new ValidationException(
                    String.format(
                        "Telemetry timestamp is too far in the past at index %d",
                        i
                    ),
                    ErrorCode.TELEMETRY_VALIDATION_FAILED,
                    Map.of(
                        "index", i,
                        "timestamp", timestamp.toString(),
                        "maxPast", maxPast.toString()
                    )
                );
            }
        }
    }
}
