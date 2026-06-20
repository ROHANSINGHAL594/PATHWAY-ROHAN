import pathway as pw
from typing import Optional
import json
from lib.open_tel.utils import flatten_attributes, safe_int
from lib.open_tel.input_nodes import OpenTelSpansNode
from lib.kafka_utils import convert_rdkafka_settings

class Span(pw.Schema):
    # Span identity fields
    _open_tel_trace_id: str  # Required, must be non-empty
    _open_tel_span_id: str  # Required, must be non-empty
    _open_tel_parent_span_id: str  # empty for root spans
    _open_tel_service_name: str
    _open_tel_service_namespace: str

    # Span metadata
    name: str  # Required
    kind: int  # Default 0 = SPAN_KIND_UNSPECIFIED
    start_time_unix_nano: int  # Required
    end_time_unix_nano: int # Required
    
    trace_state: str # W3C trace state
    
    # Status
    status_code: int  # Default 0 = STATUS_CODE_UNSET
    status_message: str
    
    # Span attributes and counters
    attributes: pw.Json  # Flattened span attributes
    dropped_attributes_count: int  # Default 0
    
    # Events (complete nested array)
    events: pw.Json  # Array of Event objects
    dropped_events_count: int  # Default 0
    
    # Links (complete nested array)
    links: pw.Json  # Array of Link objects
    dropped_links_count: int  # Default 0
    
    # Resource fields (flattened attributes as JSON dict)
    resource_attributes: pw.Json
    resource_schema_url: str
    
    # Scope fields (flattened attributes as JSON dict)
    scope_name: str
    scope_version: str
    scope_attributes: pw.Json
    scope_schema_url: str

def process_span_events(events) -> list[dict]:
    if not events:
        return []
    
    processed_events = []
    for event in events:
        processed_events.append({
            "time_unix_nano": safe_int(event.get("timeUnixNano"),0),
            "name": event.get("name", ""),
            "attributes": flatten_attributes(event.get("attributes", [])),
            "dropped_attributes_count": safe_int(event.get("droppedAttributesCount"), 0)
        })
    return processed_events

def process_span_links(links) -> list[dict]:
    if not links:
        return []
    
    processed_links = []
    for link in links:
        trace_id = link.get("traceId")
        span_id = link.get("spanId")
        
        if not trace_id or not span_id:
            continue
            
        processed_links.append({
            "trace_id": trace_id,
            "span_id": span_id,
            "trace_state": link.get("traceState"),
            "attributes": flatten_attributes(link.get("attributes", [])),
            "dropped_attributes_count": safe_int(link.get("droppedAttributesCount"), 0),
            "flags": safe_int(link.get("flags")) if link.get("flags") is not None else None
        })
    return processed_links

