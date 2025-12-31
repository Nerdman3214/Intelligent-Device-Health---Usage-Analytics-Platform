"""
Model Evaluation and Validation

Apple principle: Measure what matters for production use.

Metrics:
- Classification: Precision, Recall, F1
- Ranking: ROC-AUC
- Calibration: Brier score, calibration curve
- Confusion matrix analysis

Author: Software Engineering Intern
Purpose: Comprehensive model validation
"""

import logging
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    roc_auc_score,
    confusion_matrix,
    brier_score_loss,
    classification_report
)

from .labels import DeviceRisk

logger = logging.getLogger(__name__)


@dataclass
class EvaluationMetrics:
    """Comprehensive evaluation metrics"""
    
    # Classification metrics
    accuracy: float
    precision_macro: float
    recall_macro: float
    f1_macro: float
    
    # Per-class metrics
    per_class_metrics: Dict[str, Dict[str, float]]
    
    # Confusion matrix
    confusion_matrix: List[List[int]]
    
    # Calibration
    brier_score: float
    
    # ROC-AUC (for binary/multiclass)
    roc_auc: float
    
    # Sample counts
    n_samples: int
    class_distribution: Dict[str, int]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'accuracy': self.accuracy,
            'precision_macro': self.precision_macro,
            'recall_macro': self.recall_macro,
            'f1_macro': self.f1_macro,
            'per_class_metrics': self.per_class_metrics,
            'confusion_matrix': self.confusion_matrix,
            'brier_score': self.brier_score,
            'roc_auc': self.roc_auc,
            'n_samples': self.n_samples,
            'class_distribution': self.class_distribution
        }
    
    def summary(self) -> str:
        """Generate human-readable summary"""
        lines = [
            "=== Model Evaluation Summary ===",
            f"Samples: {self.n_samples}",
            f"Accuracy: {self.accuracy:.3f}",
            f"Precision (macro): {self.precision_macro:.3f}",
            f"Recall (macro): {self.recall_macro:.3f}",
            f"F1 (macro): {self.f1_macro:.3f}",
            f"ROC-AUC: {self.roc_auc:.3f}",
            f"Brier Score: {self.brier_score:.3f}",
            "",
            "Per-Class Performance:"
        ]
        
        for class_name, metrics in self.per_class_metrics.items():
            lines.append(
                f"  {class_name}: "
                f"P={metrics['precision']:.3f} "
                f"R={metrics['recall']:.3f} "
                f"F1={metrics['f1']:.3f}"
            )
        
        lines.append("")
        lines.append("Confusion Matrix:")
        for row in self.confusion_matrix:
            lines.append("  " + " ".join(f"{val:4d}" for val in row))
        
        return "\n".join(lines)


