# Architecture & Design Decisions

> **Apple-Style System Design Philosophy**

---

## 🏗️ System Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│                     CLIENT LAYER (Future)                    │
│              Java Spring Boot API (Phase 4)                  │
└───────────────────┬─────────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────────┐
│                   ANALYTICS LAYER (Phase 2)                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Metrics  │  │  Trends  │  │Anomalies │  │Summaries │   │
│  │          │  │          │  │          │  │          │   │
│  │ - Mean   │  │ - SMA    │  │ - Z-score│  │ - Status │   │
│  │ - Median │  │ - EMA    │  │ - IQR    │  │ - Reasons│   │
│  │ - P90-99 │  │ - Slope  │  │ - Thresh │  │ - Recs   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└───────────────────┬─────────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────────┐
│                   INGESTION LAYER (Phase 1)                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Generator│→ │Validator │→ │Normalizer│→ │  Store   │   │
│  │          │  │          │  │          │  │          │   │
│  │ - Clean  │  │ - Types  │  │ - Schema │  │ - Proc'd │   │
│  │ - Noisy  │  │ - Ranges │  │  Conv.   │  │ - Reject │   │
│  │ - Corrupt│  │ - Format │  │          │  │          │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└───────────────────┬─────────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────────┐
│                      DATA LAYER                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │   Raw    │  │Processed │  │ Rejected │                  │
│  │  (opt)   │  │  (JSON)  │  │ (w/errs) │                  │
│  └──────────┘  └──────────┘  └──────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Design Principles

### 1. Schema-First Design

**Principle:** Define data contracts before writing code.

**Implementation:**
- `TelemetrySchema` dataclass with explicit types
- `SCHEMA_CONSTRAINTS` dictionary for validation rules
- Enums for categorical data (`ThermalState`, `DeviceType`)

**Why:**
- Prevents downstream bugs
- Makes validation logic explicit
- Self-documenting code
- Easy to update constraints

**Tradeoff:**
- More upfront design work
- Schema changes require careful migration

**Apple alignment:**  
Apple obsesses over data contracts. System reliability starts with schema correctness.

---

### 2. Defensive Validation (Fail-Fast)

**Principle:** Invalid data is REJECTED, never silently fixed.

**Implementation:**
```python
# ❌ WRONG: Silent coercion
value = float(data.get('cpu_usage', 0))

# ✅ RIGHT: Explicit validation
if not isinstance(data['cpu_usage'], float):
    raise ValidationError(
        field='cpu_usage',
        reason=f'Expected float, got {type(data["cpu_usage"]).__name__}',
        expected='float type'
    )
```

**Why:**
- Silent failures are dangerous
- Engineers need to know WHY data was rejected
- Garbage-in-garbage-out prevention
- Debugging is easier with explicit errors

**Tradeoff:**
- Higher initial rejection rate
- More verbose error handling code
- Requires comprehensive logging

**Apple alignment:**  
Apple would rather have NO data than BAD data. Reliability trumps convenience.

---

### 3. Separation of Concerns

**Principle:** Each module has ONE clear responsibility.

**Layer Boundaries:**

| Layer | Responsibility | Does NOT Do |
|-------|---------------|-------------|
| **Generator** | Create test data | Validate, Store |
| **Validator** | Check data correctness | Transform, Store |
| **Ingestor** | Orchestrate pipeline | Validate logic, Analytics |
| **Metrics** | Calculate statistics | Detect anomalies, Decide |
| **Trends** | Time-series analysis | Metrics, Anomalies |
| **Anomalies** | Detect outliers | Metrics, Decisions |
| **Summaries** | Decision support | Storage, Validation |

**Why:**
- Easy testing (mock one layer at a time)
- Easy replacement (swap validator without touching metrics)
- Clear error boundaries
- Maintainable codebase

**Tradeoff:**
- More files/classes
- More interfaces to manage
- Potential over-engineering for small projects

**Apple alignment:**  
Apple teams are specialized. Backend, data, and ML engineers don't step on each other's toes.

---

### 4. Observability Over Dashboards

**Principle:** Logs + Metrics > GUI (for now)

**Implementation:**
- Comprehensive logging at INFO, WARNING, ERROR levels
- Rejection tracking with categorized reasons
- Ingestion statistics (acceptance rate, rejection breakdown)
- Anomaly details (severity, confidence, expected range)

