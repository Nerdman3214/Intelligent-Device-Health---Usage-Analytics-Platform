# Failure Modes & Safety Engineering

## 🎯 Apple Principle

**"Design for failure, not just success."**

At Apple, systems must be **predictable under failure**. This document catalogs every failure mode, how we detect it, and how we respond.

## 🏗️ System Architecture (Failure Perspective)

```
User Request
     ↓
┌────────────────────────────┐
│   Java API Layer           │  ← Can fail: OOM, thread exhaustion
│   - Validation             │  ← Can fail: Invalid input
│   - Controller             │  ← Can fail: Serialization error
│   - Global exception       │
└────────────┬───────────────┘
             ↓
┌────────────────────────────┐
│   Python Process           │  ← Can fail: Crash, timeout, corrupt output
│   - Feature extraction     │  ← Can fail: Missing columns, NaN
│   - Model inference        │  ← Can fail: Model missing, incompatible data
│   - Explainability         │  ← Can fail: Computation error
└────────────┬───────────────┘
             ↓
┌────────────────────────────┐
│   C++ Accelerator (Opt)    │  ← Can fail: Segfault, numeric overflow
│   - Rolling stats          │
│   - Percentiles            │
└────────────────────────────┘
```

**Every layer can fail.** We design for it.

## 📋 Comprehensive Failure Catalog

### Layer 1: Input Validation Failures

#### Failure: Invalid Request JSON

**Trigger**: Malformed JSON, missing fields, wrong types

```bash
# Bad request
curl -X POST http://localhost:8080/api/device/health/analyze \
  -H "Content-Type: application/json" \
  -d '{"device_id": null}'  # Missing telemetry
```

**Detection**: Spring `@Valid` annotation

**Response**:
```json
{
  "errorCode": "INVALID_REQUEST",
  "message": "Validation failed",
  "timestamp": "2025-12-31T10:30:00Z",
  "requestId": "req-abc123",
  "path": "/api/device/health/analyze",
  "details": {
    "field": "telemetry",
    "rejectedValue": null,
    "reason": "must not be null"
  }
}
```

**HTTP Status**: 400 Bad Request

**Safety**: Request never reaches Python. Fast fail.

---

#### Failure: Insufficient Telemetry

**Trigger**: < 10 telemetry samples

```json
{
  "device_id": "device-001",
  "telemetry": [
    {"timestamp": 1735650000, "cpu_percent": 45.0, ...}
    // Only 5 samples
  ]
}
```

**Detection**: `RequestValidator.validate()`

**Response**:
```json
{
  "errorCode": "INSUFFICIENT_TELEMETRY",
  "message": "Need at least 10 telemetry samples for reliable prediction",
  "details": {
    "received": 5,
    "minimum": 10
  }
}
```

**HTTP Status**: 400 Bad Request

**Safety**: Prevents unreliable predictions. Better to fail fast than return garbage.

---

#### Failure: Excessive Telemetry (DoS)

**Trigger**: > 10,000 samples in single request

**Detection**: `RequestValidator.validate()`

**Response**:
```json
{
  "errorCode": "EXCESSIVE_TELEMETRY",
  "message": "Too many samples",
  "details": {
    "received": 50000,
    "maximum": 10000
  }
}
```

**HTTP Status**: 400 Bad Request

**Safety**: DoS protection. Prevents memory exhaustion.

---

### Layer 2: Python Integration Failures

#### Failure: Python Process Crash

**Trigger**: Uncaught exception in Python, segfault, `sys.exit(1)`

```python
# Python code
raise Exception("Unexpected error")
```

**Detection**: Exit code ≠ 0

```java
int exitCode = process.waitFor(30, TimeUnit.SECONDS);
if (exitCode != 0) {
    throw new AnalyticsException(
        ErrorCode.PYTHON_PROCESS_FAILED,
        Map.of("exitCode", exitCode, "stderr", stderr)
    );
}
```

**Response**:
```json
{
  "errorCode": "PYTHON_PROCESS_FAILED",
  "message": "Analytics process exited with error",
  "details": {
    "exitCode": 1,
    "stderr": "Traceback (most recent call last):\n  File..."
  }
}
```

**HTTP Status**: 500 Internal Server Error

**Safety**: 
- Java doesn't crash (process isolation)
- Stderr captured for debugging
- Request logged with full context

---

#### Failure: Python Process Timeout

**Trigger**: Python takes > 30 seconds

```python
# Python code
import time
time.sleep(35)  # Exceeds timeout
```

**Detection**: `process.waitFor(30, TimeUnit.SECONDS)` returns `false`