class ModelEvaluator:
    """
    Evaluate model performance on test data.
    
    Provides comprehensive metrics for production readiness.
    """
    
    @staticmethod
    def evaluate(
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_proba: np.ndarray
    ) -> EvaluationMetrics:
        """
        Compute comprehensive evaluation metrics.
        
        Args:
            y_true: True labels
            y_pred: Predicted labels
            y_proba: Predicted probabilities (n_samples, n_classes)
            
        Returns:
            EvaluationMetrics with all scores
        """
        # Basic metrics
        accuracy = accuracy_score(y_true, y_pred)
        
        precision, recall, f1, support = precision_recall_fscore_support(
            y_true,
            y_pred,
            average='macro',
            zero_division=0
        )
        
        # Per-class metrics
        (
            precision_per_class,
            recall_per_class,
            f1_per_class,
            support_per_class
        ) = precision_recall_fscore_support(
            y_true,
            y_pred,
            average=None,
            zero_division=0
        )
        
        per_class_metrics = {}
        for i in range(len(precision_per_class)):
            risk_name = DeviceRisk(i).name
            per_class_metrics[risk_name] = {
                'precision': float(precision_per_class[i]),
                'recall': float(recall_per_class[i]),
                'f1': float(f1_per_class[i]),
                'support': int(support_per_class[i])
            }
        
        # Confusion matrix
        cm = confusion_matrix(y_true, y_pred)
        
        # ROC-AUC (multiclass)
        try:
            roc_auc = roc_auc_score(
                y_true,
                y_proba,
                multi_class='ovr',
                average='macro'
            )
        except ValueError:
            # Handle case where not all classes are present
            roc_auc = 0.0
        
        # Calibration (Brier score)
        # For multiclass, compute average Brier score
        brier_scores = []
        for i in range(y_proba.shape[1]):
            y_true_binary = (y_true == i).astype(int)
            y_proba_class = y_proba[:, i]
            brier = brier_score_loss(y_true_binary, y_proba_class)
            brier_scores.append(brier)
        
        brier_score = float(np.mean(brier_scores))
        
        # Class distribution
        unique, counts = np.unique(y_true, return_counts=True)
        class_dist = {
            DeviceRisk(int(cls)).name: int(count)
            for cls, count in zip(unique, counts)
        }
        
        return EvaluationMetrics(
            accuracy=float(accuracy),
            precision_macro=float(precision),
            recall_macro=float(recall),
            f1_macro=float(f1),
            per_class_metrics=per_class_metrics,
            confusion_matrix=cm.tolist(),
            brier_score=brier_score,
            roc_auc=float(roc_auc),
            n_samples=len(y_true),
            class_distribution=class_dist
        )
    
    @staticmethod
    def evaluate_predictions(
        predictions: List[Dict[str, Any]],
        true_labels: List[Dict[str, Any]]
    ) -> EvaluationMetrics:
        """
        Evaluate predictions against true labels.
        
        Args:
            predictions: List of prediction dictionaries
            true_labels: List of label dictionaries
            
        Returns:
            EvaluationMetrics
        """
        if len(predictions) != len(true_labels):
            raise ValueError(
                f"Prediction/label count mismatch: {len(predictions)} vs "
                f"{len(true_labels)}"
            )
        
        # Extract arrays
        y_true = np.array([
            label['risk_level'] for label in true_labels
        ], dtype=np.int32)
        
        y_pred = np.array([
            pred['predicted_risk'] for pred in predictions
        ], dtype=np.int32)
        
        # Build probability matrix
        n_classes = 3  # HEALTHY, AT_RISK, DEGRADED
        y_proba = np.zeros((len(predictions), n_classes))
        
        for i, pred in enumerate(predictions):
            probs = pred['probabilities']
            for risk_name, prob in probs.items():
                class_idx = DeviceRisk[risk_name].value
                y_proba[i, class_idx] = prob
        
        return ModelEvaluator.evaluate(y_true, y_pred, y_proba)
    
    @staticmethod
    def get_classification_report(
        y_true: np.ndarray,
        y_pred: np.ndarray
    ) -> str:
        """
        Get sklearn classification report.
        
        Args:
            y_true: True labels
            y_pred: Predicted labels
            
        Returns:
            Classification report string
        """
        target_names = [risk.name for risk in DeviceRisk]
        
        return classification_report(
            y_true,
            y_pred,
            target_names=target_names,
            zero_division=0
        )
    
    @staticmethod
    def analyze_confidence_calibration(
        predictions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze prediction confidence calibration.
        
        Args:
            predictions: List of prediction dictionaries
            
        Returns:
            Calibration analysis
        """
        confidences = [pred['confidence'] for pred in predictions]
        is_confident = [pred['is_confident'] for pred in predictions]
        
        return {
            'mean_confidence': float(np.mean(confidences)),
            'median_confidence': float(np.median(confidences)),
            'min_confidence': float(np.min(confidences)),
            'max_confidence': float(np.max(confidences)),
            'confident_predictions_pct': (
                float(np.mean(is_confident)) * 100
            ),
            'confidence_distribution': {
                'below_0.6': sum(1 for c in confidences if c < 0.6),
                '0.6_to_0.8': sum(1 for c in confidences if 0.6 <= c < 0.8),
                '0.8_to_0.9': sum(1 for c in confidences if 0.8 <= c < 0.9),
                'above_0.9': sum(1 for c in confidences if c >= 0.9)
            }
        }
