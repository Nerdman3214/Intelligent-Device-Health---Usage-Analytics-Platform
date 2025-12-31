package com.apple.telemetry.controller;

import com.apple.telemetry.metrics.PerformanceMetrics;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Metrics endpoint for observability.
 * 
 * Apple principle: Systems must be observable in production.
 * 
 * Exposes:
 * - Request counts and error rates
 * - Latency statistics
 * - Prediction quality metrics
 * - Model version distribution
 */
@RestController
@RequestMapping("/api/metrics")
public class MetricsController {
    
    private final PerformanceMetrics metrics;
    
    public MetricsController(PerformanceMetrics metrics) {
        this.metrics = metrics;
    }
    
    /**
     * Get current metrics snapshot.
     * 
     * GET /api/metrics
     * 
     * Returns comprehensive system metrics for monitoring dashboards.
     */
    @GetMapping
    public ResponseEntity<PerformanceMetrics.MetricsSnapshot> getMetrics() {
        return ResponseEntity.ok(metrics.getSnapshot());
    }
}
