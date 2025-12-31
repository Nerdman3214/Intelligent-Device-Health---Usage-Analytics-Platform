"""
Core Quantitative Metrics

Apple principle: Percentiles > Averages
Engineers must understand distributions, not just central tendency.

This module provides defensive statistical metrics WITHOUT machine learning.

Author: Software Engineering Intern
Purpose: Turn raw telemetry into trustworthy numbers
"""

import math
import logging
from typing import List, Dict, Any, Optional
from collections import Counter

logger = logging.getLogger(__name__)


class MetricsError(Exception):
    """Raised when metrics calculation fails due to invalid input"""
    pass


class TelemetryMetrics:
    """
    Calculate core quantitative metrics from telemetry data.
    
    Apple philosophy:
    - Validate statistical assumptions
    - Handle edge cases explicitly
    - Never silently return meaningless results
    - Prefer robust estimators (median, percentiles) over fragile ones (mean)
    """
    
    @staticmethod
    def _validate_numeric_list(
        data: List[float],
        field_name: str,
        min_samples: int = 1
    ) -> None:
        """
        Validate numeric data meets statistical requirements.
        
        Args:
            data: List of numeric values
            field_name: Name of field for error messages
            min_samples: Minimum required samples
            
        Raises:
            MetricsError: If validation fails
        """
        if not data:
            raise MetricsError(
                f"Cannot calculate metrics for '{field_name}': empty dataset"
            )
        
        if len(data) < min_samples:
            raise MetricsError(
                f"Insufficient data for '{field_name}': "
                f"got {len(data)} samples, need at least {min_samples}"
            )
        
        # Check for NaN or infinity
        for i, value in enumerate(data):
            if not isinstance(value, (int, float)):
                raise MetricsError(
                    f"Non-numeric value at index {i} in '{field_name}': {value}"
                )
            if math.isnan(value):
                raise MetricsError(
                    f"NaN value at index {i} in '{field_name}'"
                )
            if math.isinf(value):
                raise MetricsError(
                    f"Infinite value at index {i} in '{field_name}'"
                )
    
    @staticmethod
    def mean(data: List[float], field_name: str = 'data') -> float:
        """
        Calculate arithmetic mean.
        
        Note: Mean is sensitive to outliers. Consider using median() instead
        for skewed distributions.
        
        Args:
            data: List of numeric values
            field_name: Name of field for error reporting
            
        Returns:
            Arithmetic mean
            
        Raises:
            MetricsError: If data is invalid
        """
        TelemetryMetrics._validate_numeric_list(data, field_name)
        return sum(data) / len(data)
    
    @staticmethod
    def median(data: List[float], field_name: str = 'data') -> float:
        """
        Calculate median (50th percentile).
        
        Apple preference: Median is more robust than mean for real-world data.
        
        Args:
            data: List of numeric values
            field_name: Name of field for error reporting
            
        Returns:
            Median value
            
        Raises:
            MetricsError: If data is invalid
        """
        TelemetryMetrics._validate_numeric_list(data, field_name)
        
        sorted_data = sorted(data)
        n = len(sorted_data)
        
        if n % 2 == 0:
            # Even: average of two middle values
            return (sorted_data[n // 2 - 1] + sorted_data[n // 2]) / 2
        else:
            # Odd: middle value
            return sorted_data[n // 2]
    
    @staticmethod
    def percentile(
        data: List[float],
        p: float,
        field_name: str = 'data'
    ) -> float:
        """
        Calculate percentile using linear interpolation.
        
        Apple loves percentiles: P50 (median), P90, P95, P99 for understanding
        tail behavior.
        
        Args:
            data: List of numeric values
            p: Percentile to calculate (0-100)
            field_name: Name of field for error reporting
            
        Returns:
            Value at percentile p
            
        Raises:
            MetricsError: If data is invalid or p out of range
        """
        if not 0 <= p <= 100:
            raise MetricsError(f"Percentile must be in [0, 100], got {p}")
        
        TelemetryMetrics._validate_numeric_list(data, field_name)
        
        sorted_data = sorted(data)
        n = len(sorted_data)
        
        if p == 0:
            return sorted_data[0]
        if p == 100:
            return sorted_data[-1]
        
        # Linear interpolation between ranks
        rank = (p / 100) * (n - 1)
        lower_idx = int(math.floor(rank))
        upper_idx = int(math.ceil(rank))
        
        if lower_idx == upper_idx:
            return sorted_data[lower_idx]
        
        # Interpolate
        weight = rank - lower_idx
        return (1 - weight) * sorted_data[lower_idx] + weight * sorted_data[upper_idx]
    
    @staticmethod
    def variance(
        data: List[float],
        field_name: str = 'data',
        sample: bool = True
    ) -> float:
        """
        Calculate variance.
        
        Args:
            data: List of numeric values
            field_name: Name of field for error reporting
            sample: If True, use sample variance (n-1), else population variance (n)
            
        Returns:
            Variance
            
        Raises:
            MetricsError: If data is invalid
        """
        min_samples = 2 if sample else 1
        TelemetryMetrics._validate_numeric_list(data, field_name, min_samples)
        
        mean_val = TelemetryMetrics.mean(data, field_name)
        squared_diffs = [(x - mean_val) ** 2 for x in data]
        
        divisor = len(data) - 1 if sample else len(data)
        return sum(squared_diffs) / divisor
    
    @staticmethod
    def std_dev(
        data: List[float],
        field_name: str = 'data',
        sample: bool = True
    ) -> float:
        """
        Calculate standard deviation.
        
        Args:
            data: List of numeric values
            field_name: Name of field for error reporting
            sample: If True, use sample std dev, else population std dev
            
        Returns:
            Standard deviation
            
        Raises:
            MetricsError: If data is invalid
        """
        var = TelemetryMetrics.variance(data, field_name, sample)
        return math.sqrt(var)
    
    @staticmethod
    def five_number_summary(
        data: List[float],
        field_name: str = 'data'
    ) -> Dict[str, float]:
        """
        Calculate five-number summary (min, Q1, median, Q3, max).
        
        Essential for understanding distribution shape.
        
        Args:
            data: List of numeric values
            field_name: Name of field for error reporting
            
        Returns:
            Dictionary with min, q1, median, q3, max
            
        Raises:
            MetricsError: If data is invalid
        """
        TelemetryMetrics._validate_numeric_list(data, field_name)
        
        return {
            'min': min(data),
            'q1': TelemetryMetrics.percentile(data, 25, field_name),
            'median': TelemetryMetrics.median(data, field_name),
            'q3': TelemetryMetrics.percentile(data, 75, field_name),
            'max': max(data)
        }
    
    @staticmethod
    def percentile_summary(
        data: List[float],
        percentiles: List[float],
        field_name: str = 'data'
    ) -> Dict[str, float]:
        """
        Calculate multiple percentiles at once.
        
        Common Apple usage: P50, P90, P95, P99
        
        Args:
            data: List of numeric values
            percentiles: List of percentiles to calculate (e.g., [50, 90, 95, 99])
            field_name: Name of field for error reporting
            
        Returns:
            Dictionary mapping percentile to value
            
        Raises:
            MetricsError: If data is invalid
        """
        TelemetryMetrics._validate_numeric_list(data, field_name)
        
        return {
            f'p{int(p)}': TelemetryMetrics.percentile(data, p, field_name)
            for p in percentiles
        }
    
    @staticmethod
    def iqr(data: List[float], field_name: str = 'data') -> float:
        """
        Calculate interquartile range (Q3 - Q1).
        
        Useful for outlier detection in Phase 2.
        
        Args:
            data: List of numeric values
            field_name: Name of field for error reporting
            
        Returns:
            Interquartile range
            
        Raises:
            MetricsError: If data is invalid
        """
        summary = TelemetryMetrics.five_number_summary(data, field_name)
        return summary['q3'] - summary['q1']
    
    @staticmethod
    def coefficient_of_variation(
        data: List[float],
        field_name: str = 'data'
    ) -> float:
        """
        Calculate coefficient of variation (std_dev / mean).
        
        Measures relative variability (unitless).
        
        Args:
            data: List of numeric values
            field_name: Name of field for error reporting
            
        Returns:
            Coefficient of variation
            
        Raises:
            MetricsError: If data is invalid or mean is zero
        """
        mean_val = TelemetryMetrics.mean(data, field_name)
        
        if mean_val == 0:
            raise MetricsError(
                f"Cannot calculate coefficient of variation for '{field_name}': mean is zero"
            )
        
        std = TelemetryMetrics.std_dev(data, field_name)
        return std / abs(mean_val)
    
    @staticmethod
    def mode(data: List[Any], field_name: str = 'data') -> Any:
        """
        Calculate mode (most common value).
        
        Works with any hashable data type.
        
        Args:
            data: List of values
            field_name: Name of field for error reporting
            
        Returns:
            Most common value
            
        Raises:
            MetricsError: If data is empty
        """
        if not data:
            raise MetricsError(f"Cannot calculate mode for '{field_name}': empty dataset")
        
        counter = Counter(data)
        mode_value, _ = counter.most_common(1)[0]
        return mode_value
    
    @staticmethod
    def calculate_telemetry_summary(
        telemetry_records: List[Dict[str, Any]],
        field: str
    ) -> Dict[str, float]:
        """
        Calculate comprehensive summary for a specific telemetry field.
        
        This is the main entry point for Phase 2 analytics.
        
        Args:
            telemetry_records: List of telemetry dictionaries
            field: Field name to analyze (e.g., 'cpu_usage', 'battery_health')
            
        Returns:
            Dictionary with comprehensive statistics
            
        Raises:
            MetricsError: If field is missing or data is invalid
        """
        if not telemetry_records:
            raise MetricsError("Cannot calculate summary: no telemetry records")
        
        # Extract field values
        values = []
        for i, record in enumerate(telemetry_records):
            if field not in record:
                raise MetricsError(
                    f"Field '{field}' missing in record {i}"
                )
            values.append(record[field])
        
        # Calculate comprehensive metrics
        try:
            return {
                'count': len(values),
                'mean': round(TelemetryMetrics.mean(values, field), 4),
                'median': round(TelemetryMetrics.median(values, field), 4),
                'std_dev': round(TelemetryMetrics.std_dev(values, field), 4),
                'min': round(min(values), 4),
                'max': round(max(values), 4),
                'p25': round(TelemetryMetrics.percentile(values, 25, field), 4),
                'p50': round(TelemetryMetrics.percentile(values, 50, field), 4),
                'p75': round(TelemetryMetrics.percentile(values, 75, field), 4),
                'p90': round(TelemetryMetrics.percentile(values, 90, field), 4),
                'p95': round(TelemetryMetrics.percentile(values, 95, field), 4),
                'p99': round(TelemetryMetrics.percentile(values, 99, field), 4),
                'iqr': round(TelemetryMetrics.iqr(values, field), 4),
            }
        except MetricsError:
            raise
        except Exception as e:
            raise MetricsError(f"Failed to calculate metrics for '{field}': {e}")