def flatten_spans(data: str) -> list[dict]:
    """Flatten OTLP spans while preserving events and links as complete objects"""
    traces = json.loads(data)
    flattened = []
    
    for resource_span in traces.get("resourceSpans", []):
        resource = resource_span.get("resource", {})
        resource_attrs = flatten_attributes(resource.get("attributes", []))
        resource_schema = resource_span.get("schemaUrl", "")
        
        for scope_span in resource_span.get("scopeSpans", []):
            scope = scope_span.get("scope", {})
            scope_name = scope.get("name", "")
            scope_version = scope.get("version", "")
            scope_attrs = flatten_attributes(scope.get("attributes", []))
            scope_schema = scope_span.get("schemaUrl", "")
            
            for span in scope_span.get("spans", []):
                # Validate required fields
                trace_id = span.get("traceId")
                if not trace_id:
                    continue  # Skip invalid spans
                
                span_id = span.get("spanId")
                if not span_id:
                    continue  # Skip invalid spans
                
                # Optional parent_span_id (empty for root spans)
                parent_span_id = span.get("parentSpanId", "")
                
                # Process status (optional, defaults to UNSET)
                status = span.get("status", {})
                
                # Process events and links as complete objects
                events = process_span_events(span.get("events", []))
                links = process_span_links(span.get("links", []))
                service_name = resource_attrs.pop("service.name", "")
                service_namespace = resource_attrs.pop("service.namespace", "")
                flattened.append({
                    "trace_id": trace_id,
                    "span_id": span_id,
                    "parent_span_id": parent_span_id,
                    "service_name": service_name,
                    "service_namespace": service_namespace,
                    "name": span.get("name", ""),
                    "kind": safe_int(span.get("kind"), 0),
                    "status_code": safe_int(status.get("code"), 0),
                    "dropped_attributes_count": safe_int(span.get("droppedAttributesCount"), 0),
                    "dropped_events_count": safe_int(span.get("droppedEventsCount"), 0),
                    "dropped_links_count": safe_int(span.get("droppedLinksCount"), 0),
                    "start_time_unix_nano": safe_int(span.get("startTimeUnixNano")),
                    "end_time_unix_nano": safe_int(span.get("endTimeUnixNano")),
                    "trace_state": span.get("traceState", ""),  
                    "status_message": status.get("message", ""),
                    "attributes": flatten_attributes(span.get("attributes", [])),
                    "events": events,
                    "links": links,
                    "resource_attributes": resource_attrs,
                    "resource_schema_url": resource_schema,
                    "scope_name": scope_name,
                    "scope_version": scope_version,
                    "scope_attributes": scope_attrs,
                    "scope_schema_url": scope_schema,
                })
    
    return flattened



def read_spans(_, node: OpenTelSpansNode):
    kafka_spans = pw.io.kafka.read(
        rdkafka_settings=convert_rdkafka_settings(node.rdkafka_settings),
        topic=node.topic,
        format="plaintext",
    )

    spans_table = kafka_spans.select(
        flattened=pw.apply(flatten_spans, pw.this.data)
    ).flatten(pw.this.flattened).select(
        _open_tel_trace_id=pw.unwrap(pw.this.flattened["trace_id"].as_str()),
        _open_tel_span_id=pw.unwrap(pw.this.flattened["span_id"].as_str()),
        _open_tel_parent_span_id=pw.unwrap(pw.this.flattened["parent_span_id"].as_str()),
        _open_tel_service_name=pw.unwrap(pw.this.flattened["service_name"].as_str()),
        _open_tel_service_namespace=pw.unwrap(pw.this.flattened["service_namespace"].as_str()),
        name=pw.unwrap(pw.this.flattened["name"].as_str()),
        kind=pw.unwrap(pw.this.flattened["kind"].as_int()),
        start_time_unix_nano=pw.unwrap(pw.this.flattened["start_time_unix_nano"].as_int()),
        end_time_unix_nano=pw.unwrap(pw.this.flattened["end_time_unix_nano"].as_int()),
        trace_state=pw.unwrap(pw.this.flattened["trace_state"].as_str()),
        status_code=pw.unwrap(pw.this.flattened["status_code"].as_int()),
        status_message=pw.unwrap(pw.this.flattened["status_message"].as_str()),
        attributes=pw.this.flattened["attributes"],
        dropped_attributes_count=pw.unwrap(pw.this.flattened["dropped_attributes_count"].as_int()),
        events=pw.this.flattened["events"],
        dropped_events_count=pw.unwrap(pw.this.flattened["dropped_events_count"].as_int()),
        links=pw.this.flattened["links"],
        dropped_links_count=pw.unwrap(pw.this.flattened["dropped_links_count"].as_int()),
        resource_attributes=pw.this.flattened["resource_attributes"],
        resource_schema_url=pw.unwrap(pw.this.flattened["resource_schema_url"].as_str()),
        scope_name=pw.unwrap(pw.this.flattened["scope_name"].as_str()),
        scope_version=pw.unwrap(pw.this.flattened["scope_version"].as_str()),
        scope_attributes=pw.this.flattened["scope_attributes"],
        scope_schema_url=pw.unwrap(pw.this.flattened["scope_schema_url"].as_str()),
    )._with_schema(Span)
    return spans_table