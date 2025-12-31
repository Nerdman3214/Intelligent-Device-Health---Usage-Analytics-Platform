package com.apple.telemetry.controller;

import com.apple.telemetry.metrics.PerformanceMetrics;
import com.apple.telemetry.model.DeviceHealthRequest;
import com.apple.telemetry.model.DeviceHealthResponse;
import com.apple.telemetry.service.DeviceHealthService;
import jakarta.validation.Valid;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/**
 * Device Health API Controller.
 * 
 * Apple principle: Controllers are thin - they handle HTTP, nothing else.
 * 
 * Endpoints:
 * - POST /api/device/health/analyze - Analyze device health from telemetry
 * 
 * All validation/business logic is in service layer.
 */
@RestController
@RequestMapping("/api/device/health")
public class DeviceHealthController {
    
    private static final Logger logger = LoggerFactory.getLogger(DeviceHealthController.class);
    
    private final DeviceHealthService healthService;
    private final PerformanceMetrics metrics;
    
    public DeviceHealthController(DeviceHealthService healthService, PerformanceMetrics metrics) {
        this.healthService = healthService;
        this.metrics = metrics;
    }
    
    /**
     * Analyze device health from telemetry data.
     * 
     * Request:
     * POST /api/device/health/analyze
     * {
     *   "device_id": "ABC123",
     *   "telemetry": [
     *     {
     *       "timestamp": "2025-12-31T10:00:00Z",
     *       "battery_health": 0.92,
     *       "cpu_usage": 45.0,
     *       "memory_usage": 60.0,
     *       "thermal_state": 0,
     *       "device_type": 0
     *     },
     *     ...
     *   ]
     * }
     * 
     * Response:
     * {
     *   "device_id": "ABC123",
     *   "predicted_risk": "HEALTHY",
     *   "confidence": 0.89,
     *   "probabilities": {...},
     *   "top_contributing_features": [...],
     *   "explanation_text": "..."
     * }
     */
    @PostMapping("/analyze")
    public ResponseEntity<DeviceHealthResponse> analyzeDeviceHealth(
        @Valid @RequestBody DeviceHealthRequest request
    ) {
        logger.info("Received health analysis request [deviceId={}]", request.getDeviceId());
        
        PerformanceMetrics.RequestContext context = metrics.startRequest("/api/device/health/analyze");
        
        try {
            DeviceHealthResponse response = healthService.analyzeDeviceHealth(request);
            metrics.recordSuccess(context);
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            // Failure metrics recorded by GlobalExceptionHandler
            throw e;
        }
    }
    
    /**
     * Health check endpoint.
     */
    @GetMapping("/ping")
    public ResponseEntity<String> ping() {
        return ResponseEntity.ok("Device Health API is running");
    }
}