**Response**:
```java
if (!finished) {
    process.destroyForcibly();  // Kill it
    throw new AnalyticsException(
        ErrorCode.PYTHON_PROCESS_TIMEOUT,
        Map.of("timeoutSeconds", 30)
    );
}
```

```json
{
  "errorCode": "PYTHON_PROCESS_TIMEOUT",
  "message": "Analytics process timed out",
  "details": {
    "timeoutSeconds": 30
  }
}
```

**HTTP Status**: 504 Gateway Timeout

**Safety**:
- Process is **killed** (no zombie processes)
- Temp files cleaned up
- Client gets clear timeout error
- Metrics incremented (timeout counter)

---

#### Failure: Corrupted Python Output

**Trigger**: Python writes invalid JSON to stdout

```python
# Python code
print("NOT VALID JSON")
```

**Detection**: `ObjectMapper.readValue()` throws `JsonParseException`

**Response**:
```json
{
  "errorCode": "INVALID_PYTHON_OUTPUT",
  "message": "Failed to parse analytics output",
  "details": {
    "stdout": "NOT VALID JSON",
    "parseError": "Unexpected character..."
  }
}
```

**HTTP Status**: 500 Internal Server Error

**Safety**: Explicit error instead of silent corruption.

---

### Layer 3: Model & Data Failures

#### Failure: Model Not Found

**Trigger**: No trained model in `models/` directory

```python
# Python code
model_path = self.find_latest_model()
if model_path is None:
    raise FileNotFoundError("No trained model found")
```

**Detection**: Python raises exception → exit code 1

**Response**:
```json
{
  "errorCode": "MODEL_LOAD_FAILED",
  "message": "Failed to load prediction model",
  "details": {
    "stderr": "FileNotFoundError: No trained model found"
  }
}
```

**HTTP Status**: 503 Service Unavailable

**Safety**: System won't return random predictions without model.

---

#### Failure: Model Inference Error

**Trigger**: Data shape mismatch, NaN in features, OOM

```python
# Python code
predictions = model.predict(features)  # Shape mismatch
```

**Detection**: Python exception → exit code 1

**Response**:
```json
{
  "errorCode": "MODEL_INFERENCE_FAILED",
  "message": "Prediction failed",
  "details": {
    "stderr": "ValueError: Input contains NaN..."
  }
}
```

**HTTP Status**: 500 Internal Server Error

**Safety**: Explicit error instead of wrong prediction.

---

#### Failure: Low Confidence Prediction

**Trigger**: Model confidence < 0.6

```python
# Python code
confidence = max(probabilities)
if confidence < 0.6:
    warnings.append("Low confidence prediction - manual review recommended")
```

**Detection**: Application logic (not an error)

**Response**:
```json
{
  "predicted_risk": "high",
  "confidence": 0.43,
  "warnings": [
    "Low confidence prediction - manual review recommended"
  ],
  "explanation_text": "Model is uncertain. Consider collecting more telemetry."
}
```

**HTTP Status**: 200 OK (with warning)

**Safety**: 
- Prediction still returned
- **Warning flag** alerts user
- **Human decides** whether to trust it
- Metrics track low-confidence rate

---

#### Failure: Out-of-Distribution Input

**Trigger**: Feature values far outside training distribution

```python
# Example: CPU usage = 500% (impossible)
if cpu_percent > 100:
    warnings.append("Out-of-distribution input detected")
```

**Detection**: Statistical checks in feature extraction

**Response**:
```json
{
  "predicted_risk": "high",
  "confidence": 0.78,
  "warnings": [
    "Out-of-distribution input detected - prediction may be unreliable"
  ]
}
```

**HTTP Status**: 200 OK (with warning)

**Safety**: System doesn't silently trust bad inputs.

---

### Layer 4: Resource & System Failures

#### Failure: Java Out of Memory

**Trigger**: Too many concurrent requests, memory leak

**Detection**: JVM throws `OutOfMemoryError`

**Response**: Caught by `GlobalExceptionHandler`

```json
{
  "errorCode": "INTERNAL_ERROR",
  "message": "Unexpected error occurred",
  "requestId": "req-xyz789"
}
```

**HTTP Status**: 500 Internal Server Error

**Safety**:
- Error logged with full stack trace
- Request ID for correlation
- **No sensitive data** in response

**Prevention**:
- Connection pooling
- Request rate limiting (future)
- JVM max heap size tuning

---

#### Failure: Temp File Cleanup Failure

**Trigger**: Disk full, permission denied

**Detection**: `Files.delete()` throws `IOException`

**Response**: Logged as warning, not thrown

```java
try {
    Files.deleteIfExists(tempFile);
} catch (IOException e) {
    logger.warn("Failed to delete temp file [path={}]", tempFile, e);
    // Don't throw - cleanup is best-effort
}
```

