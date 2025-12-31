"""
Inference and Prediction for Device Health Risk

Apple principle: Every prediction must include confidence and explanation.

Defensive predictions:
- Reject out-of-distribution inputs
- Flag low confidence predictions
- Always calibrate probabilities

Author: Software Engineering Intern
Purpose: Production-safe inference with uncertainty quantification
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path
import numpy as np

from .train import ModelTrainer
from .labels import DeviceRisk

logger = logging.getLogger(__name__)


class PredictionError(Exception):
    """Raised when prediction validation fails"""
    pass


@dataclass
class RiskPrediction:
    """
    Prediction result with full context.
    
    Apple principle: Always return interpretable results.
    """
    device_id: str
    predicted_risk: DeviceRisk
    probabilities: Dict[str, float]  # {risk_name: probability}
    confidence: float  # Max probability
    is_confident: bool  # Confidence > threshold
    is_in_distribution: bool  # Within training data range
    warnings: List[str]  # Any issues flagged
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'device_id': self.device_id,
            'predicted_risk': self.predicted_risk.value,
            'predicted_risk_name': self.predicted_risk.name,
            'probabilities': self.probabilities,
            'confidence': self.confidence,
            'is_confident': self.is_confident,
            'is_in_distribution': self.is_in_distribution,
            'warnings': self.warnings
        }


class RiskPredictor:
    """
    Make predictions with defensive validation.
    
    Checks:
    - Input feature validity
    - Distribution shift detection
    - Confidence thresholding
    """
    
    # Confidence threshold for flagging uncertain predictions
    CONFIDENCE_THRESHOLD = 0.6
    
    # Out-of-distribution detection (z-score threshold)
    OOD_Z_THRESHOLD = 3.0
    
    def __init__(self, model_path: Path):
        """
        Load trained model.
        
        Args:
            model_path: Path to saved model file
        """
        self.trainer = ModelTrainer.load(model_path)
        self.feature_names = self.trainer.feature_names
        
        # Cache training statistics for OOD detection
        self._training_mean = None
        self._training_std = None
    
    def predict(
        self,
        device_id: str,
        features: Dict[str, float]
    ) -> RiskPrediction:
        """
        Predict device risk from features.
        
        Args:
            device_id: Device identifier
            features: Dictionary of feature values
            
        Returns:
            RiskPrediction with probabilities and confidence
        """
        warnings = []
        
        # Prepare feature vector
        try:
            X = self._prepare_feature_vector(features)
        except Exception as e:
            raise PredictionError(f"Feature preparation failed: {e}")
        
        # Check for out-of-distribution
        is_in_dist = self._check_distribution(X, warnings)
        
        # Scale features
        X_scaled = self.trainer.scaler.transform(X.reshape(1, -1))
        
        # Get predictions
        proba = self.trainer.model.predict_proba(X_scaled)[0]
        predicted_class = int(self.trainer.model.predict(X_scaled)[0])
        
        # Convert to risk levels
        predicted_risk = DeviceRisk(predicted_class)
        confidence = float(np.max(proba))
        
        probabilities = {
            DeviceRisk(i).name: float(proba[i])
            for i in range(len(proba))
        }
        
        # Check confidence
        is_confident = confidence >= self.CONFIDENCE_THRESHOLD
        if not is_confident:
            warnings.append(
                f"Low confidence prediction ({confidence:.2f} < "
                f"{self.CONFIDENCE_THRESHOLD})"
            )
        
        return RiskPrediction(
            device_id=device_id,
            predicted_risk=predicted_risk,
            probabilities=probabilities,
            confidence=confidence,
            is_confident=is_confident,
            is_in_distribution=is_in_dist,
            warnings=warnings
        )
    
    def predict_batch(
        self,
        features_list: List[Dict[str, Any]]
    ) -> List[RiskPrediction]:
        """
        Predict risk for multiple devices.
        
        Args:
            features_list: List of feature dictionaries
            
        Returns:
            List of RiskPredictions
        """
        predictions = []
        
        for feat_dict in features_list:
            device_id = feat_dict.get('device_id', 'UNKNOWN')
            features = feat_dict.get('features', feat_dict)
            
            try:
                prediction = self.predict(device_id, features)
                predictions.append(prediction)
            except Exception as e:
                logger.error(f"Prediction failed for {device_id}: {e}")
                # Create error prediction
                predictions.append(RiskPrediction(
                    device_id=device_id,
                    predicted_risk=DeviceRisk.HEALTHY,
                    probabilities={risk.name: 0.0 for risk in DeviceRisk},
                    confidence=0.0,
                    is_confident=False,
                    is_in_distribution=False,
                    warnings=[f"Prediction error: {str(e)}"]
                ))
        
        return predictions
    
    def _prepare_feature_vector(
        self,
        features: Dict[str, float]
    ) -> np.ndarray:
        """
        Convert feature dict to numpy array in correct order.
        
        Args:
            features: Dictionary of feature values
            
        Returns:
            numpy array of features
        """
        # Check for missing features
        missing = [
            name for name in self.feature_names
            if name not in features
        ]
        
        if missing:
            raise PredictionError(
                f"Missing required features: {missing}"
            )
        
        # Extract in correct order
        feature_vector = np.array([
            features[name] for name in self.feature_names
        ], dtype=np.float64)
        
        # Check for invalid values
        if np.any(np.isnan(feature_vector)):
            raise PredictionError("Feature vector contains NaN values")
        
        if np.any(np.isinf(feature_vector)):
            raise PredictionError("Feature vector contains infinite values")
        
        return feature_vector
    
    def _check_distribution(
        self,
        X: np.ndarray,
        warnings: List[str]
    ) -> bool:
        """
        Check if input is within training distribution.
        
        Simple approach: compute z-scores against training data.
        
        Args:
            X: Feature vector
            warnings: List to append warnings to
            
        Returns:
            True if in distribution, False otherwise
        """
        # Use scaler statistics as proxy for training distribution
        if self.trainer.scaler is None:
            warnings.append("Cannot check distribution (no scaler)")
            return True
        
        mean = self.trainer.scaler.mean_
        scale = self.trainer.scaler.scale_
        
        # Compute z-scores
        z_scores = np.abs((X - mean) / scale)
        max_z = np.max(z_scores)
        
        if max_z > self.OOD_Z_THRESHOLD:
            # Find which features are out of distribution
            ood_features = [
                self.feature_names[i]
                for i in range(len(z_scores))
                if z_scores[i] > self.OOD_Z_THRESHOLD
            ]
            
            warnings.append(
                f"Out-of-distribution features: {ood_features} "
                f"(max z-score: {max_z:.2f})"
            )
            return False
        
        return True
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about loaded model.
        
        Returns:
            Dictionary with model metadata
        """
        metrics = self.trainer.training_metrics
        
        return {
            'model_type': metrics.model_type,
            'feature_count': metrics.feature_count,
            'training_samples': metrics.training_samples,
            'cv_score': f"{metrics.mean_cv_score:.3f} (+/- "
                       f"{metrics.std_cv_score:.3f})",
            'class_distribution': metrics.class_distribution,
            'feature_names': self.feature_names
        }
