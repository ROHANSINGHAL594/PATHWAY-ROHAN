import pathway as pw
from typing import Optional
import json
from lib.open_tel.utils import flatten_attributes, extract_anyvalue
from lib.open_tel.input_nodes import OpenTelLogsNode
from lib.kafka_utils import convert_rdkafka_settings
from lib.open_tel.utils import flatten_attributes, safe_int


class Log(pw.Schema):
    # Timestamps
    time_unix_nano: int  # Can be 0 (unknown)
    observed_time_unix_nano: int  # Can be 0 (unknown)
    

    _open_tel_service_name: str
    _open_tel_service_namespace: str

    # Severity
    severity_number: int  # Default 0 (SEVERITY_NUMBER_UNSPECIFIED)
    severity_text: str  # Optional, can be empty string
    
    # Log content
    body: Optional[pw.Json]
    
    # Attributes
    log_attributes: pw.Json
    dropped_attributes_count: int  # Default 0
    
    # Optional trace correlation
    _open_tel_trace_id: str  # Optional - for correlation
    _open_tel_span_id: str  # Optional - for correlation
    
    # Optional event identification
    event_name: str  # Optional, can be empty

    
    # Resource and scope context
    resource_attributes: pw.Json
    resource_schema_url: str
    scope_name: str
    scope_version: str
    scope_attributes: pw.Json
    scope_schema_url: str

def flatten_logs(data: str) -> list[dict]:
    """Flatten OTLP logs"""
    logs = json.loads(data)
    flattened = []
    
    for resource_log in logs.get("resourceLogs", []):
        resource = resource_log.get("resource", {})
        resource_attrs = flatten_attributes(resource.get("attributes", []))
        resource_schema = resource_log.get("schemaUrl", "")
        
        for scope_log in resource_log.get("scopeLogs", []):
            scope = scope_log.get("scope", {})
            scope_name = scope.get("name", "")
            scope_version = scope.get("version", "")
            scope_attrs = flatten_attributes(scope.get("attributes", []))
            scope_schema = scope_log.get("schemaUrl", "")
            
            for log_record in scope_log.get("logRecords", []):
                # Extract body as AnyValue (optional)
                body = extract_anyvalue(log_record.get("body", {}))
                log_attrs = flatten_attributes(log_record.get("attributes", []))
                
                # Handle optional trace_id and span_id (can be invalid/empty)
                trace_id = log_record.get("traceId", "")
                span_id = log_record.get("spanId", "")
                
                service_name = resource_attrs.pop("service.name", "")
                service_namespace = resource_attrs.pop("service.namespace", "")

                flattened.append({
                    "time_unix_nano": safe_int(log_record.get("timeUnixNano"),0),  # 0 = unknown
                    "observed_time_unix_nano": safe_int(log_record.get("observedTimeUnixNano"),0),  # 0 = unknown
                    "severity_text": log_record.get("severityText", ""), 
                    "body": body,  # Optional
                    "log_attributes": log_attrs,
                    "severity_number": safe_int(log_record.get("severityNumber"), 0), # Default SEVERITY_NUMBER_UNSPECIFIED
                    "dropped_attributes_count": safe_int(log_record.get("droppedAttributesCount"), 0),
                    "trace_id": trace_id,
                    "span_id": span_id,
                    "service_name": service_name,
                    "service_namespace": service_namespace,
                    "event_name": log_record.get("eventName", ""),
                    "resource_attributes": resource_attrs,
                    "resource_schema_url": resource_schema,
                    "scope_name": scope_name,
                    "scope_version": scope_version,
                    "scope_attributes": scope_attrs,
                    "scope_schema_url": scope_schema,
                })
    
    return flattened


def read_logs(_,node:OpenTelLogsNode):
    kafka_logs = pw.io.kafka.read(
        rdkafka_settings=convert_rdkafka_settings(node.rdkafka_settings),
        topic=node.topic,
        format="plaintext",
    )

    logs_table = kafka_logs.select(
        flattened=pw.apply(flatten_logs, pw.this.data)
    ).flatten(pw.this.flattened).select(
        time_unix_nano=pw.unwrap(pw.this.flattened["time_unix_nano"].as_int()),
        observed_time_unix_nano=pw.unwrap(pw.this.flattened["observed_time_unix_nano"].as_int()), 
        severity_number=pw.unwrap(pw.this.flattened["severity_number"].as_int()),
        severity_text=pw.unwrap(pw.this.flattened["severity_text"].as_str()),
        body=pw.this.flattened["body"],
        log_attributes=pw.this.flattened["log_attributes"],
        dropped_attributes_count=pw.unwrap(pw.this.flattened["dropped_attributes_count"].as_int()),
        _open_tel_trace_id=pw.unwrap(pw.this.flattened["trace_id"].as_str()),
        _open_tel_span_id=pw.unwrap(pw.this.flattened["span_id"].as_str()),
        _open_tel_service_name=pw.unwrap(pw.this.flattened["service_name"].as_str()),
        _open_tel_service_namespace=pw.unwrap(pw.this.flattened["service_namespace"].as_str()),
        event_name=pw.unwrap(pw.this.flattened["event_name"].as_str()),
        resource_attributes=pw.this.flattened["resource_attributes"],
        resource_schema_url=pw.unwrap(pw.this.flattened["resource_schema_url"].as_str()),
        scope_name=pw.unwrap(pw.this.flattened["scope_name"].as_str()),
        scope_version=pw.unwrap(pw.this.flattened["scope_version"].as_str()),
        scope_attributes=pw.this.flattened["scope_attributes"],
        scope_schema_url=pw.unwrap(pw.this.flattened["scope_schema_url"].as_str()),
    )._with_schema(Log)

    return logs_table
