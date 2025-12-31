#!/usr/bin/env python3
"""
Transfer Learning & Model Checkpoint Manager

This module provides comprehensive save/load functionality for transfer learning.
Enables model checkpointing, versioning, and easy model reuse.

Author: Software Engineering Intern
Purpose: Enable transfer learning and model versioning for device health analytics
"""

import joblib
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import shutil

logger = logging.getLogger(__name__)


class ModelCheckpoint:
    """
    Represents a saved model checkpoint with metadata.
    
    Attributes:
        checkpoint_id: Unique identifier for this checkpoint
        model_path: Path to the saved model file
        metadata: Dictionary containing model metadata
        created_at: Timestamp when checkpoint was created
    """
    
    def __init__(
        self,
        checkpoint_id: str,
        model_path: Path,
        metadata: Dict[str, Any],
        created_at: str
    ):
        self.checkpoint_id = checkpoint_id
        self.model_path = model_path
        self.metadata = metadata
        self.created_at = created_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert checkpoint to dictionary for JSON serialization"""
        return {
            'checkpoint_id': self.checkpoint_id,
            'model_path': str(self.model_path),
            'metadata': self.metadata,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelCheckpoint':
        """Create ModelCheckpoint from dictionary"""
        return cls(
            checkpoint_id=data['checkpoint_id'],
            model_path=Path(data['model_path']),
            metadata=data['metadata'],
            created_at=data['created_at']
        )


class TransferLearningManager:
    """
    Manages model checkpoints for transfer learning.
    
    Features:
    - Save model checkpoints with versioning
    - Load checkpoints for fine-tuning or inference
    - List all available checkpoints
    - Export/import checkpoints for sharing
    - Automatic metadata tracking (accuracy, features, hyperparameters)
    
    Usage:
        manager = TransferLearningManager(checkpoint_dir='models/checkpoints')
        
        # Save a checkpoint
        checkpoint_id = manager.save_checkpoint(
            model=trained_model,
            model_name='xgboost_v1',
            metadata={'accuracy': 0.92, 'features': feature_list}
        )
        
        # Load a checkpoint
        model = manager.load_checkpoint(checkpoint_id)
        
        # List all checkpoints
        checkpoints = manager.list_checkpoints()
    """
    
    def __init__(self, checkpoint_dir: str | Path = 'models/checkpoints'):
        """
        Initialize transfer learning manager.
        
        Args:
            checkpoint_dir: Directory to store model checkpoints
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # Metadata file tracks all checkpoints
        self.metadata_file = self.checkpoint_dir / 'checkpoints_metadata.json'
        self._load_or_create_metadata()
    
    def _load_or_create_metadata(self):
        """Load existing metadata or create new metadata file"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                data = json.load(f)
                self.checkpoints = {
                    k: ModelCheckpoint.from_dict(v) 
                    for k, v in data.items()
                }
        else:
            self.checkpoints = {}
            self._save_metadata()
    
    def _save_metadata(self):
        """Save checkpoint metadata to disk"""
        data = {
            k: v.to_dict() 
            for k, v in self.checkpoints.items()
        }
        with open(self.metadata_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def save_checkpoint(
        self,
        model: Any,
        model_name: str,
        metadata: Optional[Dict[str, Any]] = None,
        checkpoint_id: Optional[str] = None
    ) -> str:
        """
        Save a model checkpoint with metadata.
        
        Args:
            model: The trained model object (sklearn, xgboost, etc.)
            model_name: Human-readable name for the model
            metadata: Optional dictionary with model metadata
                     (accuracy, hyperparameters, features, etc.)
            checkpoint_id: Optional custom checkpoint ID
                          (auto-generated if not provided)
        
        Returns:
            checkpoint_id: Unique identifier for this checkpoint
        
        Example:
            checkpoint_id = manager.save_checkpoint(
                model=xgb_model,
                model_name='xgboost_device_health',
                metadata={
                    'accuracy': 0.92,
                    'precision': 0.89,
                    'recall': 0.91,
                    'feature_count': 22,
                    'training_samples': 10000,
                    'hyperparameters': {
                        'max_depth': 6,
                        'learning_rate': 0.1
                    }
                }
            )
        """
        # Generate checkpoint ID if not provided
        if checkpoint_id is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            checkpoint_id = f"{model_name}_{timestamp}"
        
        # Create checkpoint directory
        checkpoint_path = self.checkpoint_dir / checkpoint_id
        checkpoint_path.mkdir(parents=True, exist_ok=True)
        
        # Save model file
        model_file = checkpoint_path / 'model.joblib'
        joblib.dump(model, model_file)
        
        # Prepare metadata
        if metadata is None:
            metadata = {}
        
        metadata['model_name'] = model_name
        metadata['saved_at'] = datetime.now().isoformat()
        metadata['model_type'] = type(model).__name__
        
        # Save metadata JSON
        metadata_file = checkpoint_path / 'metadata.json'
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Create checkpoint object
        checkpoint = ModelCheckpoint(
            checkpoint_id=checkpoint_id,
            model_path=model_file,
            metadata=metadata,
            created_at=metadata['saved_at']
        )
        
        # Register checkpoint
        self.checkpoints[checkpoint_id] = checkpoint
        self._save_metadata()
        
        logger.info(f"Saved checkpoint: {checkpoint_id}")
        logger.info(f"  Model: {model_name}")
        logger.info(f"  Path: {model_file}")
        
        return checkpoint_id
    
    def load_checkpoint(self, checkpoint_id: str) -> Any:
        """
        Load a model from a checkpoint.
        
        Args:
            checkpoint_id: Unique identifier of the checkpoint
        
        Returns:
            model: The loaded model object
        
        Raises:
            ValueError: If checkpoint_id not found
            
        Example:
            model = manager.load_checkpoint('xgboost_device_health_20250101_120000')
            
            # Use for inference
            predictions = model.predict(X_test)
            
            # Or fine-tune with new data
            model.fit(X_new, y_new)
        """
        if checkpoint_id not in self.checkpoints:
            raise ValueError(
                f"Checkpoint '{checkpoint_id}' not found. "
                f"Available: {list(self.checkpoints.keys())}"
            )
        
        checkpoint = self.checkpoints[checkpoint_id]
        
        if not checkpoint.model_path.exists():
            raise FileNotFoundError(
                f"Model file not found: {checkpoint.model_path}"
            )
        
        logger.info(f"Loading checkpoint: {checkpoint_id}")
        model = joblib.load(checkpoint.model_path)
        
        return model
    
    def get_checkpoint_metadata(self, checkpoint_id: str) -> Dict[str, Any]:
        """
        Get metadata for a specific checkpoint.
        
        Args:
            checkpoint_id: Unique identifier of the checkpoint
        
        Returns:
            metadata: Dictionary containing checkpoint metadata
        """
        if checkpoint_id not in self.checkpoints:
            raise ValueError(f"Checkpoint '{checkpoint_id}' not found")
        
        return self.checkpoints[checkpoint_id].metadata
    
    def list_checkpoints(
        self,
        model_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all available checkpoints.
        
        Args:
            model_name: Optional filter by model name
        
        Returns:
            checkpoints: List of checkpoint dictionaries
        
        Example:
            # List all checkpoints
            all_checkpoints = manager.list_checkpoints()
            
            # List only XGBoost checkpoints
            xgb_checkpoints = manager.list_checkpoints(model_name='xgboost')
        """
        result = []
        
        for checkpoint_id, checkpoint in self.checkpoints.items():
            # Filter by model name if specified
            if model_name is not None:
                if checkpoint.metadata.get('model_name') != model_name:
                    continue
            
            result.append({
                'checkpoint_id': checkpoint_id,
                'model_name': checkpoint.metadata.get('model_name', 'unknown'),
                'created_at': checkpoint.created_at,
                'model_type': checkpoint.metadata.get('model_type', 'unknown'),
                'accuracy': checkpoint.metadata.get('accuracy'),
                'feature_count': checkpoint.metadata.get('feature_count'),
                'training_samples': checkpoint.metadata.get('training_samples')
            })
        
        return result
    
    def delete_checkpoint(self, checkpoint_id: str):
        """
        Delete a checkpoint and its files.
        
        Args:
            checkpoint_id: Unique identifier of the checkpoint
        """
        if checkpoint_id not in self.checkpoints:
            raise ValueError(f"Checkpoint '{checkpoint_id}' not found")
        
        checkpoint = self.checkpoints[checkpoint_id]
        
        # Delete checkpoint directory
        checkpoint_dir = checkpoint.model_path.parent
        if checkpoint_dir.exists():
            shutil.rmtree(checkpoint_dir)
        
        # Remove from registry
        del self.checkpoints[checkpoint_id]
        self._save_metadata()
        
        logger.info(f"Deleted checkpoint: {checkpoint_id}")
    
    def export_checkpoint(
        self,
        checkpoint_id: str,
        export_path: str | Path
    ):
        """
        Export a checkpoint to a portable archive.
        
        Args:
            checkpoint_id: Unique identifier of the checkpoint
            export_path: Path where to save the exported archive (.tar.gz)
        
        Example:
            manager.export_checkpoint(
                'xgboost_device_health_20250101_120000',
                'exports/my_model.tar.gz'
            )
        """
        if checkpoint_id not in self.checkpoints:
            raise ValueError(f"Checkpoint '{checkpoint_id}' not found")
        
        checkpoint = self.checkpoints[checkpoint_id]
        checkpoint_dir = checkpoint.model_path.parent
        
        export_path = Path(export_path)
        export_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create tar.gz archive
        shutil.make_archive(
            str(export_path.with_suffix('')),
            'gztar',
            checkpoint_dir
        )
        
        logger.info(f"Exported checkpoint to: {export_path}.tar.gz")
    
    def import_checkpoint(
        self,
        import_path: str | Path,
        checkpoint_id: Optional[str] = None
    ) -> str:
        """
        Import a checkpoint from an archive.
        
        Args:
            import_path: Path to the exported archive (.tar.gz)
            checkpoint_id: Optional custom checkpoint ID
        
        Returns:
            checkpoint_id: ID of the imported checkpoint
        
        Example:
            checkpoint_id = manager.import_checkpoint(
                'exports/my_model.tar.gz'
            )
        """
        import_path = Path(import_path)
        
        if not import_path.exists():
            raise FileNotFoundError(f"Import file not found: {import_path}")
        
        # Generate checkpoint ID if not provided
        if checkpoint_id is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            checkpoint_id = f"imported_{timestamp}"
        
        # Extract archive
        checkpoint_path = self.checkpoint_dir / checkpoint_id
        shutil.unpack_archive(import_path, checkpoint_path)
        
        # Load metadata
        metadata_file = checkpoint_path / 'metadata.json'
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        # Create checkpoint object
        model_file = checkpoint_path / 'model.joblib'
        checkpoint = ModelCheckpoint(
            checkpoint_id=checkpoint_id,
            model_path=model_file,
            metadata=metadata,
            created_at=metadata.get('saved_at', datetime.now().isoformat())
        )
        
        # Register checkpoint
        self.checkpoints[checkpoint_id] = checkpoint
        self._save_metadata()
        
        logger.info(f"Imported checkpoint: {checkpoint_id}")
        
        return checkpoint_id
    
    def get_latest_checkpoint(
        self,
        model_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Get the most recent checkpoint ID.
        
        Args:
            model_name: Optional filter by model name
        
        Returns:
            checkpoint_id: ID of the latest checkpoint, or None if no checkpoints
        
        Example:
            latest_id = manager.get_latest_checkpoint(model_name='xgboost')
            model = manager.load_checkpoint(latest_id)
        """
        checkpoints = self.list_checkpoints(model_name=model_name)
        
        if not checkpoints:
            return None
        
        # Sort by created_at timestamp
        checkpoints.sort(key=lambda x: x['created_at'], reverse=True)
        
        return checkpoints[0]['checkpoint_id']
