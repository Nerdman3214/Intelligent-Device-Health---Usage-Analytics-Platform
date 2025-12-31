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
        # Convert checkpoint directory path to Path object for cross-platform compatibility
        self.checkpoint_dir = Path(checkpoint_dir)
        
        # Create checkpoint directory if it doesn't exist
        # parents=True: create parent directories if needed
        # exist_ok=True: don't raise error if directory already exists
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # Metadata file tracks all checkpoints in a centralized JSON file
        # This allows quick lookup of all available checkpoints without scanning directories
        self.metadata_file = self.checkpoint_dir / 'checkpoints_metadata.json'
        
        # Load existing checkpoint registry or create new one if first time
        self._load_or_create_metadata()
    
    def _load_or_create_metadata(self):
        """Load existing metadata or create new metadata file"""
        # Check if metadata file already exists from previous sessions
        if self.metadata_file.exists():
            # Open and read the JSON file containing all checkpoint metadata
            with open(self.metadata_file, 'r') as f:
                # Parse JSON into Python dictionary
                data = json.load(f)
                
                # Convert each dictionary entry back into ModelCheckpoint object
                # k = checkpoint_id (string), v = checkpoint data (dict)
                self.checkpoints = {
                    k: ModelCheckpoint.from_dict(v) 
                    for k, v in data.items()
                }
        else:
            # First time initialization - create empty checkpoint registry
            self.checkpoints = {}
            
            # Save the empty metadata file to disk
            self._save_metadata()
    
    def _save_metadata(self):
        """Save checkpoint metadata to disk"""
        # Convert all ModelCheckpoint objects to dictionaries for JSON serialization
        # k = checkpoint_id, v = ModelCheckpoint object
        data = {
            k: v.to_dict() 
            for k, v in self.checkpoints.items()
        }
        
        # Write to metadata file with indentation for human readability
        with open(self.metadata_file, 'w') as f:
            # indent=2: pretty-print with 2-space indentation
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
        # Step 1: Generate unique checkpoint ID if not provided by user
        if checkpoint_id is None:
            # Create timestamp string: YYYYMMDD_HHMMSS (e.g., "20251231_143022")
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            # Combine model name with timestamp for unique ID
            # Example: "xgboost_device_health_20251231_143022"
            checkpoint_id = f"{model_name}_{timestamp}"
        
        # Step 2: Create directory for this specific checkpoint
        checkpoint_path = self.checkpoint_dir / checkpoint_id
        # Create directory and any missing parent directories
        checkpoint_path.mkdir(parents=True, exist_ok=True)
        
        # Step 3: Save the actual model using joblib serialization
        model_file = checkpoint_path / 'model.joblib'
        # joblib.dump: Efficiently serialize sklearn/xgboost models
        # Handles numpy arrays better than pickle
        joblib.dump(model, model_file)
        
        # Step 4: Prepare and enhance metadata
        if metadata is None:
            # Create empty metadata dict if none provided
            metadata = {}
        
        # Add standard fields to metadata
        metadata['model_name'] = model_name  # Human-readable name
        metadata['saved_at'] = datetime.now().isoformat()  # ISO timestamp
        metadata['model_type'] = type(model).__name__  # e.g., "XGBClassifier"
        
        # Step 5: Save metadata as separate JSON file
        metadata_file = checkpoint_path / 'metadata.json'
        with open(metadata_file, 'w') as f:
            # Write metadata with pretty printing (indent=2)
            json.dump(metadata, f, indent=2)
        
        # Step 6: Create checkpoint object for in-memory registry
        checkpoint = ModelCheckpoint(
            checkpoint_id=checkpoint_id,
            model_path=model_file,
            metadata=metadata,
            created_at=metadata['saved_at']
        )
        
        # Step 7: Register checkpoint in central registry
        self.checkpoints[checkpoint_id] = checkpoint
        # Save updated registry to disk (checkpoints_metadata.json)
        self._save_metadata()
        
        # Step 8: Log checkpoint creation for debugging
        logger.info(f"Saved checkpoint: {checkpoint_id}")
        logger.info(f"  Model: {model_name}")
        logger.info(f"  Path: {model_file}")
        
        # Return the checkpoint ID so caller can load it later
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
        # Step 1: Validate that the requested checkpoint exists
        if checkpoint_id not in self.checkpoints:
            # Raise descriptive error with list of available checkpoints
            raise ValueError(
                f"Checkpoint '{checkpoint_id}' not found. "
                f"Available: {list(self.checkpoints.keys())}"
            )
        
        # Step 2: Get checkpoint metadata from registry
        checkpoint = self.checkpoints[checkpoint_id]
        
        # Step 3: Verify the model file actually exists on disk
        # (Catches cases where file was deleted but registry not updated)
        if not checkpoint.model_path.exists():
            raise FileNotFoundError(
                f"Model file not found: {checkpoint.model_path}"
            )
        
        # Step 4: Log loading operation
        logger.info(f"Loading checkpoint: {checkpoint_id}")
        
        # Step 5: Deserialize model from disk using joblib
        # joblib.load: Reconstructs the exact model state
        # Works with sklearn, xgboost, lightgbm models
        model = joblib.load(checkpoint.model_path)
        
        # Return the loaded model ready for inference or fine-tuning
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
