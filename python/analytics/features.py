"""
Feature Engineering for Predictive Device Health Analytics

Apple principle: Features must be explainable to non-ML engineers.

This module extracts ML features from telemetry data without black-box transformations.
Every feature has a clear interpretation and purpose.

Author: Software Engineering Intern
Purpose: Convert telemetry → ML-ready features for risk prediction
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import math

from .metrics import TelemetryMetrics, MetricsError
from .trends import TrendAnalyzer, TimeSeriesPoint

logger = logging.getLogger(__name__)


class FeatureExtractionError(Exception):
    """Raised when feature extraction fails"""
    pass


class DeviceFeatures:
    """
    ML features extracted from device telemetry.
    
    All features are interpretable and defensively computed.
    """
    
    def __init__(
        self,
        device_id: str,
        features: Dict[str, float],
        metadata: Dict[str, Any]
    ):
        self.device_id = device_id
        self.features = features
        self.metadata = metadata
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'device_id': self.device_id,
            'features': self.features,
            'metadata': self.metadata
        }
    
    def get_feature_vector(self, feature_names: List[str]) -> List[float]:
        """
        Get ordered feature vector for ML model.
        
        Args:
            feature_names: Ordered list of feature names
            
        Returns:
            List of feature values in specified order
            
        Raises:
            FeatureExtractionError: If feature is missing
        """
        vector = []
        for name in feature_names:
            if name not in self.features:
                raise FeatureExtractionError(
                    f"Feature '{name}' not found in extracted features"
                )
            vector.append(self.features[name])
        return vector


class FeatureExtractor:
    """
    Extract interpretable features from device telemetry.
    
    Feature Categories:
    1. Statistical aggregates (mean, median, P90, etc.)
    2. Trend indicators (slopes, week-over-week changes)
    3. Anomaly indicators (outlier counts, Z-score extremes)
    4. Usage patterns (app diversity, thermal event frequency)
    5. Temporal features (time since first sample, sample count)
    """
    
    # Feature names (for consistent ordering)
    FEATURE_NAMES = [
        # Battery health features
        'battery_health_mean',
        'battery_health_median',
        'battery_health_std',
        'battery_health_min',
        'battery_health_trend_slope',
        
        # CPU usage features
        'cpu_usage_mean',
        'cpu_usage_median',
        'cpu_usage_p90',
        'cpu_usage_p95',
        'cpu_usage_std',
        'cpu_usage_spike_count',  # How many samples > 90%
        
        # Memory usage features
        'memory_usage_mean',
        'memory_usage_p90',
        'memory_usage_p95',
        
        # Thermal features
        'thermal_critical_ratio',  # Fraction of samples in critical state
        'thermal_serious_or_worse_ratio',
        
        # Usage pattern features
        'total_app_count',  # Number of unique apps used
        'avg_apps_per_sample',
        'network_sent_mean',
        'network_received_mean',
        
        # Temporal features
        'sample_count',
        'time_span_days',
    ]
    
    @staticmethod
    def _validate_telemetry_records(
        records: List[Dict[str, Any]],
        min_samples: int = 10
    ) -> None:
        """
        Validate telemetry records meet feature extraction requirements.
        
        Args:
            records: List of telemetry dictionaries
            min_samples: Minimum required samples
            
        Raises:
            FeatureExtractionError: If validation fails
        """
        if not records:
            raise FeatureExtractionError("Cannot extract features: empty telemetry")
        
        if len(records) < min_samples:
            raise FeatureExtractionError(
                f"Insufficient samples for reliable features: "
                f"got {len(records)}, need at least {min_samples}"
            )
        
        # Check required fields
        required_fields = [
            'device_id', 'timestamp', 'battery_health', 'cpu_usage',
            'memory_usage', 'thermal_state', 'app_foreground_time',
            'network_bytes_sent', 'network_bytes_received'
        ]
        
        for i, record in enumerate(records[:3]):  # Check first 3
            for field in required_fields:
                if field not in record:
                    raise FeatureExtractionError(
                        f"Record {i} missing required field '{field}'"
                    )
    
    @staticmethod
    def _extract_statistical_features(
        records: List[Dict[str, Any]],
        field: str
    ) -> Dict[str, float]:
        """
        Extract statistical features for a numeric field.
        
        Args:
            records: Telemetry records
            field: Field name to analyze
            
        Returns:
            Dictionary of statistical features
        """
        try:
            values = [r[field] for r in records]
            
            return {
                f'{field}_mean': TelemetryMetrics.mean(values, field),
                f'{field}_median': TelemetryMetrics.median(values, field),
                f'{field}_std': TelemetryMetrics.std_dev(values, field),
                f'{field}_min': min(values),
                f'{field}_max': max(values),
                f'{field}_p90': TelemetryMetrics.percentile(values, 90, field),
                f'{field}_p95': TelemetryMetrics.percentile(values, 95, field),
            }
        except Exception as e:
            logger.warning(f"Statistical feature extraction failed for {field}: {e}")
            return {}
    
    @staticmethod
    def _extract_trend_features(
        records: List[Dict[str, Any]],
        field: str
    ) -> Dict[str, float]:
        """
        Extract trend features for a time-series field.
        
        Args:
            records: Telemetry records (sorted by timestamp)
            field: Field name to analyze
            
        Returns:
            Dictionary of trend features
        """
        try:
            time_series = [
                TimeSeriesPoint(r['timestamp'], r[field])
                for r in records
            ]
            
            trend_info = TrendAnalyzer.estimate_slope(
                time_series,
                normalize_time=True
            )
            
            return {
                f'{field}_trend_slope': trend_info['slope'],
                f'{field}_trend_r_squared': trend_info['r_squared'],
            }
        except Exception as e:
            logger.warning(f"Trend feature extraction failed for {field}: {e}")
            return {
                f'{field}_trend_slope': 0.0,
                f'{field}_trend_r_squared': 0.0,
            }
    
    @staticmethod
    def extract_features(
        device_id: str,
        telemetry_records: List[Dict[str, Any]]
    ) -> DeviceFeatures:
        """
        Extract comprehensive feature set from telemetry.
        
        This is the main entry point for feature extraction.
        
        Args:
            device_id: Device identifier
            telemetry_records: List of telemetry dictionaries
            
        Returns:
            DeviceFeatures with extracted features
            
        Raises:
            FeatureExtractionError: If extraction fails
        """
        # Validate inputs
        FeatureExtractor._validate_telemetry_records(telemetry_records)
        
        # Sort by timestamp
        sorted_records = sorted(telemetry_records, key=lambda r: r['timestamp'])
        
        features = {}
        
        # === BATTERY HEALTH FEATURES ===
        battery_values = [r['battery_health'] for r in sorted_records]
        features['battery_health_mean'] = TelemetryMetrics.mean(battery_values, 'battery_health')
        features['battery_health_median'] = TelemetryMetrics.median(battery_values, 'battery_health')
        features['battery_health_std'] = TelemetryMetrics.std_dev(battery_values, 'battery_health')
        features['battery_health_min'] = min(battery_values)
        
        # Battery trend (degradation rate)
        battery_trend = FeatureExtractor._extract_trend_features(sorted_records, 'battery_health')
        features['battery_health_trend_slope'] = battery_trend.get('battery_health_trend_slope', 0.0)
        
        # === CPU USAGE FEATURES ===
        cpu_values = [r['cpu_usage'] for r in sorted_records]
        features['cpu_usage_mean'] = TelemetryMetrics.mean(cpu_values, 'cpu_usage')
        features['cpu_usage_median'] = TelemetryMetrics.median(cpu_values, 'cpu_usage')
        features['cpu_usage_p90'] = TelemetryMetrics.percentile(cpu_values, 90, 'cpu_usage')
        features['cpu_usage_p95'] = TelemetryMetrics.percentile(cpu_values, 95, 'cpu_usage')
        features['cpu_usage_std'] = TelemetryMetrics.std_dev(cpu_values, 'cpu_usage')
        
        # CPU spikes (count of samples > 90%)
        features['cpu_usage_spike_count'] = sum(1 for v in cpu_values if v > 90.0) / len(cpu_values)
        
        # === MEMORY USAGE FEATURES ===
        memory_values = [r['memory_usage'] for r in sorted_records]
        features['memory_usage_mean'] = TelemetryMetrics.mean(memory_values, 'memory_usage')
        features['memory_usage_p90'] = TelemetryMetrics.percentile(memory_values, 90, 'memory_usage')
        features['memory_usage_p95'] = TelemetryMetrics.percentile(memory_values, 95, 'memory_usage')
        
        # === THERMAL FEATURES ===
        thermal_states = [r['thermal_state'].value for r in sorted_records]
        total = len(thermal_states)
        
        critical_count = sum(1 for s in thermal_states if s == 'critical')
        serious_or_worse = sum(1 for s in thermal_states if s in ['serious', 'critical'])
        
        features['thermal_critical_ratio'] = critical_count / total
        features['thermal_serious_or_worse_ratio'] = serious_or_worse / total
        
        # === USAGE PATTERN FEATURES ===
        all_apps = set()
        total_app_instances = 0
        
        for record in sorted_records:
            apps = record['app_foreground_time'].keys()
            all_apps.update(apps)
            total_app_instances += len(apps)
        
        features['total_app_count'] = len(all_apps)
        features['avg_apps_per_sample'] = total_app_instances / len(sorted_records)
        
        # Network usage
        network_sent = [r['network_bytes_sent'] for r in sorted_records]
        network_received = [r['network_bytes_received'] for r in sorted_records]
        
        features['network_sent_mean'] = sum(network_sent) / len(network_sent) / 1e6  # Convert to MB
        features['network_received_mean'] = sum(network_received) / len(network_received) / 1e6
        
        # === TEMPORAL FEATURES ===
        features['sample_count'] = len(sorted_records)
        
        time_span = (sorted_records[-1]['timestamp'] - sorted_records[0]['timestamp'])
        features['time_span_days'] = time_span.total_seconds() / 86400
        
        # === METADATA ===
        metadata = {
            'device_id': device_id,
            'extraction_time': datetime.now().isoformat(),
            'num_samples': len(sorted_records),
            'time_range': {
                'start': sorted_records[0]['timestamp'].isoformat(),
                'end': sorted_records[-1]['timestamp'].isoformat(),
            },
            'feature_count': len(features),
        }
        
        # Validate all expected features are present
        missing_features = set(FeatureExtractor.FEATURE_NAMES) - set(features.keys())
        if missing_features:
            logger.warning(f"Missing features: {missing_features}")
        
        return DeviceFeatures(
            device_id=device_id,
            features=features,
            metadata=metadata
        )
    
    @staticmethod
    def get_feature_names() -> List[str]:
        """Get ordered list of feature names"""
        return FeatureExtractor.FEATURE_NAMES.copy()
