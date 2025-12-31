package com.apple.telemetry.service;

import com.apple.telemetry.exception.AnalyticsException;
import com.apple.telemetry.exception.ErrorCode;
import com.apple.telemetry.model.DeviceHealthRequest;
import com.apple.telemetry.model.DeviceHealthResponse;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/**
 * Python analytics integration via subprocess.
 * 
 * Apple principle: Process isolation for safety.
 * 
 * Why subprocess (not JNI)?
 * - Simpler to debug
 * - Process isolation (Python crash != Java crash)
 * - Clear contract (JSON in/out)
 * - Appropriate for intern-level project
 * 
 * If Python fails → Java still lives
 */
@Service
public class PythonAnalyticsService {
    
    private static final Logger logger = LoggerFactory.getLogger(PythonAnalyticsService.class);
    
    @Value("${analytics.python.executable:python3}")
    private String pythonExecutable;
    
    @Value("${analytics.python.script:python/analytics_api.py}")
    private String pythonScript;
    
    @Value("${analytics.timeout.seconds:30}")
    private int timeoutSeconds;
    
    private final ObjectMapper objectMapper;
    
    public PythonAnalyticsService(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }
    
    /**
     * Analyze device health by invoking Python analytics.
     * 
     * Flow:
     * 1. Serialize request to JSON
     * 2. Invoke Python subprocess
     * 3. Wait for response (with timeout)
     * 4. Parse JSON response
     * 5. Return structured result
     * 
     * Errors are explicit:
     * - Timeout → PYTHON_PROCESS_TIMEOUT
     * - Non-zero exit → PYTHON_PROCESS_CRASHED
     * - Parse error → MODEL_INFERENCE_FAILED
     */
    public DeviceHealthResponse analyzeDeviceHealth(DeviceHealthRequest request) {
        logger.info(
            "Invoking Python analytics [deviceId={}] [samples={}]",
            request.getDeviceId(),
            request.getTelemetry().size()
        );
        
        try {
            // Serialize request to JSON
            String requestJson = objectMapper.writeValueAsString(request);
            
            // Create temp file for request (safer than stdin for large payloads)
            Path requestFile = Files.createTempFile("telemetry_request_", ".json");
            Files.writeString(requestFile, requestJson);
            
            // Build Python command
            ProcessBuilder pb = new ProcessBuilder(
                pythonExecutable,
                pythonScript,
                requestFile.toString()
            );
            
            // Set working directory to project root
            pb.directory(new File(System.getProperty("user.dir")).getParentFile());
            pb.redirectErrorStream(true);
            
            // Execute
            long startTime = System.currentTimeMillis();
            Process process = pb.start();
            
            // Read output
            StringBuilder output = new StringBuilder();
            try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(process.getInputStream())
            )) {
                String line;
                while ((line = reader.readLine()) != null) {
                    output.append(line).append("\n");
                }
            }
            
            // Wait for completion (with timeout)
            boolean completed = process.waitFor(timeoutSeconds, TimeUnit.SECONDS);
            
            if (!completed) {
                process.destroyForcibly();
                throw new AnalyticsException(
                    "Python analytics timed out",
                    ErrorCode.PYTHON_PROCESS_TIMEOUT,
                    Map.of(
                        "timeoutSeconds", timeoutSeconds,
                        "deviceId", request.getDeviceId()
                    )
                );
            }
            
            int exitCode = process.exitValue();
            long duration = System.currentTimeMillis() - startTime;
            
            // Clean up temp file
            Files.deleteIfExists(requestFile);
            
            if (exitCode != 0) {
                logger.error(
                    "Python analytics failed [exitCode={}] [output={}]",
                    exitCode,
                    output.toString()
                );
                
                throw new AnalyticsException(
                    "Python analytics process failed",
                    ErrorCode.PYTHON_PROCESS_CRASHED,
                    Map.of(
                        "exitCode", exitCode,
                        "output", output.toString().substring(0, Math.min(500, output.length()))
                    )
                );
            }
            
            // Parse response
            String responseJson = output.toString();
            DeviceHealthResponse response = objectMapper.readValue(
                responseJson,
                DeviceHealthResponse.class
            );
            
            logger.info(
                "Python analytics succeeded [deviceId={}] [risk={}] [confidence={:.2f}] [duration={}ms]",
                response.getDeviceId(),
                response.getPredictedRisk(),
                response.getConfidence(),
                duration
            );
            
            return response;
            
        } catch (AnalyticsException e) {
            throw e;
        } catch (Exception e) {
            logger.error("Python analytics invocation failed", e);
            throw new AnalyticsException(
                "Failed to invoke Python analytics",
                ErrorCode.ANALYTICS_UNAVAILABLE,
                Map.of("error", e.getMessage()),
                e
            );
        }
    }
}