**Why:**
- Easier to debug production issues
- Metrics drive decisions, not screenshots
- No frontend dependencies (focus on backend)
- Aligns with Apple's internal tooling culture

**Tradeoff:**
- Less visually impressive for demos
- Requires engineers to read logs
- No "pretty dashboard" for stakeholders

**Apple alignment:**  
Apple engineers live in logs and metrics. Dashboards are nice-to-have, not critical.

---

### 5. Percentiles > Averages

**Principle:** Use P50, P90, P95, P99 instead of just mean.

**Why:**
- **Mean is fragile:** One outlier skews everything
- **Median (P50) is robust:** Represents typical behavior
- **P90-P99 reveal tail behavior:** Where real problems hide

**Example:**
```
CPU Usage:
  Mean: 45% ← Looks fine
  P90:  85% ← Wait, 10% of time it's high!
  P99:  98% ← Sometimes it's maxing out!
```

**Tradeoff:**
- Slightly more complex to calculate
- Harder to explain to non-technical stakeholders

**Apple alignment:**  
Apple's SRE teams prioritize P99 latency. Tail behavior matters.

---

## 📊 Data Flow

### Ingestion Pipeline (Phase 1)

```
┌────────────┐
│  Generate  │ ← TelemetryGenerator creates data
│   Data     │   - Clean (90%)
└──────┬─────┘   - Corrupted (10% for testing)
       │
       ▼
┌────────────┐
│  Validate  │ ← TelemetryValidator
│   (Strict) │   - Type checks (NO coercion)
└──────┬─────┘   - Range checks
       │          - Format validation
       │
       ├─────────────────┐
       │                 │
       ▼                 ▼
  ┌─────────┐      ┌──────────┐
  │ REJECT  │      │  ACCEPT  │
  │ + Log   │      │          │
  │ + Store │      │          │
  │  Error  │      │          │
  └─────────┘      └─────┬────┘
                         │
                         ▼
                   ┌──────────┐
                   │Normalize │ ← Convert to TelemetrySchema
                   │          │
                   └─────┬────┘
                         │
                         ▼
                   ┌──────────┐
                   │  Store   │ ← processed/{device_id}_{timestamp}.json
                   │          │
                   └──────────┘
```

**Key Points:**
- Atomic writes (temp file → rename)
- No partial data
- Rejected data saved for analysis

---

### Analytics Pipeline (Phase 2)

```
┌──────────────┐
│  Telemetry   │ ← List of validated records
│   Records    │
└──────┬───────┘
       │
       ├─────────────┬─────────────┬─────────────┐
       │             │             │             │
       ▼             ▼             ▼             ▼
  ┌────────┐   ┌────────┐   ┌─────────┐   ┌─────────┐
  │Metrics │   │ Trends │   │Anomalies│   │Summaries│
  │        │   │        │   │         │   │         │
  │- Mean  │   │- SMA   │   │- Z-score│   │- Status │
  │- P90   │   │- Slope │   │- IQR    │   │- Reasons│
  └────────┘   └────────┘   └─────────┘   └────┬────┘
                                                │
                                                ▼
                                          ┌──────────┐
                                          │  Report  │
                                          │  JSON    │
                                          └──────────┘
```