**Safety**: 
- Cleanup failure doesn't break request
- Logged for ops team
- Temp files have unique names (no collision)

---

## 🛡️ Failure Response Strategy

### Principle: Fail Fast, Fail Explicitly

| ❌ Wrong | ✅ Right |
|---------|---------|
| Return success with garbage data | Throw typed exception |
| Swallow exceptions | Log + re-throw |
| Generic "Internal error" | Specific error code |
| No context | Error code + details map |
| Silent failure | Metrics + alerts |

### Exception Hierarchy

```
Exception
  └─ RuntimeException
       ├─ ValidationException (4xx - client error)
       │    ├─ INVALID_REQUEST
       │    ├─ INSUFFICIENT_TELEMETRY
       │    └─ EXCESSIVE_TELEMETRY
       │
       └─ AnalyticsException (5xx - server error)
            ├─ PYTHON_PROCESS_FAILED
            ├─ PYTHON_PROCESS_TIMEOUT
            ├─ INVALID_PYTHON_OUTPUT
            ├─ MODEL_LOAD_FAILED
            └─ MODEL_INFERENCE_FAILED
```

### Global Exception Handler

**Every exception** is caught and mapped to structured JSON:

```java
@RestControllerAdvice
public class GlobalExceptionHandler {
    
    @ExceptionHandler(ValidationException.class)
    public ResponseEntity<ApiError> handleValidation(ValidationException ex) {
        // Map to 4xx error
    }
    
    @ExceptionHandler(AnalyticsException.class)
    public ResponseEntity<ApiError> handleAnalytics(AnalyticsException ex) {
        // Map to 5xx error
    }
    
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiError> handleUnexpected(Exception ex) {
        // Safety net - catch everything
        logger.error("Unexpected error", ex);
        // Return INTERNAL_ERROR (no stack trace to client)
    }
}
```

**Apple Principle**: No exception escapes unhandled.

---

## 📊 Failure Metrics

### What We Track

```java
public class PerformanceMetrics {
    // Error counters by type
    private final ConcurrentHashMap<String, AtomicLong> errorsByType;
    
    // Specific failure metrics
    private final AtomicLong timeouts;
    private final AtomicLong pythonCrashes;
    private final AtomicLong lowConfidencePredictions;
    private final AtomicLong oodPredictions;
}
```

### Metrics Dashboard

```bash
curl http://localhost:8080/api/metrics
```

```json
{
  "totalRequests": 10000,
  "successfulRequests": 9542,
  "failedRequests": 458,
  "errorRate": 0.0458,
  "errorsByType": {
    "TIMEOUT": 89,
    "INVALID_REQUEST": 312,
    "PYTHON_PROCESS_FAILED": 42,
    "MODEL_INFERENCE_FAILED": 15
  },
  "lowConfidencePredictions": 234,
  "lowConfidenceRate": 0.0234
}
```

### Alerting Thresholds (Future)

| Metric | Threshold | Action |
|--------|-----------|--------|
| Error rate | > 5% | Page on-call |
| Timeout rate | > 2% | Scale up resources |
| Low confidence rate | > 10% | Retrain model |
| Python crash rate | > 1% | Investigate logs |

---

## 🧪 Failure Testing

### Manual Failure Injection

```bash
# Test timeout
curl -X POST http://localhost:8080/api/device/health/analyze \
  -d '{"device_id": "timeout-test", ...}'

# Test invalid input
curl -X POST http://localhost:8080/api/device/health/analyze \
  -d '{"device_id": null}'

# Test insufficient data
curl -X POST http://localhost:8080/api/device/health/analyze \
  -d '{"device_id": "test", "telemetry": []}'
```

### Chaos Engineering (Future)

```python
# Randomly inject failures
import random

if random.random() < 0.1:  # 10% failure rate
    raise Exception("Chaos monkey!")
```

---

## 🎯 Interview Talking Points

When asked: **"How do you handle failures?"**

> "I explicitly design for failure. In my device health platform, I cataloged every failure mode — timeouts, crashes, corrupted data, low confidence predictions — and designed specific responses. For example, Python process timeouts kill the process after 30 seconds and return a 504 error with metrics tracking. Low confidence predictions return a warning flag instead of failing, so humans can decide whether to trust them. Every exception is typed with an error code and context map, never generic. The system has a global exception handler as a safety net, and I track error rates by type for observability. This is Apple-style defensive programming."

**That's senior-engineer thinking.** 🍎

---

## 📚 Related Documentation

- [Performance Documentation](performance.md) - C++ optimization, latency
- [Tradeoffs Documentation](tradeoffs.md) - Engineering decisions
- [API Documentation](../PHASE4_README.md) - Error response schemas
