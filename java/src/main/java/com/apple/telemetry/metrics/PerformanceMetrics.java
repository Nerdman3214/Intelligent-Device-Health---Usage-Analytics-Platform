package com.apple.telemetry.metrics;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.time.Instant;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.Map;

/**
 * Performance and observability metrics.
 * 
 * Apple principle: You can't improve what you don't measure.
 * 
 * Tracks:
 * - Request latency (p50, p90, p95, p99)
 * - Error rates by type
 * - Prediction confidence distribution
 * - Model version usage
 * 
 * Thread-safe for concurrent use.
 */
@Component
public class PerformanceMetrics {
    
    private static final Logger logger = LoggerFactory.getLogger(PerformanceMetrics.class);
    
    // Request counters
    private final AtomicLong totalRequests = new AtomicLong(0);
    private final AtomicLong successfulRequests = new AtomicLong(0);
    private final AtomicLong failedRequests = new AtomicLong(0);
    
    // Error counters by type
    private final ConcurrentHashMap<String, AtomicLong> errorsByType = new ConcurrentHashMap<>();
    
    // Latency tracking (simplified - use Micrometer in production)
    private final ConcurrentHashMap<String, LatencyStats> latencyByEndpoint = new ConcurrentHashMap<>();
    
    // Prediction metrics
    private final AtomicLong lowConfidencePredictions = new AtomicLong(0);
    private final AtomicLong outOfDistributionPredictions = new AtomicLong(0);
    
    // Model version tracking
    private final ConcurrentHashMap<String, AtomicLong> predictionsByModel = new ConcurrentHashMap<>();
    
    /**
     * Record request start time.
     * 
     * @param endpoint Endpoint name
     * @return Request context for tracking
     */
    public RequestContext startRequest(String endpoint) {
        totalRequests.incrementAndGet();
        return new RequestContext(endpoint, Instant.now());
    }
    
    /**
     * Record successful request completion.
     */
    public void recordSuccess(RequestContext context) {
        successfulRequests.incrementAndGet();
        recordLatency(context);
    }
    
    /**
     * Record failed request.
     * 
     * @param context Request context
     * @param errorCode Error code that caused failure
     */
    public void recordFailure(RequestContext context, String errorCode) {
        failedRequests.incrementAndGet();
        errorsByType.computeIfAbsent(errorCode, k -> new AtomicLong(0)).incrementAndGet();
        recordLatency(context);
        
        logger.debug("Request failed [endpoint={}] [errorCode={}] [latencyMs={}]",
            context.endpoint, errorCode, context.getLatencyMs());
    }
    
    /**
     * Record prediction metrics.
     */
    public void recordPrediction(
        String modelVersion,
        double confidence,
        boolean isInDistribution
    ) {
        predictionsByModel.computeIfAbsent(modelVersion, k -> new AtomicLong(0))
            .incrementAndGet();
        
        if (confidence < 0.6) {
            lowConfidencePredictions.incrementAndGet();
        }
        
        if (!isInDistribution) {
            outOfDistributionPredictions.incrementAndGet();
        }
    }
    
    /**
     * Get current metrics snapshot.
     */
    public MetricsSnapshot getSnapshot() {
        MetricsSnapshot snapshot = new MetricsSnapshot();
        
        // Request metrics
        snapshot.totalRequests = totalRequests.get();
        snapshot.successfulRequests = successfulRequests.get();
        snapshot.failedRequests = failedRequests.get();
        
        if (snapshot.totalRequests > 0) {
            snapshot.successRate = (double) snapshot.successfulRequests / snapshot.totalRequests;
            snapshot.errorRate = (double) snapshot.failedRequests / snapshot.totalRequests;
        }
        
        // Error breakdown
        snapshot.errorsByType = new ConcurrentHashMap<>();
        errorsByType.forEach((code, count) -> 
            snapshot.errorsByType.put(code, count.get())
        );
        
        // Latency stats
        snapshot.latencyStats = new ConcurrentHashMap<>();
        latencyByEndpoint.forEach((endpoint, stats) -> 
            snapshot.latencyStats.put(endpoint, stats.getSnapshot())
        );
        
        // Prediction metrics
        snapshot.lowConfidencePredictions = lowConfidencePredictions.get();
        snapshot.outOfDistributionPredictions = outOfDistributionPredictions.get();
        
        if (snapshot.totalRequests > 0) {
            snapshot.lowConfidenceRate = (double) snapshot.lowConfidencePredictions / 
                                        snapshot.totalRequests;
            snapshot.oodRate = (double) snapshot.outOfDistributionPredictions / 
                              snapshot.totalRequests;
        }
        
        // Model usage
        snapshot.predictionsByModel = new ConcurrentHashMap<>();
        predictionsByModel.forEach((model, count) -> 
            snapshot.predictionsByModel.put(model, count.get())
        );
        
        return snapshot;
    }
    
