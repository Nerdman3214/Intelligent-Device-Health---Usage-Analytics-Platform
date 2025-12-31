"""
Data Ingestion Pipeline

Orchestrates the flow: generate → validate → normalize → store

Apple principles:
- Invalid data is REJECTED, not silently fixed
- All rejections are LOGGED with clear reasons
- NO partial writes (atomic operations)
- NO silent coercion

Author: Software Engineering Intern
Purpose: Production-grade defensive data ingestion
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

from .generator import TelemetryGenerator
from .validator import TelemetryValidator, ValidationResult
from .schemas import TelemetrySchema, ThermalState, DeviceType


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IngestionStats:
    """Track ingestion pipeline statistics"""
    
    def __init__(self):
        self.total_processed = 0
        self.total_accepted = 0
        self.total_rejected = 0
        self.rejection_reasons: Dict[str, int] = {}
    
    def record_acceptance(self):
        """Record a successful validation"""
        self.total_processed += 1
        self.total_accepted += 1
    
    def record_rejection(self, reason: str):
        """Record a validation failure"""
        self.total_processed += 1
        self.total_rejected += 1
        self.rejection_reasons[reason] = self.rejection_reasons.get(reason, 0) + 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics"""
        acceptance_rate = (
            (self.total_accepted / self.total_processed * 100)
            if self.total_processed > 0
            else 0.0
        )
        
        return {
            'total_processed': self.total_processed,
            'total_accepted': self.total_accepted,
            'total_rejected': self.total_rejected,
            'acceptance_rate_percent': round(acceptance_rate, 2),
            'rejection_reasons': self.rejection_reasons
        }
    
    def log_summary(self):
        """Log summary statistics"""
        summary = self.get_summary()
        logger.info("=" * 60)
        logger.info("INGESTION PIPELINE SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total Processed: {summary['total_processed']}")
        logger.info(f"Accepted: {summary['total_accepted']}")
        logger.info(f"Rejected: {summary['total_rejected']}")
        logger.info(f"Acceptance Rate: {summary['acceptance_rate_percent']}%")
        
        if summary['rejection_reasons']:
            logger.info("\nRejection Breakdown:")
            for reason, count in summary['rejection_reasons'].items():
                logger.info(f"  - {reason}: {count}")
        logger.info("=" * 60)


