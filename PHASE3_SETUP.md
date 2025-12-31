# Phase 3 Setup Guide

## Quick Start

### 1. Install Dependencies

Phase 3 requires machine learning libraries:

```bash
# Install Phase 3 dependencies
pip install -r requirements.txt
```

This installs:
- **scikit-learn**: Explainable ML models (Logistic Regression, Random Forest, Gradient Boosting)
- **numpy**: Numerical computing
- **joblib**: Model serialization
- **shap** (optional): Advanced model explainability

### 2. Run Phase 3 Demo

```bash
# Run the full ML pipeline demo
python demo_phase3.py
```

This demonstrates:
1. **Feature Extraction**: 22 interpretable features from telemetry
2. **Risk Labeling**: Transparent rule-based labels (HEALTHY, AT_RISK, DEGRADED)
3. **Model Training**: Train 3 models with cross-validation
4. **Predictions**: Inference with confidence scores
5. **Explanations**: Feature importance and contribution analysis
6. **Evaluation**: Comprehensive metrics (precision, recall, F1, ROC-AUC)

## What Phase 3 Adds

### Core Components

| Module | Purpose |
|--------|---------|
| `features.py` | Extract 22 interpretable features from telemetry |
| `labels.py` | Generate risk labels using transparent rules |
| `train.py` | Train explainable ML models with calibration |
| `predict.py` | Make predictions with confidence + OOD detection |
| `explain.py` | Explain predictions with feature attribution |
| `evaluate.py` | Comprehensive model evaluation |

### Apple Principles Applied

1. **Explainability First**
   - NO deep learning (by design)
   - Only interpretable models: Logistic Regression, Random Forest, Gradient Boosting
   - Every prediction includes feature importance

2. **Defensive ML**
   - Out-of-distribution (OOD) detection
   - Confidence thresholding (flag uncertain predictions)
   - Calibrated probabilities (Platt scaling)

3. **Production Safety**
   - Minimum sample requirements (20 per class)
   - Feature validation (no NaN/Inf)
   - Model versioning and metadata tracking

## Example Usage

### Train a Model

```python
from python.analytics.features import FeatureExtractor
from python.analytics.labels import RiskLabeler
from python.analytics.train import ModelTrainer, TrainingConfig

# Extract features from telemetry
extractor = FeatureExtractor()
features = extractor.extract_features(telemetry_records)

# Generate risk labels
labels = RiskLabeler.label_from_features(device_id, features.features)

# Train model
config = TrainingConfig(model_type='gradient_boosting')
trainer = ModelTrainer(config)
metrics = trainer.train(features_list, labels_list)

# Save model
model_path = trainer.save('models/')
```

### Make Predictions

```python
from python.analytics.predict import RiskPredictor
from python.analytics.explain import ModelExplainer

# Load trained model
predictor = RiskPredictor('models/gradient_boosting_20240115_120000.pkl')

# Predict
prediction = predictor.predict(device_id, features)
print(f"Risk: {prediction.predicted_risk.name}")
print(f"Confidence: {prediction.confidence:.2f}")

# Explain
explainer = ModelExplainer(predictor)
explanation = explainer.explain_prediction(device_id, features, prediction)
print(explanation.explanation_text)
```

## Model Comparison

| Model | Interpretability | Performance | Speed |
|-------|-----------------|-------------|-------|
| Logistic Regression | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Random Forest | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Gradient Boosting | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |

**Recommendation**: Use Gradient Boosting for best performance, Logistic Regression for maximum interpretability.

## Feature Engineering

### 22 Interpretable Features

**Battery (3 features)**
- `battery_health_mean`: Average battery health
- `battery_health_std`: Battery health variability
- `battery_health_trend_slope`: Degradation rate

**CPU (5 features)**
- `cpu_usage_mean`, `cpu_usage_p90`: Utilization metrics
- `cpu_usage_std`: Usage variability
- `cpu_usage_trend_slope`: Trending
- `cpu_usage_spike_count`: Anomaly count

**Memory (4 features)**
- Similar structure to CPU features

**Thermal (4 features)**
- `thermal_critical_ratio`: % of critical thermal events
- `thermal_serious_or_worse_ratio`: % of serious+ events
- `thermal_nominal_ratio`: % of normal thermal state
- `thermal_variability`: Thermal state changes

**Usage Patterns (6 features)**
- `sample_count`: Data volume
- `time_range_days`: Observation period
- `samples_per_day`: Data density
- `weekend_ratio`: Weekend vs weekday usage
- `recent_activity_ratio`: Recent usage patterns
- `inactive_ratio`: Idle time

All features have clear business meaning (Apple requirement).

## Next Steps

After Phase 3:
- **Phase 4**: Java Spring Boot REST API
- **Phase 5**: C++ optimization for hot paths
- **Testing**: Unit tests for all modules
- **Documentation**: API docs and architecture guide

## Interview Talking Points

**What makes this Phase 3 special?**

1. **Explainable by design**: Every prediction can be justified
2. **Production-ready**: OOD detection, confidence scores, calibration
3. **Defensive programming**: Extensive validation at every layer
4. **Apple principles**: Transparency, reliability, user trust

**Technical depth demonstrated:**
- Feature engineering (domain knowledge)
- Model selection (tradeoff analysis)
- Calibration (probability theory)
- Explainability (SHAP, feature importance)
- Evaluation (precision/recall, ROC curves)

This is NOT a Kaggle competition project — it's production ML.
