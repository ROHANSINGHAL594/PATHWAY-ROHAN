import base64
from typing import Optional, Any


def safe_int(value, default=0) -> int:
    """Safely convert string/int to int (handles OTLP JSON string encoding)"""
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    return default


def safe_float(value, default=0.0) -> float:
    """Safely convert string/float to float"""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    return default


def decode_bytes(value) -> Optional[str]:
    """Decode base64-encoded bytes from OTLP JSON"""
    if not value:
        return None
    if isinstance(value, str):
        try:
            # In OTLP JSON, bytes are base64-encoded
            decoded = base64.b64decode(value)
            # Return as hex string for readability
            return decoded.hex()
        except Exception:
            return value  # Return as-is if not base64
    return value


def extract_anyvalue(value_obj) -> Optional[Any]:
    """Extract the actual value from OTLP AnyValue union"""
    if not value_obj:
        return None
    
    # Check each possible value type
    if "stringValue" in value_obj:
        return value_obj["stringValue"]
    elif "intValue" in value_obj:
        # intValue can be string in JSON
        return safe_int(value_obj["intValue"])
    elif "doubleValue" in value_obj:
        # doubleValue can be string in JSON
        return safe_float(value_obj["doubleValue"])
    elif "boolValue" in value_obj:
        # boolValue is native JSON boolean
        return bool(value_obj["boolValue"])
    elif "bytesValue" in value_obj:
        # bytesValue is base64-encoded string in JSON
        return decode_bytes(value_obj["bytesValue"])
    elif "arrayValue" in value_obj:
        return [extract_anyvalue(v) for v in value_obj["arrayValue"].get("values", [])]
    elif "kvlistValue" in value_obj:
        return flatten_attributes(value_obj["kvlistValue"].get("values", []))
    
    return None



def flatten_attributes(attributes) -> dict:
    """Convert OTLP KeyValue array to simple dict"""
    if not attributes:
        return {}
    result = {}
    for kv in attributes:
        key = kv.get("key", "")
        value = extract_anyvalue(kv.get("value", {}))
        if key:
            result[key] = value
    return result





