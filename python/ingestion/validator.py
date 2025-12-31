"""
Defensive Validation Layer

Apple philosophy: NEVER hide errors. ALWAYS validate inputs. Fail loudly but safely.

This module validates telemetry data with explicit error messages.
NO silent coercion. NO magic behavior. NO generic exceptions.

Author: Software Engineering Intern
Purpose: Enforce data contracts with clear error reporting
"""

import re
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List
from dataclasses import dataclass

from .schemas import (
    TelemetrySchema, 
    ThermalState, 
    DeviceType, 
    SCHEMA_CONSTRAINTS
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """
    Explicit validation error with clear context.
    
    Apple principle: Engineers should understand WHY data was rejected.
    """
    field: str
    value: Any
    reason: str
    expected: str
    
    def __str__(self) -> str:
        return (
            f"Validation failed for field '{self.field}': {self.reason}. "
            f"Got: {self.value}, Expected: {self.expected}"
        )


@dataclass
class ValidationResult:
    """
    Result of validation operation.
    
    Either success (valid=True) or failure with explicit errors.
    NO silent failures allowed.
    """
    valid: bool
    errors: List[ValidationError]
    data: Dict[str, Any] | None = None
    
    def log_errors(self) -> None:
        """Log all validation errors clearly"""
        if not self.valid:
            logger.error(f"Validation failed with {len(self.errors)} error(s):")
            for error in self.errors:
                logger.error(f"  - {error}")


class TelemetryValidator:
    """
    Defensive validator for telemetry data.
    
    Responsibilities:
    - Type checking (strict, no coercion)
    - Range validation
    - Format validation (timestamps, UUIDs)
    - Enum validation
    - Timestamp sanity checks (not in future, reasonable range)
    
    NOT responsible for:
    - Data transformation (that's ingestor's job)
    - Storage (that's ingestor's job)
    - Business logic (that's analytics' job)
    """
    
    # UUID v4 regex pattern
    UUID_PATTERN = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    
    @staticmethod
    def validate_device_id(device_id: Any) -> ValidationError | None:
        """
        Validate device ID is a properly formatted UUID v4.
        
        Args:
            device_id: Value to validate
            
        Returns:
            ValidationError if invalid, None if valid
        """
        if not isinstance(device_id, str):
            return ValidationError(
                field='device_id',
                value=device_id,
                reason='Device ID must be a string',
                expected='String (UUID v4 format)'
            )
        
        if not device_id.strip():
            return ValidationError(
                field='device_id',
                value=device_id,
                reason='Device ID cannot be empty or whitespace',
                expected='Non-empty UUID v4 string'
            )
        
        if not TelemetryValidator.UUID_PATTERN.match(device_id):
            return ValidationError(
                field='device_id',
                value=device_id,
                reason='Device ID is not a valid UUID v4',
                expected='UUID v4 format (e.g., 550e8400-e29b-41d4-a716-446655440000)'
            )
        
        return None
    
    @staticmethod
    def validate_timestamp(timestamp: Any) -> ValidationError | None:
        """
        Validate timestamp is a datetime object and within reasonable bounds.
        
        Args:
            timestamp: Value to validate
            
        Returns:
            ValidationError if invalid, None if valid
        """
        if not isinstance(timestamp, datetime):
            return ValidationError(
                field='timestamp',
                value=timestamp,
                reason='Timestamp must be a datetime object',
                expected='datetime object (not string)'
            )
        
        now = datetime.now(timezone.utc)
        
        # Timestamps from the future are suspect (clock skew tolerance: 5 minutes)
        if timestamp.replace(tzinfo=timezone.utc) > now.replace(tzinfo=timezone.utc):
            # Allow 5 minute clock skew
            skew_seconds = (timestamp.replace(tzinfo=timezone.utc) - now.replace(tzinfo=timezone.utc)).total_seconds()
            if skew_seconds > 300:  # 5 minutes
                return ValidationError(
                    field='timestamp',
                    value=timestamp,
                    reason=f'Timestamp is {skew_seconds:.1f}s in the future (beyond 5min clock skew tolerance)',
                    expected='Timestamp not more than 5 minutes in the future'
                )
        
        # Timestamps older than 1 year are suspicious
        age_days = (now - timestamp.replace(tzinfo=timezone.utc)).days
        if age_days > 365:
            return ValidationError(
                field='timestamp',
                value=timestamp,
                reason=f'Timestamp is {age_days} days old (>1 year)',
                expected='Timestamp within the last year'
            )
        
        return None
    
    @staticmethod
    def validate_numeric_range(
        field: str,
        value: Any,
        expected_type: type,
        min_val: float | None = None,
        max_val: float | None = None
    ) -> ValidationError | None:
        """
        Validate numeric value is correct type and within range.
        
        NO automatic type coercion (Apple principle: explicit > implicit).
        
        Args:
            field: Field name
            value: Value to validate
            expected_type: Expected type (int or float)
            min_val: Minimum allowed value (inclusive)
            max_val: Maximum allowed value (inclusive)
            
        Returns:
            ValidationError if invalid, None if valid
        """
        # Type check (strict, no coercion)
        if not isinstance(value, expected_type):
            # Special case: Python sometimes treats int as float-compatible
            if expected_type == float and isinstance(value, int):
                value = float(value)  # Only coerce int -> float
            else:
                return ValidationError(
                    field=field,
                    value=value,
                    reason=f'Expected {expected_type.__name__}, got {type(value).__name__}',
                    expected=f'{expected_type.__name__} type'
                )
        
        # Check for NaN or infinity
        if isinstance(value, float):
            if value != value:  # NaN check
                return ValidationError(
                    field=field,
                    value=value,
                    reason='Value is NaN (Not a Number)',
                    expected='Finite numeric value'
                )
            if abs(value) == float('inf'):
                return ValidationError(
                    field=field,
                    value=value,
                    reason='Value is infinite',
                    expected='Finite numeric value'
                )
        
        # Range validation
        if min_val is not None and value < min_val:
            return ValidationError(
                field=field,
                value=value,
                reason=f'Value {value} is below minimum {min_val}',
                expected=f'Value >= {min_val}'
            )
        
        if max_val is not None and value > max_val:
            return ValidationError(
                field=field,
                value=value,
                reason=f'Value {value} exceeds maximum {max_val}',
                expected=f'Value <= {max_val}'
            )
        
        return None
    
    @staticmethod
    def validate_enum(field: str, value: Any, enum_class: type) -> ValidationError | None:
        """
        Validate value is a valid enum member.
        
        Args:
            field: Field name
            value: Value to validate
            enum_class: Enum class to check against
            
        Returns:
            ValidationError if invalid, None if valid
        """
        if not isinstance(value, enum_class):
            valid_values = [e.value for e in enum_class]
            return ValidationError(
                field=field,
                value=value,
                reason=f'Invalid enum value',
                expected=f'One of {valid_values}'
            )
        
        return None
    
    @staticmethod
    def validate_app_foreground_time(app_time: Any) -> ValidationError | None:
        """
        Validate app foreground time dictionary.
        
        Args:
            app_time: Dictionary to validate
            
        Returns:
            ValidationError if invalid, None if valid
        """
        if not isinstance(app_time, dict):
            return ValidationError(
                field='app_foreground_time',
                value=app_time,
                reason='App foreground time must be a dictionary',
                expected='Dict[str, float] mapping app names to seconds'
            )
        
        for app_name, seconds in app_time.items():
            if not isinstance(app_name, str):
                return ValidationError(
                    field='app_foreground_time',
                    value=app_name,
                    reason=f'App name must be string, got {type(app_name).__name__}',
                    expected='String app name'
                )
            
            if not isinstance(seconds, (int, float)):
                return ValidationError(
                    field='app_foreground_time',
                    value=seconds,
                    reason=f'App time must be numeric, got {type(seconds).__name__}',
                    expected='Float or int (seconds)'
                )
            
            if seconds < 0:
                return ValidationError(
                    field='app_foreground_time',
                    value=seconds,
                    reason=f'App time cannot be negative: {app_name}={seconds}',
                    expected='Non-negative time values'
                )
        
        return None
    
    @classmethod
    def validate_telemetry(cls, data: Dict[str, Any]) -> ValidationResult:
        """
        Validate complete telemetry data record.
        
        This is the main entry point for validation.
        
        Args:
            data: Dictionary of telemetry data
            
        Returns:
            ValidationResult with errors if validation fails
        """
        errors = []
        
        # Validate device_id
        if 'device_id' not in data:
            errors.append(ValidationError(
                field='device_id',
                value=None,
                reason='Missing required field',
                expected='UUID v4 string'
            ))
        else:
            error = cls.validate_device_id(data['device_id'])
            if error:
                errors.append(error)
        
        # Validate timestamp
        if 'timestamp' not in data:
            errors.append(ValidationError(
                field='timestamp',
                value=None,
                reason='Missing required field',
                expected='datetime object'
            ))
        else:
            error = cls.validate_timestamp(data['timestamp'])
            if error:
                errors.append(error)
        
        # Validate numeric fields using schema constraints
        for field, constraints in SCHEMA_CONSTRAINTS.items():
            if field not in data:
                errors.append(ValidationError(
                    field=field,
                    value=None,
                    reason='Missing required field',
                    expected=f'{constraints["type"].__name__} in range [{constraints.get("min", "-∞")}, {constraints.get("max", "∞")}]'
                ))
            else:
                error = cls.validate_numeric_range(
                    field=field,
                    value=data[field],
                    expected_type=constraints['type'],
                    min_val=constraints.get('min'),
                    max_val=constraints.get('max')
                )
                if error:
                    errors.append(error)
        
        # Validate enums
        if 'thermal_state' not in data:
            errors.append(ValidationError(
                field='thermal_state',
                value=None,
                reason='Missing required field',
                expected=f'ThermalState enum'
            ))
        else:
            error = cls.validate_enum('thermal_state', data['thermal_state'], ThermalState)
            if error:
                errors.append(error)
        
        if 'device_type' not in data:
            errors.append(ValidationError(
                field='device_type',
                value=None,
                reason='Missing required field',
                expected=f'DeviceType enum'
            ))
        else:
            error = cls.validate_enum('device_type', data['device_type'], DeviceType)
            if error:
                errors.append(error)
        
        # Validate app_foreground_time
        if 'app_foreground_time' not in data:
            errors.append(ValidationError(
                field='app_foreground_time',
                value=None,
                reason='Missing required field',
                expected='Dict[str, float]'
            ))
        else:
            error = cls.validate_app_foreground_time(data['app_foreground_time'])
            if error:
                errors.append(error)
        
        # Return validation result
        if errors:
            return ValidationResult(valid=False, errors=errors, data=None)
        else:
            return ValidationResult(valid=True, errors=[], data=data)
