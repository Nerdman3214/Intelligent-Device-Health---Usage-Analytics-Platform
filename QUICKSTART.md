# Quick Start Guide

## Running the Demo

### Option 1: Run Complete Demo
```bash
cd python
python demo.py
```

This will:
1. Generate 50 telemetry records (90% clean, 10% corrupted)
2. Run ingestion pipeline with validation
3. Show acceptance/rejection statistics
4. Analyze metrics (mean, median, P90, P95, P99)
5. Detect anomalies using Z-score and IQR
6. Generate device health summary

### Option 2: Python REPL

```python
# Add python/ to your path or run from python/ directory
import sys
sys.path.insert(0, './python')

# Phase 1: Generate and ingest data
from ingestion import TelemetryGenerator, TelemetryIngestor

generator = TelemetryGenerator()
data = generator.generate_batch(count=20, quality='clean')

ingestor = TelemetryIngestor(data_dir='./data')
result = ingestor.ingest_batch(data)
print(f"Accepted: {result['accepted']}, Rejected: {result['rejected']}")

# Phase 2: Analyze data
from analytics import TelemetryMetrics, SummaryGenerator

# Calculate metrics
metrics = TelemetryMetrics.calculate_telemetry_summary(data, 'cpu_usage')
print(f"CPU Usage - Mean: {metrics['mean']:.2f}, P90: {metrics['p90']:.2f}")

# Generate summary
summary = SummaryGenerator.generate_device_summary(
    device_id=data[0]['device_id'],
    telemetry_records=data
)
print(f"Status: {summary.status.value.upper()}")
print(f"Reasons: {summary.reasons}")
```

### Option 3: Generate Time-Series Data

```python
from ingestion import TelemetryGenerator

# Generate 30 days of telemetry (24 samples/day)
device_id = '550e8400-e29b-41d4-a716-446655440000'
time_series = TelemetryGenerator.generate_time_series(
    device_id=device_id,
    duration_days=30,
    samples_per_day=24,
    simulate_degradation=True  # Battery health degrades over time
)

# Analyze trends
from analytics import TrendAnalyzer, TimeSeriesPoint

battery_ts = [
    TimeSeriesPoint(r['timestamp'], r['battery_health'])
    for r in time_series
]

trend = TrendAnalyzer.estimate_slope(battery_ts, normalize_time=True)
print(f"Battery health trend: {trend['trend']}")
print(f"Degradation rate: {trend['slope']:.6f} per day")
```

## Testing Defensive Validation

```python
from ingestion import TelemetryGenerator, TelemetryValidator

# Generate intentionally corrupted data
corrupted = TelemetryGenerator.generate_corrupted_telemetry('out_of_range')

# Validate (should fail)
result = TelemetryValidator.validate_telemetry(corrupted)
if not result.valid:
    print("Validation failed as expected:")
    for error in result.errors:
        print(f"  - {error}")
```

## Understanding the Output

### Ingestion Stats
```
Total Processed: 50
✅ Accepted: 45
❌ Rejected: 5
Acceptance Rate: 90.0%

REJECTION BREAKDOWN:
  - Invalid cpu_usage: 2
  - Invalid device_id: 1
  - Invalid battery_health: 2
```

### Metrics Output
```
CPU USAGE:
   Mean:   45.23
   Median: 42.10
   P90:    78.50
   P95:    85.30
   P99:    92.10
   Range:  [5.20, 98.40]
```

### Device Summary
```json
{
  "device_id": "550e8400-...",
  "status": "DEGRADED",
  "confidence": 0.91,
  "reasons": [
    "Battery health is degraded",
    "Battery degrading faster than expected (1.2% per month)",
    "CPU usage is elevated (P90: 78.5%)"
  ],
  "recommendations": [
    "Consider battery replacement or service",
    "Investigate high CPU usage applications"
  ]
}
```

## File Structure After Running

```
data/
├── processed/
│   ├── 550e8400-..._20231228_143052.json  ← Validated telemetry
│   ├── 550e8400-..._20231228_143053.json
│   └── ...
└── rejected/
    ├── rejected_20231228_143052_123456.json  ← Invalid with errors
    └── ...

reports/
└── summary_550e8400.json  ← Device health summary
```

## Next Steps

1. **Explore the code** — Read the docstrings, they're comprehensive
2. **Run tests** (TODO) — `pytest python/tests/`
3. **Modify thresholds** — Try different Z-score or IQR thresholds
4. **Generate larger datasets** — Test with 1000+ records
5. **Implement Phase 3** — Add simple ML models
6. **Build Java API (Phase 4)** — Spring Boot REST API

## Common Issues

**Import errors?**
```bash
# Make sure you're in the right directory
cd "Intelligent Device Health & Usage Analytics Platform"
export PYTHONPATH="${PYTHONPATH}:$(pwd)/python"
```

**No data showing up?**
```bash
# Check data directories exist
ls -la data/processed/
ls -la data/rejected/
```

**Want more verbose output?**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Interview Talking Points

After running this demo, you can say:

> "I built a device telemetry analytics system that processes data through a defensive validation pipeline. The system rejects invalid data with explicit error messages, calculates robust statistical metrics like P90/P95/P99, detects anomalies using Z-scores and IQR, and generates actionable device health summaries with confidence scores. All without machine learning — just solid statistics and defensive programming."

🍎 Apple-approved engineering.
