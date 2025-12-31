"""
Model Training for Device Health Prediction

Apple principle: Use explainable models with clear uncertainty estimates.

Supports:
- Logistic Regression (most interpretable)
- Random Forest (good feature importance)
- Gradient Boosting (best performance)

All models include:
- Calibrated probabilities (Platt scaling / isotonic regression)
- Cross-validation for robustness
- Feature importance tracking

Author: Software Engineering Intern
Purpose: Train risk prediction models with defensive validation
"""

import logging
import json
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

import numpy as np
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import StandardScaler
import joblib

from .features import FeatureExtractor, FEATURE_NAMES
from .labels import RiskLabeler, DeviceRisk

logger = logging.getLogger(__name__)


class TrainingError(Exception):
    """Raised when training validation fails"""
    pass


@dataclass
class TrainingConfig:
    """Training configuration"""
    model_type: str  # 'logistic', 'random_forest', 'gradient_boosting'
    n_folds: int = 5
    calibration_method: str = 'sigmoid'  # 'sigmoid' or 'isotonic'
    random_state: int = 42
    
    # Model-specific hyperparameters
    logistic_c: float = 1.0
    rf_n_estimators: int = 100
    rf_max_depth: Optional[int] = 10
    gb_n_estimators: int = 100
    gb_learning_rate: float = 0.1
    gb_max_depth: int = 3


@dataclass
class TrainingMetrics:
    """Training validation metrics"""
    model_type: str
    cv_scores: List[float]
    mean_cv_score: float
    std_cv_score: float
    training_samples: int
    feature_count: int
    class_distribution: Dict[str, int]
    training_time_seconds: float