class TelemetryIngestor:
    """
    Production-grade telemetry ingestion pipeline.
    
    Workflow:
    1. Receive raw data
    2. Validate (STRICT - no silent failures)
    3. Normalize (convert to schema)
    4. Store (atomic write to processed/)
    
    Rejected data is:
    - Logged with full error context
    - Written to rejected/ directory for analysis
    - NEVER silently dropped
    """
    
    def __init__(self, data_dir: Path | str):
        """
        Initialize ingestor with data directory.
        
        Args:
            data_dir: Base directory for data storage
        """
        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / 'raw'
        self.processed_dir = self.data_dir / 'processed'
        self.rejected_dir = self.data_dir / 'rejected'
        
        # Create directories if they don't exist
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.rejected_dir.mkdir(parents=True, exist_ok=True)
        
        self.validator = TelemetryValidator()
        self.stats = IngestionStats()
        
        logger.info(f"Ingestor initialized with data_dir: {self.data_dir}")
    
    def normalize_data(self, validated_data: Dict[str, Any]) -> TelemetrySchema:
        """
        Convert validated dictionary to TelemetrySchema.
        
        This happens AFTER validation, so we trust the data structure.
        
        Args:
            validated_data: Dictionary that passed validation
            
        Returns:
            TelemetrySchema object
        """
        return TelemetrySchema(
            device_id=validated_data['device_id'],
            timestamp=validated_data['timestamp'],
            cpu_usage=validated_data['cpu_usage'],
            memory_usage=validated_data['memory_usage'],
            battery_health=validated_data['battery_health'],
            battery_level=validated_data['battery_level'],
            thermal_state=validated_data['thermal_state'],
            device_type=validated_data['device_type'],
            app_foreground_time=validated_data['app_foreground_time'],
            network_bytes_sent=validated_data['network_bytes_sent'],
            network_bytes_received=validated_data['network_bytes_received'],
            os_version=validated_data.get('os_version'),
            location_enabled=validated_data.get('location_enabled')
        )
    
    def store_processed(self, schema: TelemetrySchema) -> Path:
        """
        Store processed telemetry data.
        
        Uses timestamp-based filename for easy time-series queries.
        
        Args:
            schema: Validated and normalized telemetry schema
            
        Returns:
            Path to stored file
        """
        timestamp_str = schema.timestamp.strftime('%Y%m%d_%H%M%S')
        filename = f"{schema.device_id}_{timestamp_str}.json"
        filepath = self.processed_dir / filename
        
        # Atomic write: write to temp file, then rename
        temp_filepath = filepath.with_suffix('.tmp')
        
        with open(temp_filepath, 'w') as f:
            json.dump(schema.to_dict(), f, indent=2, default=str)
        
        temp_filepath.rename(filepath)
        
        return filepath
    
    def store_rejected(
        self,
        raw_data: Dict[str, Any],
        validation_result: ValidationResult
    ) -> Path:
        """
        Store rejected data with error details for analysis.
        
        Apple principle: Rejections should be debuggable.
        
        Args:
            raw_data: Original data that failed validation
            validation_result: Validation result with errors
            
        Returns:
            Path to rejected data file
        """
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        filename = f"rejected_{timestamp_str}.json"
        filepath = self.rejected_dir / filename
        
        rejection_record = {
            'timestamp': datetime.now().isoformat(),
            'raw_data': raw_data,
            'errors': [
                {
                    'field': err.field,
                    'value': str(err.value),
                    'reason': err.reason,
                    'expected': err.expected
                }
                for err in validation_result.errors
            ]
        }
        
        with open(filepath, 'w') as f:
            json.dump(rejection_record, f, indent=2, default=str)
        
        return filepath
    
    def ingest_single(self, raw_data: Dict[str, Any]) -> bool:
        """
        Ingest a single telemetry record.
        
        Args:
            raw_data: Raw telemetry dictionary
            
        Returns:
            True if accepted, False if rejected
        """
        # Step 1: Validate
        validation_result = self.validator.validate_telemetry(raw_data)
        
        if not validation_result.valid:
            # Log rejection
            logger.warning(f"Rejected telemetry for device {raw_data.get('device_id', 'UNKNOWN')}")
            validation_result.log_errors()
            
            # Store rejected data
            self.store_rejected(raw_data, validation_result)
            
            # Track stats
            primary_error = validation_result.errors[0].field if validation_result.errors else 'unknown'
            self.stats.record_rejection(f"Invalid {primary_error}")
            
            return False
        
        # Step 2: Normalize
        try:
            schema = self.normalize_data(validation_result.data)
        except Exception as e:
            logger.error(f"Normalization failed: {e}")
            self.stats.record_rejection("Normalization error")
            return False
        
        # Step 3: Store
        try:
            filepath = self.store_processed(schema)
            logger.debug(f"Stored telemetry: {filepath.name}")
            self.stats.record_acceptance()
            return True
        except Exception as e:
            logger.error(f"Storage failed: {e}")
            self.stats.record_rejection("Storage error")
            return False
    
    def ingest_batch(self, batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Ingest a batch of telemetry records.
        
        Args:
            batch: List of raw telemetry dictionaries
            
        Returns:
            Summary of batch ingestion results
        """
        logger.info(f"Starting batch ingestion: {len(batch)} records")
        
        accepted = 0
        rejected = 0
        
        for record in batch:
            if self.ingest_single(record):
                accepted += 1
            else:
                rejected += 1
        
        logger.info(f"Batch complete: {accepted} accepted, {rejected} rejected")
        
        return {
            'total': len(batch),
            'accepted': accepted,
            'rejected': rejected,
            'acceptance_rate': (accepted / len(batch) * 100) if batch else 0.0
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get ingestion statistics"""
        return self.stats.get_summary()
    
    def reset_stats(self):
        """Reset ingestion statistics"""
        self.stats = IngestionStats()
        logger.info("Ingestion statistics reset")


# Convenience function for quick testing
def run_ingestion_demo(data_dir: Path | str, num_records: int = 100):
    """
    Run a demo ingestion with mixed quality data.
    
    Args:
        data_dir: Directory for data storage
        num_records: Number of records to generate and ingest
    """
    logger.info("=" * 60)
    logger.info("INGESTION DEMO")
    logger.info("=" * 60)
    
    ingestor = TelemetryIngestor(data_dir)
    
    # Generate mixed quality batch (90% good, 10% corrupted)
    logger.info(f"Generating {num_records} telemetry records (90% clean, 10% corrupted)")
    batch = TelemetryGenerator.generate_batch(
        count=num_records,
        quality='clean',
        corruption_rate=0.10
    )
    
    # Ingest batch
    result = ingestor.ingest_batch(batch)
    
    # Print summary
    logger.info("\nDemo Results:")
    logger.info(f"Total: {result['total']}")
    logger.info(f"Accepted: {result['accepted']}")
    logger.info(f"Rejected: {result['rejected']}")
    logger.info(f"Acceptance Rate: {result['acceptance_rate']:.1f}%")
    
    ingestor.stats.log_summary()
