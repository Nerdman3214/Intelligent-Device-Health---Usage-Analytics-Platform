package com.apple.telemetry.service;

import com.apple.telemetry.model.DeviceHealthRequest;
import com.apple.telemetry.model.DeviceHealthResponse;
import com.apple.telemetry.validation.RequestValidator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

/**
 * Device health business logic layer.
 * 
 * Apple principle: Controllers are thin, services contain logic.
 * 
 * Responsibilities:
 * - Orchestrate validation
 * - Invoke analytics
 * - Apply business rules
 * - Log decisions
 */
@Service
public class DeviceHealthService {
    
    private static final Logger logger = LoggerFactory.getLogger(DeviceHealthService.class);
    
    private final RequestValidator validator;
    private final PythonAnalyticsService analyticsService;
    
    public DeviceHealthService(
        RequestValidator validator,
        PythonAnalyticsService analyticsService
    ) {
        this.validator = validator;
        this.analyticsService = analyticsService;
    }
    
    /**
     * Analyze device health from telemetry.
     * 
     * Flow:
     * 1. Validate request (business rules)
     * 2. Invoke Python analytics
     * 3. Return structured response
     * 
     * All exceptions are typed and logged.
     */
    public DeviceHealthResponse analyzeDeviceHealth(DeviceHealthRequest request) {
        logger.info(
            "Starting device health analysis [deviceId={}]",
            request.getDeviceId()
        );
        
        // Validate request
        validator.validateHealthRequest(request);
        
        // Invoke analytics
        DeviceHealthResponse response = analyticsService.analyzeDeviceHealth(request);
        
        // Log result
        logger.info(
            "Device health analysis complete [deviceId={}] [risk={}] [confident={}]",
            response.getDeviceId(),
            response.getPredictedRisk(),
            response.getIsConfident()
        );
        
        return response;
    }
}
