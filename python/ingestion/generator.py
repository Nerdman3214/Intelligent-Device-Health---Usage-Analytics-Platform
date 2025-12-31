"""
Telemetry Data Generator

Generates realistic device telemetry data with controlled noise and intentional bad data.

Apple engineering principle: If your pipeline can't reject bad data, it's broken.
This generator creates BOTH good and bad data to test validation rigorously.

Author: Software Engineering Intern
Purpose: Simulate realistic iPhone/Mac telemetry for testing
"""

import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from .schemas import ThermalState, DeviceType


class TelemetryGenerator:
    """
    Generates realistic device telemetry with configurable quality levels.
    
    Modes:
    - CLEAN: Perfect data (for happy path testing)
    - NOISY: Realistic with some variance (normal operation)
    - CORRUPTED: Intentionally bad data (for validation testing)
    """
    
    # Realistic app names for Apple devices
    COMMON_APPS = [
        'Safari', 'Messages', 'Mail', 'Photos', 'Music',
        'Maps', 'Calendar', 'Notes', 'Reminders', 'FaceTime',
        'Settings', 'App Store', 'Podcasts', 'News', 'Weather'
    ]
    
    # Realistic OS versions
    OS_VERSIONS = [
        'iOS 17.2', 'iOS 17.1', 'iOS 17.0',
        'macOS 14.2', 'macOS 14.1', 'macOS 14.0'
    ]
    
    @staticmethod
    def generate_device_id() -> str:
        """Generate a valid UUID v4 device ID"""
        return str(uuid.uuid4())
    
    @staticmethod
    def generate_clean_telemetry(
        device_id: str | None = None,
        device_type: DeviceType = DeviceType.IPHONE
    ) -> Dict[str, Any]:
        """
        Generate clean, valid telemetry data.
        
        Args:
            device_id: Optional specific device ID, generates new UUID if None
            device_type: Type of device to simulate
            
        Returns:
            Dictionary of valid telemetry data
        """
        if device_id is None:
            device_id = TelemetryGenerator.generate_device_id()
        
        # Normal operating conditions with realistic variance
        cpu_usage = random.gauss(35.0, 12.0)  # Mean 35%, std 12%
        cpu_usage = max(0.0, min(100.0, cpu_usage))  # Clamp to valid range
        
        memory_usage = random.gauss(45.0, 15.0)
        memory_usage = max(0.0, min(100.0, memory_usage))
        
        # Battery health: typically high with slow degradation
        battery_health = random.gauss(0.95, 0.03)
        battery_health = max(0.0, min(1.0, battery_health))
        
        battery_level = random.uniform(20.0, 95.0)
        
        # Thermal state: mostly nominal
        thermal_weights = [0.85, 0.10, 0.04, 0.01]  # Nominal, Fair, Serious, Critical
        thermal_state = random.choices(
            list(ThermalState),
            weights=thermal_weights,
            k=1
        )[0]
        
        # Generate realistic app usage (total should be reasonable)
        num_apps = random.randint(3, 8)
        selected_apps = random.sample(TelemetryGenerator.COMMON_APPS, num_apps)
        
        # Distribute ~8 hours of usage across apps
        total_seconds = random.uniform(6 * 3600, 10 * 3600)  # 6-10 hours
        app_foreground_time = {}
        
        remaining = total_seconds
        for i, app in enumerate(selected_apps[:-1]):
            time_fraction = random.uniform(0.05, 0.30)
            app_time = remaining * time_fraction
            app_foreground_time[app] = round(app_time, 2)
            remaining -= app_time
        
        # Last app gets remaining time
        app_foreground_time[selected_apps[-1]] = round(remaining, 2)
        
        # Network usage: realistic daily amounts (in bytes)
        network_sent = random.randint(10_000_000, 500_000_000)  # 10 MB - 500 MB
        network_received = random.randint(50_000_000, 2_000_000_000)  # 50 MB - 2 GB
        
        return {
            'device_id': device_id,
            'timestamp': datetime.now(timezone.utc),
            'cpu_usage': round(cpu_usage, 2),
            'memory_usage': round(memory_usage, 2),
            'battery_health': round(battery_health, 4),
            'battery_level': round(battery_level, 2),
            'thermal_state': thermal_state,
            'device_type': device_type,
            'app_foreground_time': app_foreground_time,
            'network_bytes_sent': network_sent,
            'network_bytes_received': network_received,
            'os_version': random.choice(TelemetryGenerator.OS_VERSIONS),
            'location_enabled': random.choice([True, False])
        }
    
    @staticmethod
    def generate_noisy_telemetry(
        device_id: str | None = None,
        device_type: DeviceType = DeviceType.IPHONE
    ) -> Dict[str, Any]:
        """
        Generate realistic but noisier telemetry (edge of normal operation).
        
        Args:
            device_id: Optional specific device ID
            device_type: Type of device to simulate
            
        Returns:
            Dictionary of telemetry data with higher variance
        """
        data = TelemetryGenerator.generate_clean_telemetry(device_id, device_type)
        
        # Add noise: occasional high CPU/memory
        if random.random() < 0.15:  # 15% chance of high CPU
            data['cpu_usage'] = random.uniform(75.0, 98.0)
        
        if random.random() < 0.12:  # 12% chance of high memory
            data['memory_usage'] = random.uniform(80.0, 95.0)
        
        # Occasional thermal events
        if random.random() < 0.08:
            data['thermal_state'] = random.choice([ThermalState.SERIOUS, ThermalState.CRITICAL])
        
        # Battery degradation scenarios
        if random.random() < 0.10:
            data['battery_health'] = random.uniform(0.70, 0.85)
        
        return data
    
    @staticmethod
    def generate_corrupted_telemetry(corruption_type: str = 'random') -> Dict[str, Any]:
        """
        Generate intentionally corrupted data for validation testing.
        
        Apple principle: Your validation MUST catch bad data.
        
        Corruption types:
        - 'missing_fields': Remove required fields
        - 'wrong_types': Use wrong data types
        - 'out_of_range': Values outside valid ranges
        - 'invalid_format': Malformed UUIDs, timestamps
        - 'future_timestamp': Timestamp in the future
        - 'random': Random corruption
        
        Args:
            corruption_type: Type of corruption to introduce
            
        Returns:
            Dictionary of corrupted telemetry data
        """
        data = TelemetryGenerator.generate_clean_telemetry()
        
        if corruption_type == 'random':
            corruption_type = random.choice([
                'missing_fields', 'wrong_types', 'out_of_range',
                'invalid_format', 'future_timestamp'
            ])
        
        if corruption_type == 'missing_fields':
            # Remove random required field
            required_fields = ['device_id', 'timestamp', 'cpu_usage', 'battery_health']
            field_to_remove = random.choice(required_fields)
            del data[field_to_remove]
        
        elif corruption_type == 'wrong_types':
            # Use wrong types
            corruptions = [
                ('cpu_usage', '75.5'),  # String instead of float
                ('battery_health', 'good'),  # String instead of float
                ('network_bytes_sent', 100.5),  # Float instead of int
                ('app_foreground_time', 'invalid'),  # String instead of dict
            ]
            field, bad_value = random.choice(corruptions)
            data[field] = bad_value
        
        elif corruption_type == 'out_of_range':
            # Values outside valid ranges
            corruptions = [
                ('cpu_usage', random.choice([-5.0, 150.0])),
                ('battery_health', random.choice([-0.1, 1.5])),
                ('memory_usage', random.choice([-10.0, 200.0])),
                ('network_bytes_sent', -1000),
            ]
            field, bad_value = random.choice(corruptions)
            data[field] = bad_value
        
        elif corruption_type == 'invalid_format':
            # Malformed data
            corruptions = [
                ('device_id', 'not-a-uuid'),
                ('device_id', ''),
                ('device_id', '12345'),
                ('thermal_state', 'EXPLODING'),  # Invalid enum
            ]
            field, bad_value = random.choice(corruptions)
            data[field] = bad_value
        
        elif corruption_type == 'future_timestamp':
            # Timestamp way in the future (beyond clock skew tolerance)
            data['timestamp'] = datetime.now(timezone.utc) + timedelta(hours=2)
        
        return data
    
    @staticmethod
    def generate_batch(
        count: int,
        device_id: str | None = None,
        quality: str = 'clean',
        corruption_rate: float = 0.0
    ) -> list[Dict[str, Any]]:
        """
        Generate a batch of telemetry records.
        
        Args:
            count: Number of records to generate
            device_id: Optional specific device ID (generates unique IDs if None)
            quality: 'clean', 'noisy', or 'corrupted'
            corruption_rate: For 'clean'/'noisy', chance of corruption (0.0-1.0)
            
        Returns:
            List of telemetry dictionaries
        """
        batch = []
        
        for _ in range(count):
            # Decide if this record should be corrupted
            if corruption_rate > 0 and random.random() < corruption_rate:
                record = TelemetryGenerator.generate_corrupted_telemetry()
            else:
                if quality == 'clean':
                    record = TelemetryGenerator.generate_clean_telemetry(device_id)
                elif quality == 'noisy':
                    record = TelemetryGenerator.generate_noisy_telemetry(device_id)
                else:  # corrupted
                    record = TelemetryGenerator.generate_corrupted_telemetry()
            
            batch.append(record)
        
        return batch
    
    @staticmethod
    def generate_time_series(
        device_id: str,
        duration_days: int,
        samples_per_day: int = 24,
        simulate_degradation: bool = True
    ) -> list[Dict[str, Any]]:
        """
        Generate time-series telemetry data for trend analysis.
        
        Useful for Phase 2 analytics testing.
        
        Args:
            device_id: Device ID to use
            duration_days: Number of days to simulate
            samples_per_day: Number of samples per day
            simulate_degradation: If True, simulate battery health degradation
            
        Returns:
            List of telemetry records ordered by timestamp
        """
        records = []
        start_time = datetime.now(timezone.utc) - timedelta(days=duration_days)
        
        battery_health = 1.0  # Start with perfect health
        decay_rate = 0.0001 if simulate_degradation else 0.0
        
        for day in range(duration_days):
            for sample in range(samples_per_day):
                timestamp = start_time + timedelta(
                    days=day,
                    hours=(24 / samples_per_day) * sample
                )
                
                record = TelemetryGenerator.generate_clean_telemetry(device_id)
                record['timestamp'] = timestamp
                
                # Apply battery degradation
                if simulate_degradation:
                    battery_health -= decay_rate
                    battery_health = max(0.7, battery_health)  # Floor at 70%
                    record['battery_health'] = round(battery_health, 4)
                
                records.append(record)
        
        return records
