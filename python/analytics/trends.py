"""
Time-Series Trend Analysis

Detect changes over time using statistical methods (NOT machine learning).

Apple philosophy:
- Trends must be explainable to non-ML engineers
- Use simple math: moving averages, slopes, differences
- No black boxes

Author: Software Engineering Intern
Purpose: Understand time-series behavior without ML
"""

import math
import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from .metrics import MetricsError

logger = logging.getLogger(__name__)


class TrendsError(Exception):
    """Raised when trend analysis fails"""
    pass


class TimeSeriesPoint:
    """Single point in time series"""
    
    def __init__(self, timestamp: datetime, value: float):
        self.timestamp = timestamp
        self.value = value
    
    def __repr__(self):
        return f"TimeSeriesPoint({self.timestamp}, {self.value})"


class TrendAnalyzer:
    """
    Analyze time-series trends in telemetry data.
    
    Methods:
    - Moving averages (simple, exponential)
    - Rolling windows
    - First-order differences (rate of change)
    - Slope estimation (linear regression)
    - Week-over-week comparisons
    """
    
    @staticmethod
    def _validate_time_series(
        data: List[TimeSeriesPoint],
        min_points: int = 2
    ) -> None:
        """
        Validate time series data.
        
        Args:
            data: List of time series points
            min_points: Minimum required points
            
        Raises:
            TrendsError: If validation fails
        """
        if not data:
            raise TrendsError("Cannot analyze trends: empty time series")
        
        if len(data) < min_points:
            raise TrendsError(
                f"Insufficient data: got {len(data)} points, need at least {min_points}"
            )
        
        # Check timestamps are sorted
        for i in range(1, len(data)):
            if data[i].timestamp < data[i-1].timestamp:
                raise TrendsError(
                    f"Time series must be sorted: timestamp at index {i} "
                    f"is before timestamp at index {i-1}"
                )
    
    @staticmethod
    def simple_moving_average(
        data: List[TimeSeriesPoint],
        window_size: int
    ) -> List[TimeSeriesPoint]:
        """
        Calculate simple moving average.
        
        SMA smooths noise and reveals underlying trends.
        
        Args:
            data: List of time series points (must be sorted by timestamp)
            window_size: Number of points in moving window
            
        Returns:
            List of smoothed time series points
            
        Raises:
            TrendsError: If data is invalid
        """
        TrendAnalyzer._validate_time_series(data, min_points=window_size)
        
        if window_size < 1:
            raise TrendsError(f"Window size must be >= 1, got {window_size}")
        
        if window_size > len(data):
            raise TrendsError(
                f"Window size {window_size} exceeds data length {len(data)}"
            )
        
        smoothed = []
        
        for i in range(len(data) - window_size + 1):
            window = data[i:i + window_size]
            avg_value = sum(p.value for p in window) / window_size
            
            # Use timestamp of last point in window
            smoothed.append(TimeSeriesPoint(
                timestamp=window[-1].timestamp,
                value=avg_value
            ))
        
        return smoothed
    
    @staticmethod
    def exponential_moving_average(
        data: List[TimeSeriesPoint],
        alpha: float = 0.3
    ) -> List[TimeSeriesPoint]:
        """
        Calculate exponential moving average.
        
        EMA gives more weight to recent observations.
        
        Args:
            data: List of time series points (must be sorted)
            alpha: Smoothing factor in (0, 1). Higher = more weight on recent data
            
        Returns:
            List of smoothed time series points
            
        Raises:
            TrendsError: If data is invalid
        """
        TrendAnalyzer._validate_time_series(data, min_points=2)
        
        if not 0 < alpha < 1:
            raise TrendsError(f"Alpha must be in (0, 1), got {alpha}")
        
        smoothed = []
        ema = data[0].value  # Initialize with first value
        
        for point in data:
            ema = alpha * point.value + (1 - alpha) * ema
            smoothed.append(TimeSeriesPoint(
                timestamp=point.timestamp,
                value=ema
            ))
        
        return smoothed
    
    @staticmethod
    def first_order_difference(
        data: List[TimeSeriesPoint]
    ) -> List[Tuple[datetime, float]]:
        """
        Calculate first-order differences (rate of change).
        
        Useful for detecting acceleration/deceleration in trends.
        
        Args:
            data: List of time series points (must be sorted)
            
        Returns:
            List of (timestamp, difference) tuples
            
        Raises:
            TrendsError: If data is invalid
        """
        TrendAnalyzer._validate_time_series(data, min_points=2)
        
        differences = []
        
        for i in range(1, len(data)):
            diff = data[i].value - data[i-1].value
            differences.append((data[i].timestamp, diff))
        
        return differences
    
    @staticmethod
    def estimate_slope(
        data: List[TimeSeriesPoint],
        normalize_time: bool = True
    ) -> Dict[str, float]:
        """
        Estimate linear trend slope using least squares regression.
        
        Apple principle: This is explainable math, not ML.
        
        Args:
            data: List of time series points (must be sorted)
            normalize_time: If True, normalize time to days since start
            
        Returns:
            Dictionary with slope, intercept, and r_squared
            
        Raises:
            TrendsError: If data is invalid
        """
        TrendAnalyzer._validate_time_series(data, min_points=2)
        
        # Convert timestamps to numeric values (seconds or days since start)
        start_time = data[0].timestamp
        
        if normalize_time:
            # Convert to days
            x = [(p.timestamp - start_time).total_seconds() / 86400 for p in data]
        else:
            # Use seconds
            x = [(p.timestamp - start_time).total_seconds() for p in data]
        
        y = [p.value for p in data]
        
        n = len(x)
        
        # Calculate means
        x_mean = sum(x) / n
        y_mean = sum(y) / n
        
        # Calculate slope and intercept
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            raise TrendsError("Cannot estimate slope: all timestamps are identical")
        
        slope = numerator / denominator
        intercept = y_mean - slope * x_mean
        
        # Calculate R² (coefficient of determination)
        y_pred = [slope * x[i] + intercept for i in range(n)]
        ss_res = sum((y[i] - y_pred[i]) ** 2 for i in range(n))
        ss_tot = sum((y[i] - y_mean) ** 2 for i in range(n))
        
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0
        
        return {
            'slope': slope,
            'intercept': intercept,
            'r_squared': r_squared,
            'trend': 'increasing' if slope > 0 else ('decreasing' if slope < 0 else 'flat'),
            'time_unit': 'days' if normalize_time else 'seconds'
        }
    
    @staticmethod
    def week_over_week_change(
        data: List[TimeSeriesPoint],
        aggregation: str = 'mean'
    ) -> Dict[str, Any]:
        """
        Calculate week-over-week change.
        
        Useful for detecting degradation patterns (e.g., battery health).
        
        Args:
            data: List of time series points (must be sorted)
            aggregation: How to aggregate each week ('mean', 'median', 'sum')
            
        Returns:
            Dictionary with weekly aggregates and change metrics
            
        Raises:
            TrendsError: If data is invalid or insufficient
        """
        TrendAnalyzer._validate_time_series(data, min_points=2)
        
        if aggregation not in ['mean', 'median', 'sum']:
            raise TrendsError(f"Invalid aggregation: {aggregation}")
        
        # Group data by week
        weeks = defaultdict(list)
        
        for point in data:
            # Get week number (ISO week)
            week_key = point.timestamp.strftime('%Y-W%U')
            weeks[week_key].append(point.value)
        
        if len(weeks) < 2:
            raise TrendsError(
                f"Need at least 2 weeks of data, got {len(weeks)} week(s)"
            )
        
        # Calculate aggregate for each week
        sorted_weeks = sorted(weeks.keys())
        weekly_values = []
        
        for week in sorted_weeks:
            values = weeks[week]
            
            if aggregation == 'mean':
                agg_value = sum(values) / len(values)
            elif aggregation == 'median':
                sorted_vals = sorted(values)
                n = len(sorted_vals)
                if n % 2 == 0:
                    agg_value = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
                else:
                    agg_value = sorted_vals[n // 2]
            else:  # sum
                agg_value = sum(values)
            
            weekly_values.append((week, agg_value))
        
        # Calculate week-over-week changes
        changes = []
        for i in range(1, len(weekly_values)):
            prev_week, prev_value = weekly_values[i-1]
            curr_week, curr_value = weekly_values[i]
            
            absolute_change = curr_value - prev_value
            percent_change = (absolute_change / prev_value * 100) if prev_value != 0 else 0.0
            
            changes.append({
                'from_week': prev_week,
                'to_week': curr_week,
                'absolute_change': absolute_change,
                'percent_change': percent_change
            })
        
        # Calculate average change
        avg_absolute_change = sum(c['absolute_change'] for c in changes) / len(changes)
        avg_percent_change = sum(c['percent_change'] for c in changes) / len(changes)
        
        return {
            'num_weeks': len(weekly_values),
            'weekly_values': weekly_values,
            'changes': changes,
            'avg_absolute_change': avg_absolute_change,
            'avg_percent_change': avg_percent_change,
            'aggregation_method': aggregation
        }
    
    @staticmethod
    def rolling_statistics(
        data: List[TimeSeriesPoint],
        window_size: int
    ) -> List[Dict[str, Any]]:
        """
        Calculate rolling statistics (mean, std, min, max) over a window.
        
        Args:
            data: List of time series points (must be sorted)
            window_size: Size of rolling window
            
        Returns:
            List of dictionaries with rolling statistics
            
        Raises:
            TrendsError: If data is invalid
        """
        TrendAnalyzer._validate_time_series(data, min_points=window_size)
        
        if window_size < 1:
            raise TrendsError(f"Window size must be >= 1, got {window_size}")
        
        results = []
        
        for i in range(len(data) - window_size + 1):
            window = data[i:i + window_size]
            values = [p.value for p in window]
            
            mean_val = sum(values) / len(values)
            variance = sum((v - mean_val) ** 2 for v in values) / len(values)
            std_dev = math.sqrt(variance)
            
            results.append({
                'timestamp': window[-1].timestamp,
                'mean': mean_val,
                'std_dev': std_dev,
                'min': min(values),
                'max': max(values),
                'range': max(values) - min(values)
            })
        
        return results
    
    @staticmethod
    def detect_trend_reversal(
        data: List[TimeSeriesPoint],
        window_size: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Detect points where trend reverses (increasing → decreasing or vice versa).
        
        Uses slope changes in rolling windows.
        
        Args:
            data: List of time series points (must be sorted)
            window_size: Window size for slope estimation
            
        Returns:
            List of detected reversals with context
            
        Raises:
            TrendsError: If data is invalid
        """
        if window_size < 3:
            raise TrendsError("Window size must be >= 3 for reversal detection")
        
        TrendAnalyzer._validate_time_series(data, min_points=window_size * 2)
        
        reversals = []
        prev_slope = None
        
        # Calculate slopes in rolling windows
        for i in range(len(data) - window_size + 1):
            window = data[i:i + window_size]
            
            try:
                slope_info = TrendAnalyzer.estimate_slope(window, normalize_time=True)
                curr_slope = slope_info['slope']
                
                # Detect reversal (sign change in slope)
                if prev_slope is not None:
                    if (prev_slope > 0 and curr_slope < 0) or (prev_slope < 0 and curr_slope > 0):
                        reversals.append({
                            'timestamp': window[-1].timestamp,
                            'from_trend': 'increasing' if prev_slope > 0 else 'decreasing',
                            'to_trend': 'increasing' if curr_slope > 0 else 'decreasing',
                            'prev_slope': prev_slope,
                            'curr_slope': curr_slope,
                            'value': window[-1].value
                        })
                
                prev_slope = curr_slope
            
            except TrendsError:
                # Skip windows where slope can't be calculated
                continue
        
        return reversals
