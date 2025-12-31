"""
Device Health Summaries

Convert metrics and anomalies into actionable insights.

Apple principle: Engineers need decisions, not just numbers.

This module produces human-readable summaries with:
- Device status (HEALTHY, DEGRADED, CRITICAL)
- Clear reasons for status
- Confidence scores
- Actionable recommendations

Author: Software Engineering Intern  
Purpose: Transform data into decisions
"""

import logging
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime, timedelta

from .metrics import TelemetryMetrics, MetricsError
from .anomalies import AnomalyDetector, Anomaly, AnomalySeverity
from .trends import TrendAnalyzer, TimeSeriesPoint

logger = logging.getLogger(__name__)


class DeviceStatus(Enum):
    """Overall device health status"""
    HEALTHY = "healthy"
    FAIR = "fair"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class DeviceHealthSummary:
    """
    Comprehensive device health summary.
    
    This is what gets presented to engineers for decision-making.
    """
    
    def __init__(
        self,
        device_id: str,
        status: DeviceStatus,
        confidence: float,
        reasons: List[str],
        metrics: Dict[str, Any],
        anomalies: List[Anomaly],
        recommendations: List[str],
        timestamp: datetime
    ):
        self.device_id = device_id
        self.status = status
        self.confidence = confidence
        self.reasons = reasons
        self.metrics = metrics
        self.anomalies = anomalies
        self.recommendations = recommendations
        self.timestamp = timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'device_id': self.device_id,
            'status': self.status.value,
            'confidence': self.confidence,
            'reasons': self.reasons,
            'metrics': self.metrics,
            'anomalies': [a.to_dict() for a in self.anomalies],
            'recommendations': self.recommendations,
            'timestamp': self.timestamp.isoformat()
        }
    
    def __repr__(self):
        return (
            f"DeviceHealthSummary(device={self.device_id}, "
            f"status={self.status.value.upper()}, "
            f"confidence={self.confidence:.2f}, "
            f"reasons={len(self.reasons)})"
        )


