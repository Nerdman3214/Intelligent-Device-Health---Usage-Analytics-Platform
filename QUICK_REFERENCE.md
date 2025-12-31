# 🚀 Quick Reference Card

## Running the Project

### Phase 1-2 Demo (Data Ingestion + Statistics)
```bash
python python/demo.py
```

### Phase 3 Demo (ML Training + Prediction)
```bash
python demo_phase3.py
```

### Phase 4 API (Backend Server)
```bash
cd java && mvn spring-boot:run
# Access: http://localhost:8080/api/device/health/ping
```

---

## Project Structure at a Glance

```
📦 Intelligent Device Health & Usage Analytics Platform
├── 📂 python/
│   ├── 📂 ingestion/          # Phase 1: Data pipeline
│   │   ├── schemas.py
│   │   ├── validator.py
│   │   ├── generator.py
│   │   └── ingestor.py
│   ├── 📂 analytics/          # Phase 2-3: Analytics + ML
│   │   ├── metrics.py         # Phase 2
│   │   ├── trends.py          # Phase 2
│   │   ├── anomalies.py       # Phase 2
│   │   ├── summaries.py       # Phase 2
│   │   ├── features.py        # Phase 3
│   │   ├── labels.py          # Phase 3
│   │   ├── train.py           # Phase 3
│   │   ├── predict.py         # Phase 3
│   │   ├── explain.py         # Phase 3
│   │   └── evaluate.py        # Phase 3
│   ├── analytics_api.py       # Phase 4: Java ↔ Python bridge
│   └── demo.py                # Phase 1-2 demo
├── 📂 java/                   # Phase 4: Backend API
│   ├── pom.xml
│   └── src/main/java/com/apple/telemetry/
│       ├── TelemetryApplication.java
│       ├── controller/
│       ├── service/
│       ├── validation/
│       ├── model/
│       └── exception/
├── 📂 models/                 # Trained ML models
├── 📂 data/                   # Generated telemetry
├── 📂 reports/                # Analysis outputs
├── demo_phase3.py             # Phase 3 demo
├── requirements.txt
└── README.md
```

---

## Key Commands

```bash
# Install Python dependencies
pip install -r requirements.txt

# Train ML models (required before Phase 4)
python demo_phase3.py

# Run Java backend
cd java && mvn clean package && mvn spring-boot:run

# Test API
curl http://localhost:8080/api/device/health/ping
```

---

## Interview Cheat Sheet

### 1-Minute Pitch
"I built a device health analytics platform similar to what Apple uses internally. It demonstrates backend engineering, defensive programming, and explainable ML. The system has 4 phases: data ingestion with validation, statistical analysis, predictive ML with feature engineering, and a Java Spring Boot REST API. Key features include typed exceptions, process isolation, and comprehensive explainability for every prediction."

### Technical Highlights
- **~3,670 lines** of production code (Python + Java)
- **22 interpretable features** extracted from device telemetry
- **3 ML models** (Logistic Regression, Random Forest, Gradient Boosting)
- **Defensive validation** at every layer (no silent failures)
- **Process isolation** (Java API ↔ Python analytics via subprocess)
- **Typed error codes** (13 explicit error types, no generic 500s)

### Apple Principles Applied
1. **Explainability** - Only interpretable models, feature attribution
2. **Reliability** - Fail-fast validation, typed exceptions
3. **Observability** - Structured logging with request IDs
4. **Defensiveness** - Two-layer validation, OOD detection, timeout protection

---

## File Count

- **17** Python modules
- **13** Java classes  
- **8** documentation files
- **2** API endpoints
- **3** ML models supported
- **22** features engineered

---

## Architecture Pattern

```
Client → Java API → Python Analytics → ML Models
         ↓            ↓                 ↓
      Validation   Features         Prediction
      Exception    Extraction       + Explain
      Handling     Labeling
      Logging      Training
```

**Key Design:** Java never crashes (even if Python fails)

---

## Error Handling Philosophy

```
❌ NEVER: throw new Exception("Something failed");
✅ ALWAYS: throw new AnalyticsException(
              "Model inference failed",
              ErrorCode.MODEL_INFERENCE_FAILED,
              Map.of("modelVersion", "v1.2.0", "deviceId", "ABC")
          );
```

Every error must be:
- **Categorized** (typed error code)
- **Contextualized** (metadata map)
- **Logged** (with request ID)
- **Returned** (structured JSON)

---

## Demo Paths

### Show Data Pipeline (5 min)
```bash
python python/demo.py
# Watch validation, metrics, trends, anomalies, summaries
```

### Show ML Training (10 min)
```bash
python demo_phase3.py
# Watch feature extraction, labeling, training, prediction, evaluation
```

### Show Backend API (5 min)
```bash
cd java && mvn spring-boot:run
# In another terminal:
curl http://localhost:8080/api/device/health/ping
```

---

**Total Project Time Investment:** Phases 1-4 Complete
**Readiness:** Apple Software Engineer Intern Interview ✅
