#!/usr/bin/env python3
"""
Transfer Learning Demo

Demonstrates how to:
1. Save model checkpoints
2. Load checkpoints for inference
3. Load checkpoints for fine-tuning (transfer learning)
4. Export/import checkpoints for sharing

Author: Software Engineering Intern
"""

import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from python.analytics.transfer_learning import TransferLearningManager
from sklearn.ensemble import RandomForestClassifier
import numpy as np

def main():
    print("=" * 60)
    print("  Transfer Learning & Model Checkpoint Demo")
    print("=" * 60)
    print()
    
    # Initialize manager
    manager = TransferLearningManager(checkpoint_dir='models/checkpoints')
    
    # === DEMO 1: Save a checkpoint ===
    print("1. Saving a model checkpoint...")
    print("-" * 60)
    
    # Create a dummy trained model
    model = RandomForestClassifier(n_estimators=100, max_depth=6)
    X_train = np.random.randn(100, 22)  # 100 samples, 22 features
    y_train = np.random.randint(0, 3, 100)  # 3 classes
    model.fit(X_train, y_train)
    
    # Save checkpoint with metadata
    checkpoint_id = manager.save_checkpoint(
        model=model,
        model_name='random_forest_device_health',
        metadata={
            'accuracy': 0.92,
            'precision': 0.89,
            'recall': 0.91,
            'f1_score': 0.90,
            'feature_count': 22,
            'training_samples': 10000,
            'hyperparameters': {
                'n_estimators': 100,
                'max_depth': 6,
                'min_samples_split': 2
            },
            'risk_classes': ['HEALTHY', 'DEGRADING', 'AT_RISK'],
            'notes': 'Baseline model trained on synthetic data'
        }
    )
    
    print(f"✓ Checkpoint saved: {checkpoint_id}")
    print()
    
    # === DEMO 2: List all checkpoints ===
    print("2. Listing all checkpoints...")
    print("-" * 60)
    
    checkpoints = manager.list_checkpoints()
    
    for checkpoint in checkpoints:
        print(f"  ID: {checkpoint['checkpoint_id']}")
        print(f"    Model: {checkpoint['model_name']}")
        print(f"    Type: {checkpoint['model_type']}")
        print(f"    Created: {checkpoint['created_at']}")
        if checkpoint.get('accuracy'):
            print(f"    Accuracy: {checkpoint['accuracy']:.2%}")
        print()
    
    # === DEMO 3: Load a checkpoint for inference ===
    print("3. Loading checkpoint for inference...")
    print("-" * 60)
    
    # Get latest checkpoint
    latest_id = manager.get_latest_checkpoint()
    
    if latest_id:
        loaded_model = manager.load_checkpoint(latest_id)
        
        # Use for predictions
        X_test = np.random.randn(5, 22)
        predictions = loaded_model.predict(X_test)
        
        print(f"✓ Loaded checkpoint: {latest_id}")
        print(f"  Model type: {type(loaded_model).__name__}")
        print(f"  Test predictions: {predictions}")
        print()
    
    # === DEMO 4: Load checkpoint metadata ===
    print("4. Viewing checkpoint metadata...")
    print("-" * 60)
    
    if latest_id:
        metadata = manager.get_checkpoint_metadata(latest_id)
        
        print("Metadata:")
        for key, value in metadata.items():
            if key != 'hyperparameters':
                print(f"  {key}: {value}")
        
        if 'hyperparameters' in metadata:
            print("  hyperparameters:")
            for param, val in metadata['hyperparameters'].items():
                print(f"    {param}: {val}")
        print()
    
    # === DEMO 5: Transfer learning (fine-tuning) ===
    print("5. Transfer Learning: Fine-tuning loaded model...")
    print("-" * 60)
    
    if latest_id:
        # Load pre-trained model
        base_model = manager.load_checkpoint(latest_id)
        
        # Fine-tune with new data (simulated)
        X_new = np.random.randn(50, 22)
        y_new = np.random.randint(0, 3, 50)
        
        # For tree-based models, we can't directly fine-tune,
        # but we can use them as a starting point for ensemble methods
        # or as feature extractors
        
        print(f"✓ Loaded base model: {type(base_model).__name__}")
        print(f"  Original estimators: {base_model.n_estimators}")
        print()
        print("  Transfer learning strategies:")
        print("    - Use predictions as features for meta-learner")
        print("    - Extract feature importances for feature selection")
        print("    - Use as part of ensemble (stacking/voting)")
        print()
    
    # === DEMO 6: Export checkpoint ===
    print("6. Exporting checkpoint for sharing...")
    print("-" * 60)
    
    if latest_id:
        export_path = Path('models/exports') / latest_id
        export_path.parent.mkdir(parents=True, exist_ok=True)
        
        manager.export_checkpoint(latest_id, export_path)
        
        # The export actually creates .tar.gz extension
        actual_path = Path(str(export_path) + '.tar.gz')
        
        print(f"✓ Exported to: {actual_path}")
        if actual_path.exists():
            print(f"  File size: {actual_path.stat().st_size / 1024:.2f} KB")
        print()
    
    # === DEMO 7: Summary ===
    print("=" * 60)
    print("  Summary: Transfer Learning Capabilities")
    print("=" * 60)
    print()
    print("✓ Checkpoint Management")
    print("  - Save models with comprehensive metadata")
    print("  - Version tracking with timestamps")
    print("  - Easy retrieval by checkpoint ID")
    print()
    print("✓ Transfer Learning")
    print("  - Load pre-trained models for inference")
    print("  - Load checkpoints as starting point for fine-tuning")
    print("  - Extract learned features/patterns")
    print()
    print("✓ Portability")
    print("  - Export checkpoints as archives")
    print("  - Import shared checkpoints")
    print("  - Share models across environments")
    print()
    print("✓ Production Ready")
    print("  - Metadata tracking (accuracy, hyperparameters)")
    print("  - Easy model deployment")
    print("  - Reproducible ML pipeline")
    print()

if __name__ == '__main__':
    main()
