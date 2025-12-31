package com.apple.telemetry;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Device Health Analytics API
 * 
 * Apple-style defensive backend that exposes device health predictions
 * from the Python analytics layer.
 * 
 * Architecture:
 * - Java owns the API (this application)
 * - Python owns the analytics (subprocess invocation)
 * - Process isolation for safety
 * - Explicit error handling
 * 
 * @author Software Engineering Intern
 */
@SpringBootApplication
public class TelemetryApplication {
    
    private static final Logger logger = LoggerFactory.getLogger(TelemetryApplication.class);
    
    public static void main(String[] args) {
        logger.info("Starting Device Health Analytics API");
        logger.info("Python analytics integration: subprocess-based");
        logger.info("Defensive programming: ENABLED");
        
        SpringApplication.run(TelemetryApplication.class, args);
        
        logger.info("API ready - listening for requests");
    }
}