class SummaryGenerator:
    """
    Generate actionable device health summaries.
    
    Combines metrics, trends, and anomalies into decision support.
    """
    
    # Thresholds for battery health assessment
    BATTERY_HEALTH_THRESHOLDS = {
        'critical': 0.70,
        'degraded': 0.80,
        'fair': 0.90,
        'healthy': 0.95
    }
    
    # Thresholds for CPU usage assessment
    CPU_USAGE_THRESHOLDS = {
        'critical': 90.0,
        'warning': 75.0,
        'normal': 50.0
    }
    
    # Thresholds for memory usage assessment
    MEMORY_USAGE_THRESHOLDS = {
        'critical': 90.0,
        'warning': 80.0,
        'normal': 60.0
    }
    
    @staticmethod
    def _assess_battery_health(
        battery_health: float,
        trend_slope: Optional[float] = None
    ) -> tuple[str, float]:
        """
        Assess battery health status.
        
        Args:
            battery_health: Current battery health (0.0-1.0)
            trend_slope: Optional trend slope (degradation rate per day)
            
        Returns:
            Tuple of (status_message, concern_score)
        """
        if battery_health >= SummaryGenerator.BATTERY_HEALTH_THRESHOLDS['healthy']:
            status = "Battery health is excellent"
            concern = 0.0
        elif battery_health >= SummaryGenerator.BATTERY_HEALTH_THRESHOLDS['fair']:
            status = "Battery health is good"
            concern = 0.2
        elif battery_health >= SummaryGenerator.BATTERY_HEALTH_THRESHOLDS['degraded']:
            status = "Battery health is fair but showing wear"
            concern = 0.5
        elif battery_health >= SummaryGenerator.BATTERY_HEALTH_THRESHOLDS['critical']:
            status = "Battery health is degraded"
            concern = 0.7
        else:
            status = "Battery health is critically low"
            concern = 0.95
        
        # Factor in trend if available
        if trend_slope is not None and trend_slope < 0:
            # Battery is degrading
            degradation_rate = abs(trend_slope)
            
            # Convert to percent per month for interpretability
            percent_per_month = degradation_rate * 30 * 100
            
            if percent_per_month > 2.0:  # > 2% per month
                status += f" and degrading rapidly ({percent_per_month:.1f}% per month)"
                concern = min(1.0, concern + 0.3)
            elif percent_per_month > 0.5:  # > 0.5% per month
                status += f" and degrading faster than expected ({percent_per_month:.1f}% per month)"
                concern = min(1.0, concern + 0.15)
        
        return status, concern
    
    @staticmethod
    def _assess_cpu_usage(
        cpu_metrics: Dict[str, float]
    ) -> tuple[str, float]:
        """
        Assess CPU usage patterns.
        
        Args:
            cpu_metrics: Dictionary with mean, p90, p99, etc.
            
        Returns:
            Tuple of (status_message, concern_score)
        """
        p90 = cpu_metrics.get('p90', cpu_metrics.get('mean', 0.0))
        mean = cpu_metrics.get('mean', 0.0)
        
        # P90 is more important than mean (tail behavior matters)
        if p90 >= SummaryGenerator.CPU_USAGE_THRESHOLDS['critical']:
            status = f"CPU usage is critically high (P90: {p90:.1f}%)"
            concern = 0.9
        elif p90 >= SummaryGenerator.CPU_USAGE_THRESHOLDS['warning']:
            status = f"CPU usage is elevated (P90: {p90:.1f}%)"
            concern = 0.6
        elif mean >= SummaryGenerator.CPU_USAGE_THRESHOLDS['normal']:
            status = f"CPU usage is moderate (mean: {mean:.1f}%)"
            concern = 0.3
        else:
            status = f"CPU usage is normal (mean: {mean:.1f}%)"
            concern = 0.0
        
        return status, concern
    
    @staticmethod
    def _assess_memory_usage(
        memory_metrics: Dict[str, float]
    ) -> tuple[str, float]:
        """
        Assess memory usage patterns.
        
        Args:
            memory_metrics: Dictionary with mean, p90, p99, etc.
            
        Returns:
            Tuple of (status_message, concern_score)
        """
        p90 = memory_metrics.get('p90', memory_metrics.get('mean', 0.0))
        mean = memory_metrics.get('mean', 0.0)
        
        if p90 >= SummaryGenerator.MEMORY_USAGE_THRESHOLDS['critical']:
            status = f"Memory usage is critically high (P90: {p90:.1f}%)"
            concern = 0.85
        elif p90 >= SummaryGenerator.MEMORY_USAGE_THRESHOLDS['warning']:
            status = f"Memory usage is elevated (P90: {p90:.1f}%)"
            concern = 0.5
        else:
            status = f"Memory usage is normal (mean: {mean:.1f}%)"
            concern = 0.0
        
        return status, concern
    
    @staticmethod
    def _assess_thermal_state(
        thermal_states: List[str]
    ) -> tuple[str, float]:
        """
        Assess thermal state distribution.
        
        Args:
            thermal_states: List of thermal state values
            
        Returns:
            Tuple of (status_message, concern_score)
        """
        if not thermal_states:
            return "No thermal data available", 0.0
        
        total = len(thermal_states)
        critical_count = sum(1 for s in thermal_states if s == 'critical')
        serious_count = sum(1 for s in thermal_states if s == 'serious')
        
        critical_pct = critical_count / total * 100
        serious_pct = serious_count / total * 100
        
        if critical_pct > 5.0:
            status = f"Frequent critical thermal events ({critical_pct:.1f}% of samples)"
            concern = 0.95
        elif serious_pct > 15.0:
            status = f"Elevated thermal events ({serious_pct:.1f}% serious or critical)"
            concern = 0.7
        elif serious_pct > 5.0:
            status = f"Occasional thermal events ({serious_pct:.1f}% serious)"
            concern = 0.4
        else:
            status = "Thermal state is normal"
            concern = 0.0
        
        return status, concern
    
    @staticmethod
    def generate_device_summary(
        device_id: str,
        telemetry_records: List[Dict[str, Any]],
        time_window_days: int = 7
    ) -> DeviceHealthSummary:
        """
        Generate comprehensive device health summary.
        
        This is the main entry point for Phase 2 summaries.
        
        Args:
            device_id: Device identifier
            telemetry_records: List of telemetry dictionaries
            time_window_days: Number of days to analyze
            
        Returns:
            DeviceHealthSummary with status and recommendations
        """
        if not telemetry_records:
            return DeviceHealthSummary(
                device_id=device_id,
                status=DeviceStatus.UNKNOWN,
                confidence=0.0,
                reasons=["No telemetry data available"],
                metrics={},
                anomalies=[],
                recommendations=["Ensure device is reporting telemetry"],
                timestamp=datetime.now()
            )
        
        reasons = []
        concern_scores = []
        recommendations = []
        all_anomalies = []
        metrics_summary = {}
        
        # === BATTERY HEALTH ANALYSIS ===
        try:
            battery_values = [r['battery_health'] for r in telemetry_records]
            battery_metrics = TelemetryMetrics.calculate_telemetry_summary(
                telemetry_records, 'battery_health'
            )
            metrics_summary['battery_health'] = battery_metrics
            
            # Analyze trend
            battery_ts = [
                TimeSeriesPoint(r['timestamp'], r['battery_health'])
                for r in telemetry_records
            ]
            trend_info = TrendAnalyzer.estimate_slope(battery_ts, normalize_time=True)
            
            status_msg, concern = SummaryGenerator._assess_battery_health(
                battery_metrics['median'],
                trend_info['slope']
            )
            reasons.append(status_msg)
            concern_scores.append(concern)
            
            if concern > 0.5:
                recommendations.append("Consider battery replacement or service")
            
            # Detect battery anomalies
            battery_anomalies = AnomalyDetector.detect_anomalies_comprehensive(
                telemetry_records,
                'battery_health',
                absolute_thresholds={'lower': 0.6, 'upper': 1.0}
            )
            all_anomalies.extend(battery_anomalies)
        
        except Exception as e:
            logger.warning(f"Battery health analysis failed: {e}")
        
        # === CPU USAGE ANALYSIS ===
        try:
            cpu_metrics = TelemetryMetrics.calculate_telemetry_summary(
                telemetry_records, 'cpu_usage'
            )
            metrics_summary['cpu_usage'] = cpu_metrics
            
            status_msg, concern = SummaryGenerator._assess_cpu_usage(cpu_metrics)
            reasons.append(status_msg)
            concern_scores.append(concern)
            
            if concern > 0.7:
                recommendations.append("Investigate high CPU usage applications")
            
            # Detect CPU anomalies
            cpu_anomalies = AnomalyDetector.detect_anomalies_comprehensive(
                telemetry_records,
                'cpu_usage',
                z_score_threshold=2.5
            )
            all_anomalies.extend(cpu_anomalies)
        
        except Exception as e:
            logger.warning(f"CPU usage analysis failed: {e}")
        
        # === MEMORY USAGE ANALYSIS ===
        try:
            memory_metrics = TelemetryMetrics.calculate_telemetry_summary(
                telemetry_records, 'memory_usage'
            )
            metrics_summary['memory_usage'] = memory_metrics
            
            status_msg, concern = SummaryGenerator._assess_memory_usage(memory_metrics)
            reasons.append(status_msg)
            concern_scores.append(concern)
            
            if concern > 0.6:
                recommendations.append("Monitor memory-intensive applications")
        
        except Exception as e:
            logger.warning(f"Memory usage analysis failed: {e}")
        
        # === THERMAL STATE ANALYSIS ===
        try:
            thermal_states = [r['thermal_state'].value for r in telemetry_records]
            status_msg, concern = SummaryGenerator._assess_thermal_state(thermal_states)
            reasons.append(status_msg)
            concern_scores.append(concern)
            
            if concern > 0.7:
                recommendations.append("Check device ventilation and ambient temperature")
        
        except Exception as e:
            logger.warning(f"Thermal state analysis failed: {e}")
        
        # === DETERMINE OVERALL STATUS ===
        if not concern_scores:
            overall_status = DeviceStatus.UNKNOWN
            confidence = 0.0
        else:
            max_concern = max(concern_scores)
            avg_concern = sum(concern_scores) / len(concern_scores)
            
            # Status based on maximum concern (worst signal)
            if max_concern >= 0.9:
                overall_status = DeviceStatus.CRITICAL
            elif max_concern >= 0.6:
                overall_status = DeviceStatus.DEGRADED
            elif max_concern >= 0.3:
                overall_status = DeviceStatus.FAIR
            else:
                overall_status = DeviceStatus.HEALTHY
            
            # Confidence based on data quantity and consistency
            data_quantity_score = min(1.0, len(telemetry_records) / 100)
            confidence = data_quantity_score * 0.7 + 0.3  # Base 30% + up to 70% from data
        
        # Add general recommendations
        if overall_status == DeviceStatus.HEALTHY and not recommendations:
            recommendations.append("Device is operating normally")
        
        return DeviceHealthSummary(
            device_id=device_id,
            status=overall_status,
            confidence=confidence,
            reasons=reasons,
            metrics=metrics_summary,
            anomalies=all_anomalies,
            recommendations=recommendations,
            timestamp=datetime.now()
        )
    
    @staticmethod
    def generate_fleet_summary(
        device_summaries: List[DeviceHealthSummary]
    ) -> Dict[str, Any]:
        """
        Generate fleet-wide summary from individual device summaries.
        
        Useful for understanding overall device population health.
        
        Args:
            device_summaries: List of individual device summaries
            
        Returns:
            Dictionary with fleet-wide statistics
        """
        if not device_summaries:
            return {
                'total_devices': 0,
                'status_distribution': {},
                'critical_devices': [],
                'recommendations': ['No device data available']
            }
        
        status_counts = {status.value: 0 for status in DeviceStatus}
        critical_devices = []
        degraded_devices = []
        
        for summary in device_summaries:
            status_counts[summary.status.value] += 1
            
            if summary.status == DeviceStatus.CRITICAL:
                critical_devices.append({
                    'device_id': summary.device_id,
                    'reasons': summary.reasons,
                    'confidence': summary.confidence
                })
            elif summary.status == DeviceStatus.DEGRADED:
                degraded_devices.append({
                    'device_id': summary.device_id,
                    'reasons': summary.reasons
                })
        
        total = len(device_summaries)
        
        return {
            'total_devices': total,
            'status_distribution': {
                status: {'count': count, 'percentage': count / total * 100}
                for status, count in status_counts.items()
            },
            'critical_devices': critical_devices,
            'degraded_devices': degraded_devices,
            'health_rate': status_counts['healthy'] / total * 100,
            'timestamp': datetime.now().isoformat()
        }