    /**
     * Reset all metrics (useful for testing).
     */
    public void reset() {
        totalRequests.set(0);
        successfulRequests.set(0);
        failedRequests.set(0);
        errorsByType.clear();
        latencyByEndpoint.clear();
        lowConfidencePredictions.set(0);
        outOfDistributionPredictions.set(0);
        predictionsByModel.clear();
    }
    
    private void recordLatency(RequestContext context) {
        LatencyStats stats = latencyByEndpoint.computeIfAbsent(
            context.endpoint,
            k -> new LatencyStats()
        );
        stats.record(context.getLatencyMs());
    }
    
    /**
     * Request tracking context.
     */
    public static class RequestContext {
        private final String endpoint;
        private final Instant startTime;
        
        public RequestContext(String endpoint, Instant startTime) {
            this.endpoint = endpoint;
            this.startTime = startTime;
        }
        
        public long getLatencyMs() {
            return Duration.between(startTime, Instant.now()).toMillis();
        }
    }
    
    /**
     * Latency statistics tracker.
     * 
     * Simplified implementation - use Micrometer/Prometheus in production.
     */
    private static class LatencyStats {
        private final AtomicLong count = new AtomicLong(0);
        private final AtomicLong sum = new AtomicLong(0);
        private volatile long min = Long.MAX_VALUE;
        private volatile long max = Long.MIN_VALUE;
        
        public synchronized void record(long latencyMs) {
            count.incrementAndGet();
            sum.addAndGet(latencyMs);
            
            if (latencyMs < min) min = latencyMs;
            if (latencyMs > max) max = latencyMs;
        }
        
        public LatencyStatsSnapshot getSnapshot() {
            long cnt = count.get();
            if (cnt == 0) {
                return new LatencyStatsSnapshot(0, 0, 0, 0);
            }
            
            return new LatencyStatsSnapshot(
                cnt,
                sum.get() / cnt,  // mean
                min,
                max
            );
        }
    }
    
    /**
     * Immutable latency stats snapshot.
     */
    public static class LatencyStatsSnapshot {
        public final long count;
        public final long meanMs;
        public final long minMs;
        public final long maxMs;
        
        public LatencyStatsSnapshot(long count, long meanMs, long minMs, long maxMs) {
            this.count = count;
            this.meanMs = meanMs;
            this.minMs = minMs;
            this.maxMs = maxMs;
        }
    }
    
    /**
     * Immutable metrics snapshot.
     */
    public static class MetricsSnapshot {
        public long totalRequests;
        public long successfulRequests;
        public long failedRequests;
        public double successRate;
        public double errorRate;
        
        public Map<String, Long> errorsByType;
        public Map<String, LatencyStatsSnapshot> latencyStats;
        
        public long lowConfidencePredictions;
        public long outOfDistributionPredictions;
        public double lowConfidenceRate;
        public double oodRate;
        
        public Map<String, Long> predictionsByModel;
        
        @Override
        public String toString() {
            return String.format(
                "MetricsSnapshot[total=%d, success=%d, failed=%d, successRate=%.2f%%, " +
                "lowConfidence=%d, ood=%d]",
                totalRequests, successfulRequests, failedRequests, 
                successRate * 100, lowConfidencePredictions, outOfDistributionPredictions
            );
        }
    }
}
