package com.apple.telemetry.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;

/**
 * Request to analyze device health from telemetry.
 * 
 * Apple principle: Make the happy path easy, make the error path explicit.
 * 
 * Valid request:
 * {
 *   "device_id": "ABC123",
 *   "telemetry": [ {...}, {...}, ... ]
 * }
 * 
 * Invalid request → ValidationException with clear reasons
 */
@Data
public class DeviceHealthRequest {
    
    @NotNull(message = "Device ID is required")
    @JsonProperty("device_id")
    private String deviceId;
    
    @NotEmpty(message = "Telemetry data is required")
    @Valid
    @JsonProperty("telemetry")
    private List<TelemetryRecord> telemetry;
}
