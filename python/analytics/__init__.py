"""
Analytics Layer - Phase 2 & Phase 3

Phase 2: Statistical analysis WITHOUT machine learning
Phase 3: Predictive analytics WITH explainable ML
"""

# Phase 2: Statistical Analytics
from .metrics import TelemetryMetrics, MetricsError
from .trends import TrendAnalyzer, TimeSeriesPoint, TrendsError
from .anomalies import (
    AnomalyDetector,
    Anomaly,
    AnomalySeverity,
    AnomalyType
)
from .summaries import (
    SummaryGenerator,
    DeviceHealthSummary,
    DeviceStatus
)

# Phase 3: Predictive Analytics
from .features import FeatureExtractor, DeviceFeatures, FeatureExtractionError
from .labels import RiskLabeler, DeviceRisk, RiskLabel
from .train import ModelTrainer, TrainingConfig, TrainingError
from .predict import RiskPredictor, RiskPrediction, PredictionError
from .explain import ModelExplainer, Explanation
from .evaluate import ModelEvaluator, EvaluationMetrics

__all__ = [
    # Phase 2
    'TelemetryMetrics',
    'MetricsError',
    'TrendAnalyzer',
    'TimeSeriesPoint',
    'TrendsError',
    'AnomalyDetector',
    'Anomaly',
    'AnomalySeverity',
    'AnomalyType',
    'SummaryGenerator',
    'DeviceHealthSummary',
    'DeviceStatus',
    # Phase 3
    'FeatureExtractor',
    'DeviceFeatures',
    'FeatureExtractionError',
    'RiskLabeler',
    'DeviceRisk',
    'RiskLabel',
    'ModelTrainer',
    'TrainingConfig',
    'TrainingError',
    'RiskPredictor',
    'RiskPrediction',
    'PredictionError',
    'ModelExplainer',
    'Explanation',
    'ModelEvaluator',
    'EvaluationMetrics',
]