class ModelTrainer:
    """
    Train device health prediction models.
    
    Defensive principles:
    - Require minimum samples per class
    - Validate feature distributions
    - Always calibrate probabilities
    - Track training metrics
    """
    
    MIN_SAMPLES_PER_CLASS = 20
    MIN_TOTAL_SAMPLES = 100
    
    def __init__(self, config: TrainingConfig):
        self.config = config
        self.model = None
        self.scaler = None
        self.feature_names = FEATURE_NAMES.copy()
        self.training_metrics = None
    
    def _create_base_model(self):
        """Create base model based on config"""
        if self.config.model_type == 'logistic':
            return LogisticRegression(
                C=self.config.logistic_c,
                random_state=self.config.random_state,
                max_iter=1000,
                class_weight='balanced'
            )
        elif self.config.model_type == 'random_forest':
            return RandomForestClassifier(
                n_estimators=self.config.rf_n_estimators,
                max_depth=self.config.rf_max_depth,
                random_state=self.config.random_state,
                class_weight='balanced'
            )
        elif self.config.model_type == 'gradient_boosting':
            return GradientBoostingClassifier(
                n_estimators=self.config.gb_n_estimators,
                learning_rate=self.config.gb_learning_rate,
                max_depth=self.config.gb_max_depth,
                random_state=self.config.random_state
            )
        else:
            raise TrainingError(
                f"Unknown model type: {self.config.model_type}. "
                f"Must be 'logistic', 'random_forest', or 'gradient_boosting'"
            )
    
    def _validate_training_data(
        self,
        X: np.ndarray,
        y: np.ndarray
    ) -> None:
        """
        Validate training data before fitting.
        
        Defensive checks:
        - Sufficient total samples
        - Balanced class distribution
        - No missing values
        - Valid feature ranges
        """
        n_samples, n_features = X.shape
        
        # Check total samples
        if n_samples < self.MIN_TOTAL_SAMPLES:
            raise TrainingError(
                f"Insufficient training samples: {n_samples} < "
                f"{self.MIN_TOTAL_SAMPLES} required"
            )
        
        # Check feature count
        if n_features != len(self.feature_names):
            raise TrainingError(
                f"Feature mismatch: got {n_features}, "
                f"expected {len(self.feature_names)}"
            )
        
        # Check for missing values
        if np.any(np.isnan(X)):
            raise TrainingError("Training data contains NaN values")
        
        if np.any(np.isinf(X)):
            raise TrainingError("Training data contains infinite values")
        
        # Check class distribution
        unique, counts = np.unique(y, return_counts=True)
        class_dist = dict(zip(unique, counts))
        
        for class_label, count in class_dist.items():
            if count < self.MIN_SAMPLES_PER_CLASS:
                raise TrainingError(
                    f"Insufficient samples for class {class_label}: "
                    f"{count} < {self.MIN_SAMPLES_PER_CLASS} required"
                )
        
        logger.info(f"Training data validation passed: "
                   f"{n_samples} samples, {n_features} features")
        logger.info(f"Class distribution: {class_dist}")
    
    def train(
        self,
        features_list: List[Dict[str, Any]],
        labels_list: List[Dict[str, Any]]
    ) -> TrainingMetrics:
        """
        Train model from features and labels.
        
        Args:
            features_list: List of feature dictionaries
            labels_list: List of label dictionaries
            
        Returns:
            TrainingMetrics with cross-validation scores
        """
        start_time = datetime.now()
        
        # Prepare training data
        X, y, class_dist = self._prepare_training_data(
            features_list,
            labels_list
        )
        
        # Validate
        self._validate_training_data(X, y)
        
        # Scale features
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        # Cross-validation before final training
        base_model = self._create_base_model()
        cv = StratifiedKFold(
            n_splits=self.config.n_folds,
            shuffle=True,
            random_state=self.config.random_state
        )
        
        cv_scores = cross_val_score(
            base_model,
            X_scaled,
            y,
            cv=cv,
            scoring='f1_weighted'
        )
        
        logger.info(f"Cross-validation scores: {cv_scores}")
        logger.info(f"Mean CV score: {cv_scores.mean():.3f} "
                   f"(+/- {cv_scores.std():.3f})")
        
        # Train final model with calibration
        base_model = self._create_base_model()
        self.model = CalibratedClassifierCV(
            base_model,
            method=self.config.calibration_method,
            cv=self.config.n_folds
        )
        
        self.model.fit(X_scaled, y)
        
        # Calculate metrics
        training_time = (datetime.now() - start_time).total_seconds()
        
        self.training_metrics = TrainingMetrics(
            model_type=self.config.model_type,
            cv_scores=cv_scores.tolist(),
            mean_cv_score=float(cv_scores.mean()),
            std_cv_score=float(cv_scores.std()),
            training_samples=len(X),
            feature_count=len(self.feature_names),
            class_distribution=class_dist,
            training_time_seconds=training_time
        )
        
        logger.info(f"Training completed in {training_time:.2f}s")
        
        return self.training_metrics
    
    def _prepare_training_data(
        self,
        features_list: List[Dict[str, Any]],
        labels_list: List[Dict[str, Any]]
    ) -> Tuple[np.ndarray, np.ndarray, Dict[str, int]]:
        """
        Convert features and labels to numpy arrays.
        
        Returns:
            (X, y, class_distribution)
        """
        if len(features_list) != len(labels_list):
            raise TrainingError(
                f"Feature/label mismatch: {len(features_list)} features, "
                f"{len(labels_list)} labels"
            )
        
        X_list = []
        y_list = []
        
        for feat_dict, label_dict in zip(features_list, labels_list):
            # Extract feature vector in correct order
            features = feat_dict.get('features', feat_dict)
            feature_vector = [
                features.get(name, 0.0) for name in self.feature_names
            ]
            X_list.append(feature_vector)
            
            # Extract label
            risk_level = label_dict.get('risk_level', label_dict.get('risk'))
            y_list.append(int(risk_level))
        
        X = np.array(X_list, dtype=np.float64)
        y = np.array(y_list, dtype=np.int32)
        
        # Get class distribution
        unique, counts = np.unique(y, return_counts=True)
        class_dist = {
            DeviceRisk(int(cls)).name: int(count)
            for cls, count in zip(unique, counts)
        }
        
        return X, y, class_dist
    
    def save(self, output_dir: Path) -> Path:
        """
        Save trained model and metadata.
        
        Args:
            output_dir: Directory to save model
            
        Returns:
            Path to saved model file
        """
        if self.model is None:
            raise TrainingError("No trained model to save")
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_name = f"{self.config.model_type}_{timestamp}"
        
        # Save model + scaler
        model_path = output_dir / f"{model_name}.pkl"
        joblib.dump({
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'config': self.config,
            'metrics': self.training_metrics
        }, model_path)
        
        # Save metadata
        metadata_path = output_dir / f"{model_name}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump({
                'model_type': self.config.model_type,
                'training_date': timestamp,
                'feature_names': self.feature_names,
                'metrics': {
                    'mean_cv_score': self.training_metrics.mean_cv_score,
                    'std_cv_score': self.training_metrics.std_cv_score,
                    'training_samples': self.training_metrics.training_samples,
                    'class_distribution': (
                        self.training_metrics.class_distribution
                    )
                }
            }, f, indent=2)
        
        logger.info(f"Model saved to {model_path}")
        return model_path
    
    @staticmethod
    def load(model_path: Path) -> 'ModelTrainer':
        """
        Load trained model.
        
        Args:
            model_path: Path to saved model file
            
        Returns:
            ModelTrainer with loaded model
        """
        model_data = joblib.load(model_path)
        
        trainer = ModelTrainer(model_data['config'])
        trainer.model = model_data['model']
        trainer.scaler = model_data['scaler']
        trainer.feature_names = model_data['feature_names']
        trainer.training_metrics = model_data['metrics']
        
        logger.info(f"Model loaded from {model_path}")
        return trainer
    
    def get_feature_importance(self) -> Optional[Dict[str, float]]:
        """
        Get feature importance scores.
        
        Only available for tree-based models.
        
        Returns:
            Dictionary mapping feature names to importance scores
        """
        if self.model is None:
            return None
        
        # Get base estimator from calibrated classifier
        base_estimator = self.model.calibrated_classifiers_[0].estimator
        
        if hasattr(base_estimator, 'feature_importances_'):
            importances = base_estimator.feature_importances_
            return {
                name: float(imp)
                for name, imp in zip(self.feature_names, importances)
            }
        elif hasattr(base_estimator, 'coef_'):
            # For logistic regression, use absolute coefficients
            coefs = np.abs(base_estimator.coef_[0])
            return {
                name: float(coef)
                for name, coef in zip(self.feature_names, coefs)
            }
        
        return None
