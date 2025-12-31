package com.apple.telemetry.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.*;
import lombok.Data;

import java.time.Instant;

/**
 * Single telemetry data point from a device.
 * 
 * Apple principle: API models must match Python schemas exactly.
 * This mirrors TelemetrySchema from python/ingestion/schemas.py
 */
@Data
public class TelemetryRecord {
    
    @NotBlank(message = "Device ID is required")
    @JsonProperty("device_id")
    private String deviceId;
    
    @NotNull(message = "Timestamp is required")
    @JsonProperty("timestamp")
    private Instant timestamp;
    
    @NotNull(message = "Battery health is required")
    @DecimalMin(value = "0.0", message = "Battery health must be >= 0.0")
    @DecimalMax(value = "1.0", message = "Battery health must be <= 1.0")
    @JsonProperty("battery_health")
    private Double batteryHealth;
    
    @NotNull(message = "CPU usage is required")
    @DecimalMin(value = "0.0", message = "CPU usage must be >= 0.0")
    @DecimalMax(value = "100.0", message = "CPU usage must be <= 100.0")
    @JsonProperty("cpu_usage")
    private Double cpuUsage;
    
    @NotNull(message = "Memory usage is required")
    @DecimalMin(value = "0.0", message = "Memory usage must be >= 0.0")
    @DecimalMax(value = "100.0", message = "Memory usage must be <= 100.0")
    @JsonProperty("memory_usage")
    private Double memoryUsage;
    
    @NotNull(message = "Thermal state is required")
    @Min(value = 0, message = "Thermal state must be >= 0")
    @Max(value = 4, message = "Thermal state must be <= 4")
    @JsonProperty("thermal_state")
    private Integer thermalState;
    
    @NotNull(message = "Device type is required")
    @Min(value = 0, message = "Device type must be >= 0")
    @Max(value = 3, message = "Device type must be <= 3")
    @JsonProperty("device_type")
    private Integer deviceType;
}