**Key Points:**
- Independent modules (metrics doesn't depend on trends)
- Summaries combine all insights
- Output is actionable (status + recommendations)

---

## 🛡️ Error Handling Strategy

### Levels of Error Handling

| Level | Scope | Action | Example |
|-------|-------|--------|---------|
| **Validation** | Single field | Reject + explain | "cpu_usage must be float in [0, 100]" |
| **Record** | Entire telemetry | Reject + log + store | Store rejected record with all errors |
| **Batch** | Multiple records | Continue + track stats | "98 accepted, 2 rejected" |
| **Analytics** | Metric calculation | Log warning + skip | "Z-score failed: insufficient data" |
| **System** | Critical failure | Fail loudly + alert | Database unreachable |

### Error Context

Every error includes:
- **Field** — What was wrong?
- **Value** — What did we receive?
- **Reason** — Why is it wrong?
- **Expected** — What should it be?

```python
ValidationError(
    field='cpu_usage',
    value=150.0,
    reason='Value 150.0 exceeds maximum 100.0',
    expected='Value <= 100.0'
)
```

---

## 📈 Scalability Considerations

### Current Scale (Phase 1-2)
- **Target:** Thousands of devices
- **Volume:** Millions of telemetry records
- **Storage:** File-based (JSON)
- **Processing:** Batch-oriented

### Future Scale (Phase 4+)
- **Target:** Millions of devices
- **Volume:** Billions of telemetry records
- **Storage:** Time-series database (InfluxDB, TimescaleDB)
- **Processing:** Stream-oriented (Kafka, Flink)

### Design Decisions for Scale

| Decision | Current | Future |
|----------|---------|--------|
| **Storage** | JSON files | Time-series DB |
| **Indexing** | Filename (device_id + timestamp) | Database indexes |
| **Query** | File I/O | SQL/InfluxQL |
| **Aggregation** | In-memory | Database aggregation |
| **Caching** | None | Redis for summaries |

**Why file-based now:**
- Simple to debug
- No database setup
- Easy to inspect rejected data
- Sufficient for demo/interview

**When to switch:**
- >100K devices
- Real-time analytics needed
- Query performance matters

---

## 🧪 Testing Strategy

### Phase 1 Testing (Ingestion)

**Test Cases:**
1. **Valid data passes** — All fields correct
2. **Invalid types** — String instead of float
3. **Out of range** — Values outside bounds
4. **Missing fields** — Required field absent
5. **Malformed data** — Invalid UUID, bad timestamp
6. **Edge cases** — Empty string, NaN, infinity, negative values

**Test Data Generation:**
```python
# Intentional corruption for testing
corrupted = TelemetryGenerator.generate_corrupted_telemetry('wrong_types')
# Should be rejected by validator
```

### Phase 2 Testing (Analytics)

**Test Cases:**
1. **Normal distribution** — Standard bell curve
2. **Skewed distribution** — Long tail
3. **Empty inputs** — Handle gracefully
4. **Extreme values** — Very large/small numbers
5. **Time gaps** — Missing data points in time series
6. **Single point** — Insufficient data for some metrics

**Example:**
```python
# Test Z-score with skewed data
data = [10, 10, 11, 10, 11, 100]  # 100 is outlier
anomalies = AnomalyDetector.z_score_detection(data, threshold=2.0)
assert 5 in anomalies  # Index 5 (value 100) should be detected
```

---

## 🔐 Privacy & Security Considerations

### Privacy-First Design

**No PII in telemetry:**
- Device ID is UUID (not serial number)
- No user names, emails, or locations
- App names are generic (Safari, Mail, etc.)
- Aggregated metrics only

**Data Retention:**
- Clear retention policies (TBD: 30/90/365 days)
- Automatic deletion of old telemetry
- Anonymization for long-term storage

**Apple Alignment:**  
Apple's differential privacy approach — aggregate insights without individual tracking.

---

## 📝 Tradeoffs Summary

| Decision | Pro | Con | Apple Priority |
|----------|-----|-----|----------------|
| **Schema-First** | Reliability, clarity | Upfront work | ✅ Reliability |
| **Fail-Fast** | Catch errors early | Higher rejection | ✅ Data quality |
| **Percentiles** | Robust metrics | Complex | ✅ Tail behavior |
| **File Storage** | Simple, debuggable | Doesn't scale | ⚠️ Prototype OK |
| **No ML Yet** | Explainable | Less sophisticated | ✅ Trust first |
| **Logs > GUI** | Production-ready | Less visual | ✅ Observability |

---

## 🔜 Future Enhancements

### Phase 3: ML Integration
- **Isolation Forest** for anomaly detection
- **ARIMA/Prophet** for forecasting
- **Explainability:** SHAP values, feature importance

### Phase 4: Java API
- **Spring Boot** REST API
- **Custom exceptions** (no generic 500s)
- **OpenAPI** documentation
- **Rate limiting** and **authentication**

### Phase 5: C++ Optimization
- **Performance-critical** aggregation
- **Memory-efficient** data structures
- **SIMD** optimizations for metrics

---

## 🎯 Conclusion

This architecture demonstrates **Apple-grade engineering:**

- ✅ **Reliability** — Fail-fast validation, explicit errors
- ✅ **Scalability** — Schema-first, separation of concerns
- ✅ **Observability** — Comprehensive logging, metrics tracking
- ✅ **Maintainability** — Clear boundaries, testable modules
- ✅ **Privacy** — No PII, aggregate metrics only

**Not** overengineered — every decision has a clear reason.  
**Not** underengineered — production-minded from day one.

This is how Apple builds reliable systems. 🍎
