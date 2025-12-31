#!/usr/bin/env python3
"""
Phase 3 Demo: Predictive Device Health Analytics

Demonstrates end-to-end ML pipeline:
1. Generate synthetic telemetry data
2. Extract features
3. Generate risk labels
4. Train predictive model
5. Make predictions with explanations
6. Evaluate model performance

This showcases Apple-style explainable ML for device health.

Author: Software Engineering Intern
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from python.ingestion.generator import TelemetryGenerator
from python.analytics.features import FeatureExtractor
from python.analytics.labels import RiskLabeler
from python.analytics.train import ModelTrainer, TrainingConfig
from python.analytics.predict import RiskPredictor
from python.analytics.explain import ModelExplainer
from python.analytics.evaluate import ModelEvaluator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_section(title: str):
    """Print section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def main():
    """Run Phase 3 demonstration"""
    
    print_section("Phase 3: Predictive Device Health Analytics")
    print("This demo shows explainable ML for device health prediction.")
    print("Apple principle: Every prediction must be interpretable.\n")
    
    # === STEP 1: Generate Training Data ===
    print_section("Step 1: Generate Synthetic Telemetry")
    
    generator = TelemetryGenerator(seed=42)
    
    # Generate diverse dataset
    print("Generating devices with different health profiles...")
    all_records = []
    device_configs = [
        # Healthy devices
        ("HEALTHY_001", "clean", 100),
        ("HEALTHY_002", "clean", 100),
        ("HEALTHY_003", "clean", 100),
        # Degraded devices (battery issues)
        ("DEGRADED_001", "battery_degraded", 100),
        ("DEGRADED_002", "battery_degraded", 100),
        # At-risk devices (thermal + CPU issues)
        ("ATRISK_001", "thermal_stressed", 100),
        ("ATRISK_002", "cpu_stressed", 100),
        ("ATRISK_003", "mixed_issues", 100),
    ]
    
    for device_id, profile, count in device_configs:
        records = generator.generate_time_series(
            device_id=device_id,
            duration_days=7,
            samples_per_day=count // 7,
            quality=profile
        )
        all_records.extend(records)
        print(f"  Generated {len(records)} samples for {device_id} ({profile})")
    
    print(f"\nTotal samples: {len(all_records)}")
    
    # === STEP 2: Extract Features ===
    print_section("Step 2: Extract Features from Telemetry")
    
    extractor = FeatureExtractor()
    
    # Group by device
    device_records = {}
    for record in all_records:
        device_id = record['device_id']
        if device_id not in device_records:
            device_records[device_id] = []
        device_records[device_id].append(record)
    
    features_list = []
    for device_id, records in device_records.items():
        try:
            device_features = extractor.extract_features(records)
            features_list.append({
                'device_id': device_id,
                'features': device_features.features
            })
            print(f"  Extracted {len(device_features.features)} features "
                  f"from {device_id}")
        except Exception as e:
            logger.error(f"Feature extraction failed for {device_id}: {e}")
    
    print(f"\nExtracted features for {len(features_list)} devices")
    
    # === STEP 3: Generate Risk Labels ===
    print_section("Step 3: Generate Risk Labels")
    
    labels_list = RiskLabeler.create_training_labels(features_list)
    
    print("Risk distribution:")
    label_dist = RiskLabeler.get_label_distribution(labels_list)
    for risk_name, count in label_dist['counts'].items():
        pct = label_dist['percentages'][risk_name]
        print(f"  {risk_name}: {count} ({pct:.1f}%)")
    
    print(f"\nIs balanced: {label_dist['is_balanced']}")
    
    # Show some label justifications
    print("\nSample label justifications:")
    for i, label in enumerate(labels_list[:3]):
        print(f"\n  Device {label.device_id}:")
        print(f"    Risk: {label.risk_level.name} "
              f"(confidence: {label.confidence:.2f})")
        print(f"    Reasons:")
        for reason in label.reasons[:3]:  # Show top 3 reasons
            print(f"      - {reason}")
    
    # === STEP 4: Train Predictive Models ===
    print_section("Step 4: Train Predictive Models")
    
    # Convert labels to dict format
    labels_dict = [label.to_dict() for label in labels_list]
    
    # Train multiple models for comparison
    model_configs = [
        ('logistic', "Logistic Regression (most interpretable)"),
        ('random_forest', "Random Forest (good importance)"),
        ('gradient_boosting', "Gradient Boosting (best performance)")
    ]
    
    trained_models = {}
    
    for model_type, description in model_configs:
        print(f"\nTraining {description}...")
        
        config = TrainingConfig(
            model_type=model_type,
            n_folds=3,  # Use 3 folds for small dataset
            random_state=42
        )
        
        trainer = ModelTrainer(config)
        
        try:
            metrics = trainer.train(features_list, labels_dict)
            
            print(f"  Cross-validation score: "
                  f"{metrics.mean_cv_score:.3f} "
                  f"(+/- {metrics.std_cv_score:.3f})")
            print(f"  Training time: {metrics.training_time_seconds:.2f}s")
            
            # Save model
            models_dir = project_root / 'models'
            model_path = trainer.save(models_dir)
            trained_models[model_type] = model_path
            
            print(f"  Model saved to {model_path.name}")
            
        except Exception as e:
            logger.error(f"Training failed for {model_type}: {e}")
            continue
    
    # Use best model for demonstration (gradient boosting)
    best_model_type = 'gradient_boosting'
    if best_model_type not in trained_models:
        best_model_type = list(trained_models.keys())[0]
    
    best_model_path = trained_models[best_model_type]
    
    print(f"\nUsing {best_model_type} for predictions")
    
    # === STEP 5: Make Predictions with Explanations ===
    print_section("Step 5: Make Predictions with Explanations")
    
    predictor = RiskPredictor(best_model_path)
    explainer = ModelExplainer(predictor, use_shap=False)  # Fallback mode
    
    print("Model information:")
    model_info = predictor.get_model_info()
    print(f"  Type: {model_info['model_type']}")
    print(f"  Training samples: {model_info['training_samples']}")
    print(f"  CV score: {model_info['cv_score']}")
    
    # Make predictions on all devices
    print("\nMaking predictions...")
    predictions = predictor.predict_batch(features_list)
    
    print(f"Generated {len(predictions)} predictions")
    
    # Show detailed predictions with explanations
    print("\nSample predictions with explanations:")
    for i in range(min(3, len(predictions))):
        pred = predictions[i]
        features = features_list[i]['features']
        
        print(f"\n  Device {pred.device_id}:")
        print(f"    Predicted Risk: {pred.predicted_risk.name}")
        print(f"    Confidence: {pred.confidence:.2f}")
        print(f"    Is confident: {pred.is_confident}")
        print(f"    Is in distribution: {pred.is_in_distribution}")
        
        if pred.warnings:
            print(f"    Warnings: {pred.warnings}")
        
        # Get explanation
        explanation = explainer.explain_prediction(
            pred.device_id,
            features,
            pred,
            top_n=3
        )
        
        print(f"\n    Top contributing features:")
        for feat in explanation.top_contributing_features:
            print(f"      - {feat['feature']}: {feat['value']:.3f} "
                  f"({feat['direction']} risk)")
    
    # === STEP 6: Evaluate Model Performance ===
    print_section("Step 6: Evaluate Model Performance")
    
    # Convert predictions and labels to evaluation format
    pred_dict = [p.to_dict() for p in predictions]
    
    try:
        eval_metrics = ModelEvaluator.evaluate_predictions(
            pred_dict,
            labels_dict
        )
        
        print(eval_metrics.summary())
        
        # Analyze confidence calibration
        print("\n\nConfidence Calibration:")
        calib = ModelEvaluator.analyze_confidence_calibration(pred_dict)
        print(f"  Mean confidence: {calib['mean_confidence']:.3f}")
        print(f"  Confident predictions: "
              f"{calib['confident_predictions_pct']:.1f}%")
        print(f"\n  Confidence distribution:")
        for range_name, count in calib['confidence_distribution'].items():
            print(f"    {range_name}: {count}")
        
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
    
    # === STEP 7: Feature Importance ===
    print_section("Step 7: Global Feature Importance")
    
    importance = explainer.get_global_importance(top_n=10)
    
    print("Top 10 most important features:")
    for i, feat_info in enumerate(importance, 1):
        print(f"  {i}. {feat_info['readable_name']}: "
              f"{feat_info['importance']:.4f}")
    
    # === Summary ===
    print_section("Demo Complete!")
    
    print("Key Takeaways:")
    print("  ✓ Explainable ML models (no black boxes)")
    print("  ✓ Calibrated confidence scores")
    print("  ✓ Feature importance and explanations")
    print("  ✓ Out-of-distribution detection")
    print("  ✓ Comprehensive evaluation metrics")
    print("\nThis demonstrates production-ready ML for Apple-style analytics.")
    print(f"\nModels saved in: {models_dir}")


if __name__ == '__main__':
    main()
