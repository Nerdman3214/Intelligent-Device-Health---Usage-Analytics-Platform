"""
Risk Labeling for Device Health Prediction

Apple principle: Labels must be defensible with clear thresholds.

This module creates training labels from telemetry using rule-based heuristics.
NO manual labeling required — rules are transparent and auditable.

Author: Software Engineering Intern
Purpose: Generate risk labels (HEALTHY, AT_RISK, DEGRADED) for supervised learning
"""

import logging
from typing import List, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class DeviceRisk(Enum):
    """Device health risk levels for prediction"""
    HEALTHY = 0
    AT_RISK = 1
    DEGRADED = 2


class RiskLabel:
    """
    Risk label with justification.
    
    Apple principle: Every label should be explainable.
    """
    
    def __init__(
        self,
        device_id: str,
        risk_level: DeviceRisk,
        confidence: float,
        reasons: List[str]
    ):
        self.device_id = device_id
        self.risk_level = risk_level
        self.confidence = confidence
        self.reasons = reasons
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'device_id': self.device_id,
            'risk_level': self.risk_level.value,
            'risk_name': self.risk_level.name,
            'confidence': self.confidence,
            'reasons': self.reasons
        }


class RiskLabeler:
    """
    Generate risk labels from telemetry using transparent rules.
    
    Rules are based on Apple's actual device health criteria:
    - Battery health degradation
    - Thermal management issues
    - Resource utilization patterns
    """
    
    # Risk thresholds (tuned for realistic device behavior)
    THRESHOLDS = {
        # Battery
        'battery_health_critical': 0.75,
        'battery_health_degraded': 0.85,
        'battery_degradation_rate_warning': -0.0005,  # per day
        
        # CPU
        'cpu_p90_critical': 90.0,
        'cpu_p90_warning': 75.0,
        'cpu_spike_ratio_warning': 0.15,  # 15% of samples > 90%
        
        # Memory
        'memory_p90_critical': 90.0,
        'memory_p90_warning': 80.0,
        
        # Thermal
        'thermal_critical_ratio_warning': 0.05,  # 5% critical
        'thermal_serious_ratio_warning': 0.15,  # 15% serious or worse
    }
    
    @staticmethod
    def label_from_features(
        device_id: str,
        features: Dict[str, float]
    ) -> RiskLabel:
        """
        Generate risk label from extracted features.
        
        Uses transparent heuristics — no ML required for labeling.
        
        Args:
            device_id: Device identifier
            features: Dictionary of extracted features
            
        Returns:
            RiskLabel with risk level and reasons
        """
        risk_signals = []
        degraded_signals = []
        
        # === BATTERY HEALTH CHECKS ===
        battery_health = features.get('battery_health_mean', 1.0)
        battery_slope = features.get('battery_health_trend_slope', 0.0)
        
        if battery_health < RiskLabeler.THRESHOLDS['battery_health_critical']:
            degraded_signals.append(
                f"Battery health critically low ({battery_health:.2f})"
            )
        elif battery_health < RiskLabeler.THRESHOLDS['battery_health_degraded']:
            risk_signals.append(
                f"Battery health degraded ({battery_health:.2f})"
            )
        
        if battery_slope < RiskLabeler.THRESHOLDS['battery_degradation_rate_warning']:
            degradation_rate_pct = abs(battery_slope) * 30 * 100  # % per month
            if degradation_rate_pct > 2.0:
                degraded_signals.append(
                    f"Rapid battery degradation ({degradation_rate_pct:.1f}% per month)"
                )
            else:
                risk_signals.append(
                    f"Elevated battery degradation ({degradation_rate_pct:.1f}% per month)"
                )
        
        # === CPU USAGE CHECKS ===
        cpu_p90 = features.get('cpu_usage_p90', 0.0)
        cpu_spikes = features.get('cpu_usage_spike_count', 0.0)
        
        if cpu_p90 > RiskLabeler.THRESHOLDS['cpu_p90_critical']:
            degraded_signals.append(
                f"Excessive CPU usage (P90: {cpu_p90:.1f}%)"
            )
        elif cpu_p90 > RiskLabeler.THRESHOLDS['cpu_p90_warning']:
            risk_signals.append(
                f"Elevated CPU usage (P90: {cpu_p90:.1f}%)"
            )
        
        if cpu_spikes > RiskLabeler.THRESHOLDS['cpu_spike_ratio_warning']:
            risk_signals.append(
                f"Frequent CPU spikes ({cpu_spikes*100:.1f}% of samples > 90%)"
            )
        
        # === MEMORY USAGE CHECKS ===
        memory_p90 = features.get('memory_usage_p90', 0.0)
        
        if memory_p90 > RiskLabeler.THRESHOLDS['memory_p90_critical']:
            degraded_signals.append(
                f"Critical memory usage (P90: {memory_p90:.1f}%)"
            )
        elif memory_p90 > RiskLabeler.THRESHOLDS['memory_p90_warning']:
            risk_signals.append(
                f"High memory usage (P90: {memory_p90:.1f}%)"
            )
        
        # === THERMAL CHECKS ===
        thermal_critical = features.get('thermal_critical_ratio', 0.0)
        thermal_serious = features.get('thermal_serious_or_worse_ratio', 0.0)
        
        if thermal_critical > RiskLabeler.THRESHOLDS['thermal_critical_ratio_warning']:
            degraded_signals.append(
                f"Frequent critical thermal events ({thermal_critical*100:.1f}%)"
            )
        elif thermal_serious > RiskLabeler.THRESHOLDS['thermal_serious_ratio_warning']:
            risk_signals.append(
                f"Elevated thermal events ({thermal_serious*100:.1f}%)"
            )
        
        # === DETERMINE OVERALL RISK ===
        if len(degraded_signals) >= 2:
            # Multiple degraded signals = DEGRADED
            risk_level = DeviceRisk.DEGRADED
            confidence = min(1.0, 0.7 + len(degraded_signals) * 0.1)
            reasons = degraded_signals + risk_signals
        elif len(degraded_signals) >= 1:
            # One critical signal = AT_RISK
            risk_level = DeviceRisk.AT_RISK
            confidence = 0.8
            reasons = degraded_signals + risk_signals
        elif len(risk_signals) >= 2:
            # Multiple warning signals = AT_RISK
            risk_level = DeviceRisk.AT_RISK
            confidence = 0.7
            reasons = risk_signals
        elif len(risk_signals) >= 1:
            # Single warning = still AT_RISK but lower confidence
            risk_level = DeviceRisk.AT_RISK
            confidence = 0.6
            reasons = risk_signals
        else:
            # No signals = HEALTHY
            risk_level = DeviceRisk.HEALTHY
            confidence = 0.9
            reasons = ["All metrics within normal ranges"]
        
        return RiskLabel(
            device_id=device_id,
            risk_level=risk_level,
            confidence=confidence,
            reasons=reasons
        )
    
    @staticmethod
    def create_training_labels(
        features_list: List[Dict[str, Any]]
    ) -> List[RiskLabel]:
        """
        Generate training labels for a batch of devices.
        
        Args:
            features_list: List of feature dictionaries
            
        Returns:
            List of RiskLabels
        """
        labels = []
        
        for feature_dict in features_list:
            device_id = feature_dict.get('device_id', 'UNKNOWN')
            features = feature_dict.get('features', feature_dict)
            
            label = RiskLabeler.label_from_features(device_id, features)
            labels.append(label)
        
        return labels
    
    @staticmethod
    def get_label_distribution(labels: List[RiskLabel]) -> Dict[str, Any]:
        """
        Get distribution of risk labels (for training balance analysis).
        
        Args:
            labels: List of RiskLabels
            
        Returns:
            Dictionary with label counts and percentages
        """
        total = len(labels)
        if total == 0:
            return {}
        
        counts = {level.name: 0 for level in DeviceRisk}
        
        for label in labels:
            counts[label.risk_level.name] += 1
        
        return {
            'total': total,
            'counts': counts,
            'percentages': {
                name: (count / total * 100) for name, count in counts.items()
            },
            'is_balanced': all(
                20 <= (count / total * 100) <= 80
                for count in counts.values() if count > 0
            )
        }
