# Phase 4: Java Spring Boot Backend API

## ✅ Status: COMPLETE

Apple-style defensive backend that safely exposes Python analytics via REST API.

---

## 🏗️ Architecture

```
┌─────────────────┐
│ REST API Client │
└────────┬────────┘
         │ HTTP/JSON
         ▼
┌─────────────────────────┐
│ Spring Boot API (Java)  │
├─────────────────────────┤
│ • Controller Layer      │
│ • Validation Layer      │
│ • Service Layer         │
│ • Exception Handling    │
└────────┬────────────────┘
         │ Subprocess (JSON)
         ▼
┌─────────────────────────┐
│ Python Analytics        │
│ (Phases 1-3)            │
└─────────────────────────┘
```

**Key Design:**
- Java owns the API (never exposes Python directly)
- Process isolation (Python crash != Java crash)
- Clear contract (JSON in/out)
- Typed exceptions (no generic 500s)

---

## 📁 Project Structure

```
java/
├── pom.xml                                    # Maven dependencies
└── src/main/java/com/apple/telemetry/
    ├── TelemetryApplication.java              # Spring Boot entry point
    ├── controller/
    │   └── DeviceHealthController.java        # REST endpoints
    ├── service/
    │   ├── DeviceHealthService.java           # Business logic
    │   └── PythonAnalyticsService.java        # Python integration
    ├── validation/
    │   └── RequestValidator.java              # Business validation
    ├── model/
    │   ├── TelemetryRecord.java               # Input model
    │   ├── DeviceHealthRequest.java           # Request DTO
    │   └── DeviceHealthResponse.java          # Response DTO
    └── exception/
        ├── ErrorCode.java                     # Typed error codes
        ├── ApiError.java                      # Structured errors
        ├── ValidationException.java           # Client errors (4xx)
        ├── AnalyticsException.java            # System errors (5xx)
        └── GlobalExceptionHandler.java        # Error mapping
```

---

## 🔌 API Endpoints

### POST /api/device/health/analyze

Analyze device health from telemetry data.

**Request:**
```json
{
  "device_id": "ABC123",
  "telemetry": [
    {
      "device_id": "ABC123",
      "timestamp": "2025-12-31T10:00:00Z",
      "battery_health": 0.92,
      "cpu_usage": 45.0,
      "memory_usage": 60.0,
      "thermal_state": 0,
      "device_type": 0
    },
    ...  // minimum 10 samples required
  ]
}
```

**Response (Success):**
```json
{
  "device_id": "ABC123",
  "predicted_risk": "HEALTHY",
  "confidence": 0.89,
  "probabilities": {
    "HEALTHY": 0.89,
    "AT_RISK": 0.10,
    "DEGRADED": 0.01
  },
  "is_confident": true,
  "is_in_distribution": true,
  "top_contributing_features": [
    {
      "feature": "battery_health_mean",
      "value": 0.92,
      "contribution": 0.15,
      "direction": "decreases"
    },
    ...
  ],
  "warnings": [],
  "explanation_text": "Device risk level: HEALTHY\n...",
  "model_version": "gradient_boosting_20240115_120000.pkl"
}
```

**Response (Error):**
```json
{
  "errorCode": "INSUFFICIENT_TELEMETRY",
  "message": "Insufficient telemetry data: 5 samples provided, minimum 10 required",
  "timestamp": "2025-12-31T10:30:00Z",
  "requestId": "req-a1b2c3d4",
  "path": "/api/device/health/analyze",
  "details": {
    "providedSamples": 5,
    "requiredSamples": 10
  }
}
```

### GET /api/device/health/ping

Health check endpoint.

**Response:**
```
Device Health API is running
```

---

## 🛡️ Defensive Programming Features

### 1. Typed Error Codes (No Generic 500s)

Every error has an explicit code:
- `INVALID_REQUEST` - Bad input format
- `INSUFFICIENT_TELEMETRY` - Not enough samples
- `MODEL_INFERENCE_FAILED` - Prediction failed
- `PYTHON_PROCESS_TIMEOUT` - Analytics took too long
- `PYTHON_PROCESS_CRASHED` - Python exited abnormally

### 2. Two-Layer Validation

**Spring @Valid** (syntax):
- Field presence (`@NotNull`)
- Value ranges (`@Min`, `@Max`)
- Type correctness

**RequestValidator** (business logic):
- Minimum 10 telemetry samples
- Maximum 10,000 samples (DoS protection)
- Timestamps within reasonable range
- Device ID format validation

### 3. Process Isolation

Python runs in separate process:
- **Timeout protection** (default: 30 seconds)
- **Exit code checking** (non-zero = error)
- **Stderr capture** (for debugging)
- **Temp file cleanup** (no leaks)

If Python crashes → Java returns structured error, API stays alive.

### 4. Structured Logging

