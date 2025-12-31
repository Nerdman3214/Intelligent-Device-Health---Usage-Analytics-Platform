"""
Statistical Anomaly Detection

Apple principle: Simple, explainable rules BEFORE machine learning.

This module detects anomalies using statistical methods:
- Z-score (standard deviations from mean)
- IQR (interquartile range method)
- Threshold-based alerts
- Rate-of-change checks

NO machine learning. NO black boxes.

Author: Software Engineering Intern
Purpose: Detect unusual behavior with explainable statistics
"""

import math
import logging
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from datetime import datetime

from .metrics import TelemetryMetrics, MetricsError
from .trends import TimeSeriesPoint

logger = logging.getLogger(__name__)


class AnomalySeverity(Enum):
    """Severity levels for detected anomalies"""
    INFO = "info"  # Slightly unusual but not concerning
    WARNING = "warning"  # Should investigate
    CRITICAL = "critical"  # Immediate attention required


class AnomalyType(Enum):
    """Types of anomalies we can detect"""
    Z_SCORE = "z_score"  # Statistical outlier
    IQR = "iqr"  # Outside interquartile range
    THRESHOLD = "threshold"  # Exceeds absolute threshold
    RATE_OF_CHANGE = "rate_of_change"  # Changing too fast
    CONSECUTIVE = "consecutive"  # Multiple anomalies in a row


class Anomaly:
    """
    Detected anomaly with full context.
    
    Apple principle: Anomalies should be debuggable.
    """
    
    def __init__(
        self,
        timestamp: datetime,
        value: float,
        field: str,
        anomaly_type: AnomalyType,
        severity: AnomalySeverity,
        reason: str,
        expected_range: Optional[Tuple[float, float]] = None,
        confidence: float = 1.0
    ):
        self.timestamp = timestamp
        self.value = value
        self.field = field
        self.anomaly_type = anomaly_type
        self.severity = severity
        self.reason = reason
        self.expected_range = expected_range
        self.confidence = confidence
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'value': self.value,
            'field': self.field,
            'type': self.anomaly_type.value,
            'severity': self.severity.value,
            'reason': self.reason,
            'expected_range': self.expected_range,
            'confidence': self.confidence
        }
    
    def __repr__(self):
        return (
            f"Anomaly({self.severity.value.upper()}: {self.field}={self.value} "
            f"at {self.timestamp}, reason: {self.reason})"
        )


