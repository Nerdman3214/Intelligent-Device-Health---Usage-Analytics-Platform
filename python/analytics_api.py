#!/usr/bin/env python3
"""
Python Analytics Bridge for Java API

This script is invoked by the Java Spring Boot API as a subprocess.
It receives device telemetry as JSON, runs analytics, and returns predictions.

Apple principle: Clear contract (JSON in/out), process isolation.

Usage:
    python analytics_api.py <request_file.json>

Input JSON (from Java):
    {
      "device_id": "ABC123",
      "telemetry": [...]
    }

Output JSON (to Java):
    {
      "device_id": "ABC123",
      "predicted_risk": "HEALTHY",
      "confidence": 0.89,
      ...
    }
"""

import sys
import json
import logging
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from python.analytics.features import FeatureExtractor
from python.analytics.predict import RiskPredictor
from python.analytics.explain import ModelExplainer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_request(request_file: Path) -> dict:
    """Load and validate request JSON"""
    with open(request_file, 'r') as f:
        return json.load(f)


def analyze_device_health(request: dict) -> dict:
    """
    Analyze device health from telemetry.
    
    Returns prediction with explanation.
    """
    device_id = request['device_id']
    telemetry = request['telemetry']
    
    logger.info(f"Analyzing device {device_id} ({len(telemetry)} samples)")
    
    # Extract features
    extractor = FeatureExtractor()
    device_features = extractor.extract_features(telemetry)
    
    # Load model (use latest gradient boosting model)
    models_dir = project_root / 'models'
    model_files = list(models_dir.glob('gradient_boosting_*.pkl'))
    
    if not model_files:
        raise FileNotFoundError("No trained models found. Run demo_phase3.py first.")
    
    # Use most recent model
    latest_model = sorted(model_files)[-1]
    logger.info(f"Using model: {latest_model.name}")
    
    # Predict
    predictor = RiskPredictor(latest_model)
    prediction = predictor.predict(device_id, device_features.features)
    
    # Explain
    explainer = ModelExplainer(predictor, use_shap=False)
    explanation = explainer.explain_prediction(
        device_id,
        device_features.features,
        prediction,
        top_n=5
    )
    
    # Build response
    response = {
        'device_id': prediction.device_id,
        'predicted_risk': prediction.predicted_risk.name,
        'confidence': prediction.confidence,
        'probabilities': prediction.probabilities,
        'is_confident': prediction.is_confident,
        'is_in_distribution': prediction.is_in_distribution,
        'top_contributing_features': explanation.top_contributing_features,
        'warnings': prediction.warnings,
        'explanation_text': explanation.explanation_text,
        'model_version': latest_model.name
    }
    
    logger.info(
        f"Prediction: {response['predicted_risk']} "
        f"(confidence: {response['confidence']:.2f})"
    )
    
    return response


def main():
    """Main entry point for Java subprocess invocation"""
    if len(sys.argv) != 2:
        print("Usage: python analytics_api.py <request_file.json>", file=sys.stderr)
        sys.exit(1)
    
    request_file = Path(sys.argv[1])
    
    if not request_file.exists():
        print(f"Request file not found: {request_file}", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Load request
        request = load_request(request_file)
        
        # Analyze
        response = analyze_device_health(request)
        
        # Output JSON to stdout (Java reads this)
        print(json.dumps(response, indent=2))
        
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Analytics failed: {e}", exc_info=True)
        
        # Return error as JSON
        error_response = {
            'error': str(e),
            'error_type': type(e).__name__
        }
        print(json.dumps(error_response), file=sys.stderr)
        
        sys.exit(1)


if __name__ == '__main__':
    main()
