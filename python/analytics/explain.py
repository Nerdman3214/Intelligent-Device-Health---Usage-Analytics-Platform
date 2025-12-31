"""
Model Explainability for Device Health Predictions

Apple principle: Every prediction must be explainable to engineers.

Provides:
- Global feature importance
- Per-prediction SHAP values
- Human-readable explanations

Author: Software Engineering Intern
Purpose: Make ML predictions interpretable and actionable
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path
import numpy as np

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logging.warning("SHAP not available - limited explainability")

from .train import ModelTrainer
from .predict import RiskPredictor
from .labels import DeviceRisk

logger = logging.getLogger(__name__)


@dataclass
class Explanation:
    """
    Explanation for a single prediction.
    
    Contains both global and local explanations.
    """
    device_id: str
    predicted_risk: str
    top_contributing_features: List[Dict[str, Any]]
    feature_values: Dict[str, float]
    explanation_text: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'device_id': self.device_id,
            'predicted_risk': self.predicted_risk,
            'top_contributing_features': self.top_contributing_features,
            'feature_values': self.feature_values,
            'explanation_text': self.explanation_text
        }


class ModelExplainer:
    """
    Generate explanations for predictions.
    
    Uses SHAP when available, falls back to feature importance.
    """
    
    def __init__(
        self,
        predictor: RiskPredictor,
        use_shap: bool = True
    ):
        """
        Initialize explainer.
        
        Args:
            predictor: Trained predictor
            use_shap: Whether to use SHAP (if available)
        """
        self.predictor = predictor
        self.trainer = predictor.trainer
        self.feature_names = predictor.feature_names
        
        self.use_shap = use_shap and SHAP_AVAILABLE
        self.shap_explainer = None
        
        if self.use_shap:
            self._initialize_shap()
    
    def _initialize_shap(self):
        """Initialize SHAP explainer"""
        try:
            # Get base estimator from calibrated classifier
            base_estimator = (
                self.trainer.model.calibrated_classifiers_[0].estimator
            )
            
            # Create SHAP explainer based on model type
            model_type = self.trainer.config.model_type
            
            if model_type in ['random_forest', 'gradient_boosting']:
                # Tree-based models use TreeExplainer
                self.shap_explainer = shap.TreeExplainer(base_estimator)
            else:
                # Linear models use LinearExplainer or KernelExplainer
                # For simplicity, use KernelExplainer (model-agnostic)
                # Note: This requires background data
                logger.info(
                    "Using KernelExplainer (slower but model-agnostic)"
                )
                self.shap_explainer = None  # Initialize with background later
            
            logger.info(f"SHAP initialized for {model_type}")
        except Exception as e:
            logger.warning(f"SHAP initialization failed: {e}")
            self.use_shap = False
    
    def explain_prediction(
        self,
        device_id: str,
        features: Dict[str, float],
        prediction: Optional[Any] = None,
        top_n: int = 5
    ) -> Explanation:
        """
        Generate explanation for a prediction.
        
        Args:
            device_id: Device identifier
            features: Feature dictionary
            prediction: Optional prediction result
            top_n: Number of top features to include
            
        Returns:
            Explanation with top contributing features
        """
        # Get prediction if not provided
        if prediction is None:
            prediction = self.predictor.predict(device_id, features)
        
        # Prepare feature vector
        X = np.array([
            features[name] for name in self.feature_names
        ]).reshape(1, -1)
        
        # Get feature contributions
        if self.use_shap and self.shap_explainer is not None:
            contributions = self._get_shap_contributions(X)
        else:
            contributions = self._get_importance_contributions()
        
        # Sort by absolute contribution
        sorted_features = sorted(
            contributions.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )[:top_n]
        
        top_features = [
            {
                'feature': name,
                'value': float(features[name]),
                'contribution': float(contrib),
                'direction': 'increases' if contrib > 0 else 'decreases'
            }
            for name, contrib in sorted_features
        ]
        
        # Generate human-readable explanation
        explanation_text = self._generate_explanation_text(
            prediction.predicted_risk,
            top_features,
            features
        )
        
        return Explanation(
            device_id=device_id,
            predicted_risk=prediction.predicted_risk.name,
            top_contributing_features=top_features,
            feature_values=features,
            explanation_text=explanation_text
        )
    
    def _get_shap_contributions(
        self,
        X: np.ndarray
    ) -> Dict[str, float]:
        """Get SHAP values as feature contributions"""
        # Scale features
        X_scaled = self.trainer.scaler.transform(X)
        
        # Compute SHAP values
        shap_values = self.shap_explainer.shap_values(X_scaled)
        
        # For multi-class, use values for predicted class
        if isinstance(shap_values, list):
            predicted_class = self.trainer.model.predict(X_scaled)[0]
            shap_values = shap_values[predicted_class]
        
        # Map to feature names
        contributions = {
            name: float(val)
            for name, val in zip(self.feature_names, shap_values[0])
        }
        
        return contributions
    
    def _get_importance_contributions(self) -> Dict[str, float]:
        """
        Fallback: use feature importance as proxy for contributions.
        
        Note: This is global importance, not instance-specific.
        """
        importance = self.trainer.get_feature_importance()
        
        if importance is None:
            # If no importance available, return uniform
            return {name: 1.0 / len(self.feature_names)
                   for name in self.feature_names}
        
        return importance
    
    def _generate_explanation_text(
        self,
        risk: DeviceRisk,
        top_features: List[Dict[str, Any]],
        features: Dict[str, float]
    ) -> str:
        """
        Generate human-readable explanation.
        
        Args:
            risk: Predicted risk level
            top_features: Top contributing features
            features: All feature values
            
        Returns:
            Human-readable explanation string
        """
        lines = [f"Device risk level: {risk.name}"]
        lines.append("\nKey factors:")
        
        for i, feat in enumerate(top_features, 1):
            name = feat['feature']
            value = feat['value']
            direction = feat['direction']
            
            # Make feature names human-readable
            readable_name = name.replace('_', ' ').title()
            
            # Add context based on feature type
            if 'battery' in name:
                if value < 0.85:
                    context = "below healthy threshold"
                else:
                    context = f"at {value:.1%}"
            elif 'p90' in name or 'p95' in name:
                context = f"90th percentile at {value:.1f}%"
            elif 'ratio' in name:
                context = f"{value*100:.1f}% of samples"
            elif 'slope' in name:
                context = f"trending at {value:.4f}/day"
            else:
                context = f"value: {value:.2f}"
            
            lines.append(
                f"{i}. {readable_name} ({context}) "
                f"{direction} risk"
            )
        
        return '\n'.join(lines)
    
    def get_global_importance(
        self,
        top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get global feature importance ranking.
        
        Args:
            top_n: Number of top features to return
            
        Returns:
            List of features with importance scores
        """
        importance = self.trainer.get_feature_importance()
        
        if importance is None:
            return []
        
        sorted_features = sorted(
            importance.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]
        
        return [
            {
                'feature': name,
                'importance': float(score),
                'readable_name': name.replace('_', ' ').title()
            }
            for name, score in sorted_features
        ]