Every request logs:
```
INFO  - Received health analysis request [deviceId=ABC123]
DEBUG - Validating health request for device: ABC123
DEBUG - Validation passed for device: ABC123
INFO  - Invoking Python analytics [deviceId=ABC123] [samples=100]
INFO  - Python analytics succeeded [deviceId=ABC123] [risk=HEALTHY] [confidence=0.89] [duration=1234ms]
INFO  - Device health analysis complete [deviceId=ABC123] [risk=HEALTHY] [confident=true]
```

Errors log with context:
```
ERROR - Python analytics failed [exitCode=1] [output=...]
ERROR - UNEXPECTED EXCEPTION [requestId=req-12345] [type=IOException] [message=...]
```

### 5. Global Exception Handler

Catches ALL exceptions and maps to structured errors:
- `ValidationException` → 4xx with details
- `AnalyticsException` → 5xx with context
- `Exception` → 500 with request ID for support

NO unhandled exceptions leak to clients.

---

## 🚀 How to Run

### Prerequisites

1. **Java 17+** installed
2. **Maven 3.8+** installed
3. **Python 3.10+** with Phase 3 dependencies
4. **Trained models** (run `python demo_phase3.py` first)

### Build & Run

```bash
# Navigate to Java directory
cd java/

# Build with Maven
mvn clean package

# Run Spring Boot application
mvn spring-boot:run

# Or run JAR directly
java -jar target/telemetry-api-1.0.0.jar
```

**API starts on:** http://localhost:8080

### Test the API

```bash
# Health check
curl http://localhost:8080/api/device/health/ping

# Analyze device health (example)
curl -X POST http://localhost:8080/api/device/health/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "TEST_DEVICE",
    "telemetry": [
      {
        "device_id": "TEST_DEVICE",
        "timestamp": "2025-12-31T10:00:00Z",
        "battery_health": 0.92,
        "cpu_usage": 45.0,
        "memory_usage": 60.0,
        "thermal_state": 0,
        "device_type": 0
      },
      ... (repeat 10+ times with variations)
    ]
  }'
```

---

## 📊 What This Demonstrates

### Backend Engineering
✅ **Layered architecture** (Controller → Service → Validation → Integration)
✅ **Dependency injection** (Spring's IoC container)
✅ **RESTful API design** (proper HTTP verbs, status codes)
✅ **DTO pattern** (separate request/response models)

### Defensive Programming
✅ **Typed exceptions** (no generic RuntimeException)
✅ **Global error handling** (@RestControllerAdvice)
✅ **Input validation** (both syntax and business logic)
✅ **Process isolation** (subprocess, not JNI)
✅ **Timeout protection** (analytics can't hang API)

### Production Readiness
✅ **Structured logging** (with context)
✅ **Configuration externalization** (application.properties)
✅ **Error observability** (request IDs, stack traces)
✅ **Resource cleanup** (temp files deleted)

### Apple Principles
✅ **Explicit over implicit** (typed errors, clear messages)
✅ **Fail loudly but safely** (structured errors, never crash)
✅ **Observability first** (log decisions, not just failures)
✅ **Process boundaries** (Java ≠ Python, clear contracts)

---

## 🎤 Interview Talking Points

### "Why Java for the API?"

> "Python is great for analytics, but Java is better for backend services at scale. Java gives us:
> - Strong typing (catch errors at compile time)
> - Better concurrency (thread pools, async)
> - Industry standard for backend APIs
> - Clear separation from analytics (process isolation)"

### "Why subprocess, not JNI?"

> "Process isolation is safer and simpler:
> - If Python crashes, Java stays alive
> - Clear JSON contract (no ABI issues)
> - Easier to debug (separate logs)
> - Easier to version independently
> - Appropriate complexity for intern project
> 
> JNI would be overkill and harder to maintain."

### "How do you handle Python failures?"

> "Defensively, with explicit error types:
> - **Timeout**: Kill process, return `PYTHON_PROCESS_TIMEOUT`
> - **Non-zero exit**: Capture stderr, return `PYTHON_PROCESS_CRASHED`
> - **Parse error**: Return `MODEL_INFERENCE_FAILED`
> 
> Java API never crashes. Every error is typed, logged, and returned as structured JSON."

### "What makes this 'Apple-style'?"

> "Three things:
> 1. **Explainability**: Every error has a code and context
> 2. **Reliability**: No silent failures, explicit validation
> 3. **Observability**: Structured logs with request IDs
> 
> This isn't just CRUD — it's production-grade defensive engineering."

---

## ✅ Phase 4 Completion Checklist

- ✅ API accepts device telemetry
- ✅ API returns health predictions
- ✅ Errors are explicit and typed
- ✅ Logs are structured
- ✅ No silent failures exist
- ✅ Can explain every layer

**Phase 4 is COMPLETE!** 🎉

---

## 🔮 Next Steps (Phase 5)

- C++ optimization for hot paths (feature extraction)
- Python bindings (pybind11)
- Performance benchmarking
- Load testing

---

**Ready for your Apple Software Engineer Intern interview!** 🍎
