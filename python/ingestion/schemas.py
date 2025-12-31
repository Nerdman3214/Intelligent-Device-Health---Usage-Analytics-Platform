"""
Data Schemas for Device Telemetry

Apple-style defensive data contracts with explicit validation rules.
NO silent failures. NO magic coercion. Clear error messages.

Author: Software Engineering Intern
Purpose: Define what "valid data" means for device telemetry
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import datetime


class ThermalState(Enum):
    """
    Device thermal states matching Apple's thermal management system.
    
    NOMINAL: Normal operating temperature
    FAIR: Slightly elevated, no throttling
    SERIOUS: Elevated, may throttle
    CRITICAL: Dangerous, aggressive throttling
    """
    NOMINAL = "nominal"
    FAIR = "fair"
    SERIOUS = "serious"
    CRITICAL = "critical"


class DeviceType(Enum):
    """Supported device types"""
    IPHONE = "iphone"
    IPAD = "ipad"
    MACBOOK = "macbook"
    IMAC = "imac"
    WATCH = "watch"


@dataclass
class TelemetrySchema:
    """
    Core schema for device telemetry data.
    
    All fields are required unless explicitly marked Optional.
    This is Apple's philosophy: explicit is better than implicit.
    
    Validation Rules (ENFORCED, not suggested):
    - device_id: Must be non-empty string matching UUID format
    - timestamp: Must be valid ISO 8601 datetime, not in future
    - cpu_usage: Float in range [0.0, 100.0]
    - memory_usage: Float in range [0.0, 100.0]
    - battery_health: Float in range [0.0, 1.0] (1.0 = perfect health)
    - battery_level: Float in range [0.0, 100.0]
    - thermal_state: Must be valid ThermalState enum
    - device_type: Must be valid DeviceType enum
    - app_foreground_time: Dict[str, float] where values >= 0
    - network_bytes_sent: Integer >= 0
    - network_bytes_received: Integer >= 0
    """
    
    device_id: str
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    battery_health: float
    battery_level: float
    thermal_state: ThermalState
    device_type: DeviceType
    app_foreground_time: dict[str, float]  # app_name -> seconds
    network_bytes_sent: int
    network_bytes_received: int
    
    # Optional contextual fields
    os_version: Optional[str] = None
    location_enabled: Optional[bool] = None
    
    def to_dict(self) -> dict:
        """
        Convert schema to dictionary for serialization.
        
        Returns:
            Dictionary representation with enums converted to strings
        """
        return {
            'device_id': self.device_id,
            'timestamp': self.timestamp.isoformat(),
            'cpu_usage': self.cpu_usage,
            'memory_usage': self.memory_usage,
            'battery_health': self.battery_health,
            'battery_level': self.battery_level,
            'thermal_state': self.thermal_state.value,
            'device_type': self.device_type.value,
            'app_foreground_time': self.app_foreground_time,
            'network_bytes_sent': self.network_bytes_sent,
            'network_bytes_received': self.network_bytes_received,
            'os_version': self.os_version,
            'location_enabled': self.location_enabled
        }


# Schema validation constraints (for validator.py to enforce)
SCHEMA_CONSTRAINTS = {
    'cpu_usage': {'min': 0.0, 'max': 100.0, 'type': float},
    'memory_usage': {'min': 0.0, 'max': 100.0, 'type': float},
    'battery_health': {'min': 0.0, 'max': 1.0, 'type': float},
    'battery_level': {'min': 0.0, 'max': 100.0, 'type': float},
    'network_bytes_sent': {'min': 0, 'type': int},
    'network_bytes_received': {'min': 0, 'type': int},
}


# Baseline expectations (for anomaly detection in Phase 2)
BASELINE_EXPECTATIONS = {
    'cpu_usage_normal_mean': 35.0,
    'cpu_usage_normal_std': 15.0,
    'memory_usage_normal_mean': 45.0,
    'memory_usage_normal_std': 20.0,
    'battery_health_decay_rate_per_day': 0.0001,  # ~3.6% per year
    'thermal_nominal_probability': 0.85,  # 85% should be nominal
}