class AnomalyDetector:
    """
    Statistical anomaly detection for telemetry data.
    
    Methods are explainable and don't require ML expertise to understand.
    """
    
    @staticmethod
    def z_score_detection(
        data: List[float],
        threshold: float = 3.0,
        field_name: str = 'data'
    ) -> List[int]:
        """
        Detect anomalies using Z-score method.
        
        Z-score = (value - mean) / std_dev
        
        Points with |Z-score| > threshold are anomalies.
        
        Args:
            data: List of numeric values
            threshold: Z-score threshold (typically 2.5-3.5)
            field_name: Name of field for error reporting
            
        Returns:
            List of indices of anomalous points
            
        Raises:
            MetricsError: If data is invalid
        """
        if len(data) < 3:
            raise MetricsError(
                f"Z-score detection requires at least 3 points, got {len(data)}"
            )
        
        mean = TelemetryMetrics.mean(data, field_name)
        std_dev = TelemetryMetrics.std_dev(data, field_name)
        
        if std_dev == 0:
            # All values are identical - no anomalies
            return []
        
        anomalies = []
        
        for i, value in enumerate(data):
            z_score = abs((value - mean) / std_dev)
            if z_score > threshold:
                anomalies.append(i)
        
        return anomalies
    
    @staticmethod
    def iqr_detection(
        data: List[float],
        multiplier: float = 1.5,
        field_name: str = 'data'
    ) -> List[int]:
        """
        Detect anomalies using IQR (Interquartile Range) method.
        
        Tukey's method:
        - Lower fence: Q1 - multiplier * IQR
        - Upper fence: Q3 + multiplier * IQR
        
        Values outside fences are anomalies.
        
        Args:
            data: List of numeric values
            multiplier: IQR multiplier (1.5 = outliers, 3.0 = extreme outliers)
            field_name: Name of field for error reporting
            
        Returns:
            List of indices of anomalous points
            
        Raises:
            MetricsError: If data is invalid
        """
        if len(data) < 4:
            raise MetricsError(
                f"IQR detection requires at least 4 points, got {len(data)}"
            )
        
        summary = TelemetryMetrics.five_number_summary(data, field_name)
        q1 = summary['q1']
        q3 = summary['q3']
        iqr = q3 - q1
        
        lower_fence = q1 - multiplier * iqr
        upper_fence = q3 + multiplier * iqr
        
        anomalies = []
        
        for i, value in enumerate(data):
            if value < lower_fence or value > upper_fence:
                anomalies.append(i)
        
        return anomalies
    
    @staticmethod
    def threshold_detection(
        data: List[float],
        lower_threshold: Optional[float] = None,
        upper_threshold: Optional[float] = None
    ) -> List[int]:
        """
        Detect anomalies using absolute thresholds.
        
        Simple but effective for known acceptable ranges.
        
        Args:
            data: List of numeric values
            lower_threshold: Minimum acceptable value (None = no lower limit)
            upper_threshold: Maximum acceptable value (None = no upper limit)
            
        Returns:
            List of indices of anomalous points
        """
        if lower_threshold is None and upper_threshold is None:
            raise ValueError("At least one threshold must be specified")
        
        anomalies = []
        
        for i, value in enumerate(data):
            if lower_threshold is not None and value < lower_threshold:
                anomalies.append(i)
            elif upper_threshold is not None and value > upper_threshold:
                anomalies.append(i)
        
        return anomalies
    
    @staticmethod
    def rate_of_change_detection(
        time_series: List[TimeSeriesPoint],
        max_rate: float,
        field_name: str = 'data'
    ) -> List[int]:
        """
        Detect anomalies based on rate of change.
        
        Useful for detecting sudden jumps or drops.
        
        Args:
            time_series: List of time series points (must be sorted)
            max_rate: Maximum acceptable change per second
            field_name: Name of field for error reporting
            
        Returns:
            List of indices where rate exceeds threshold
        """
        if len(time_series) < 2:
            raise ValueError("Need at least 2 points for rate of change detection")
        
        anomalies = []
        
        for i in range(1, len(time_series)):
            prev = time_series[i-1]
            curr = time_series[i]
            
            time_diff = (curr.timestamp - prev.timestamp).total_seconds()
            
            if time_diff <= 0:
                # Invalid time sequence
                logger.warning(
                    f"Invalid time sequence at index {i}: timestamps not increasing"
                )
                continue
            
            value_diff = abs(curr.value - prev.value)
            rate = value_diff / time_diff
            
            if rate > max_rate:
                anomalies.append(i)
        
        return anomalies
    
    @staticmethod
    def detect_anomalies_comprehensive(
        telemetry_records: List[Dict[str, Any]],
        field: str,
        z_score_threshold: float = 3.0,
        iqr_multiplier: float = 1.5,
        absolute_thresholds: Optional[Dict[str, float]] = None
    ) -> List[Anomaly]:
        """
        Comprehensive anomaly detection combining multiple methods.
        
        This is the main entry point for Phase 2 anomaly detection.
        
        Args:
            telemetry_records: List of telemetry dictionaries
            field: Field to analyze
            z_score_threshold: Threshold for Z-score method
            iqr_multiplier: Multiplier for IQR method
            absolute_thresholds: Optional dict with 'lower' and 'upper' keys
            
        Returns:
            List of detected anomalies with full context
        """
        if not telemetry_records:
            return []
        
        # Extract values and timestamps
        values = []
        timestamps = []
        
        for record in telemetry_records:
            if field not in record:
                raise ValueError(f"Field '{field}' not found in telemetry records")
            
            values.append(record[field])
            timestamps.append(record['timestamp'])
        
        detected_anomalies = []
        
        # Method 1: Z-score detection
        try:
            z_anomaly_indices = AnomalyDetector.z_score_detection(
                values, z_score_threshold, field
            )
            
            mean = TelemetryMetrics.mean(values, field)
            std_dev = TelemetryMetrics.std_dev(values, field)
            
            for idx in z_anomaly_indices:
                z_score = abs((values[idx] - mean) / std_dev)
                
                severity = (
                    AnomalySeverity.CRITICAL if z_score > 4.0
                    else AnomalySeverity.WARNING if z_score > 3.0
                    else AnomalySeverity.INFO
                )
                
                detected_anomalies.append(Anomaly(
                    timestamp=timestamps[idx],
                    value=values[idx],
                    field=field,
                    anomaly_type=AnomalyType.Z_SCORE,
                    severity=severity,
                    reason=f"Z-score {z_score:.2f} exceeds threshold {z_score_threshold}",
                    expected_range=(mean - z_score_threshold * std_dev, 
                                   mean + z_score_threshold * std_dev),
                    confidence=min(1.0, z_score / 5.0)  # Higher z-score = higher confidence
                ))
        
        except MetricsError as e:
            logger.warning(f"Z-score detection failed: {e}")
        
        # Method 2: IQR detection
        try:
            iqr_anomaly_indices = AnomalyDetector.iqr_detection(
                values, iqr_multiplier, field
            )
            
            summary = TelemetryMetrics.five_number_summary(values, field)
            q1, q3 = summary['q1'], summary['q3']
            iqr = q3 - q1
            lower_fence = q1 - iqr_multiplier * iqr
            upper_fence = q3 + iqr_multiplier * iqr
            
            for idx in iqr_anomaly_indices:
                # Skip if already detected by Z-score
                if idx in z_anomaly_indices:
                    continue
                
                distance_from_fence = min(
                    abs(values[idx] - lower_fence),
                    abs(values[idx] - upper_fence)
                )
                
                severity = (
                    AnomalySeverity.CRITICAL if distance_from_fence > iqr * 2
                    else AnomalySeverity.WARNING if distance_from_fence > iqr
                    else AnomalySeverity.INFO
                )
                
                detected_anomalies.append(Anomaly(
                    timestamp=timestamps[idx],
                    value=values[idx],
                    field=field,
                    anomaly_type=AnomalyType.IQR,
                    severity=severity,
                    reason=f"Value outside IQR fences (multiplier={iqr_multiplier})",
                    expected_range=(lower_fence, upper_fence),
                    confidence=0.85
                ))
        
        except MetricsError as e:
            logger.warning(f"IQR detection failed: {e}")
        
        # Method 3: Absolute threshold detection
        if absolute_thresholds:
            threshold_indices = AnomalyDetector.threshold_detection(
                values,
                lower_threshold=absolute_thresholds.get('lower'),
                upper_threshold=absolute_thresholds.get('upper')
            )
            
            for idx in threshold_indices:
                # Skip if already detected
                if idx in z_anomaly_indices or idx in iqr_anomaly_indices:
                    continue
                
                lower = absolute_thresholds.get('lower', float('-inf'))
                upper = absolute_thresholds.get('upper', float('inf'))
                
                detected_anomalies.append(Anomaly(
                    timestamp=timestamps[idx],
                    value=values[idx],
                    field=field,
                    anomaly_type=AnomalyType.THRESHOLD,
                    severity=AnomalySeverity.CRITICAL,
                    reason=f"Value outside acceptable range [{lower}, {upper}]",
                    expected_range=(lower, upper),
                    confidence=1.0
                ))
        
        # Sort anomalies by timestamp
        detected_anomalies.sort(key=lambda a: a.timestamp)
        
        return detected_anomalies
    
    @staticmethod
    def detect_consecutive_anomalies(
        anomalies: List[Anomaly],
        min_consecutive: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Detect patterns of consecutive anomalies.
        
        Multiple anomalies in a row may indicate systematic issues.
        
        Args:
            anomalies: List of detected anomalies (sorted by timestamp)
            min_consecutive: Minimum consecutive anomalies to report
            
        Returns:
            List of consecutive anomaly patterns
        """
        if len(anomalies) < min_consecutive:
            return []
        
        patterns = []
        current_streak = [anomalies[0]]
        
        for i in range(1, len(anomalies)):
            # Check if this anomaly is for the same field as previous
            if anomalies[i].field == current_streak[0].field:
                current_streak.append(anomalies[i])
            else:
                # Check if streak meets threshold
                if len(current_streak) >= min_consecutive:
                    patterns.append({
                        'field': current_streak[0].field,
                        'start_time': current_streak[0].timestamp,
                        'end_time': current_streak[-1].timestamp,
                        'count': len(current_streak),
                        'severity': max(a.severity.value for a in current_streak),
                        'anomalies': current_streak
                    })
                
                # Start new streak
                current_streak = [anomalies[i]]
        
        # Check final streak
        if len(current_streak) >= min_consecutive:
            patterns.append({
                'field': current_streak[0].field,
                'start_time': current_streak[0].timestamp,
                'end_time': current_streak[-1].timestamp,
                'count': len(current_streak),
                'severity': max(a.severity.value for a in current_streak),
                'anomalies': current_streak
            })
        
        return patterns
