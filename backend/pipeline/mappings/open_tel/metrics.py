import pathway as pw
from typing import Optional
import json
from lib.open_tel.utils import flatten_attributes, safe_int, safe_float
from lib.open_tel.input_nodes import OpenTelMetricsNode
from lib.kafka_utils import convert_rdkafka_settings


class Metric(pw.Schema):
    # Metric metadata
    metric_name: str  # Required
    metric_description: str  # Can be empty
    metric_unit: str  # Can be empty
    metric_type: str  # "gauge", "sum", "histogram", "exponential_histogram", "summary"
    
    # Metric-level metadata (optional)
    metadata: pw.Json  # Optional metric metadata attributes
    
    metric_attributes: pw.Json
    
    # All data points as a complete array
    data_points: pw.Json  # Array of data point objects with all fields
    
    # Resource and scope context
    resource_attributes: pw.Json
    resource_schema_url: str
    scope_name: str
    scope_version: str
    scope_attributes: pw.Json
    scope_schema_url: str

def process_data_point(dp: dict, metric_type: str) -> dict:
    """Process a single data point with proper handling of optional fields"""
    # Flatten attributes
    dp_attrs = flatten_attributes(dp.get("attributes", []))
    
    # Required time field (0 = invalid, should skip)
    time = safe_int(dp.get("timeUnixNano"),0)
    if time == 0:
        return None  # Invalid data point
    
    # Optional but strongly encouraged
    start_time = safe_int(dp.get("startTimeUnixNano"),0)
    
    # Extract value based on metric type
    value = None
    if metric_type in ["gauge", "sum"]:
        # NumberDataPoint - has oneof value
        if "asDouble" in dp:
            value = safe_float(dp["asDouble"])
        elif "asInt" in dp:
            value = safe_int(dp["asInt"])
    elif metric_type == "histogram":
        # HistogramDataPoint
        sum_val = dp.get("sum")
        min_val = dp.get("min")
        max_val = dp.get("max")
        value = {
            "count": safe_int(dp.get("count"), 0),
            "sum": safe_float(sum_val) if sum_val is not None else None,  
            "bucket_counts": [safe_int(bc) for bc in dp.get("bucketCounts", [])],
            "explicit_bounds": [safe_float(eb) for eb in dp.get("explicitBounds", [])],
            "min": safe_float(min_val) if min_val is not None else None,
            "max": safe_float(max_val) if max_val is not None else None,
        }
    elif metric_type == "exponential_histogram":
        # ExponentialHistogramDataPoint
        sum_val = dp.get("sum")
        min_val = dp.get("min")
        max_val = dp.get("max")
        value = {
            "count": safe_int(dp.get("count"), 0),
            "sum": safe_float(sum_val) if sum_val is not None else None,
            "scale": safe_int(dp.get("scale"), 0),
            "zero_count": safe_int(dp.get("zeroCount"), 0), 
            "zero_threshold": safe_float(dp.get("zeroThreshold"), 0.0), 
            "positive": dp.get("positive", {}),
            "negative": dp.get("negative", {}),
            "min": safe_float(min_val) if min_val is not None else None,
            "max": safe_float(max_val) if max_val is not None else None,
        }
    elif metric_type == "summary":
        # SummaryDataPoint
        value = {
            "count": dp.get("count", 0),
            "sum": dp.get("sum", 0.0),
            "quantile_values": dp.get("quantileValues", [])
        }
    
    # Process exemplars (optional)
    exemplars = []
    for ex in dp.get("exemplars", []):
        ex_value = None
        if "asDouble" in ex:
            ex_value = ex["asDouble"]
        elif "asInt" in ex:
            ex_value = ex["asInt"]
        
        exemplars.append({
            "filtered_attributes": flatten_attributes(ex.get("filteredAttributes", [])),
            "time_unix_nano": safe_int(ex.get("timeUnixNano"),0),
            "value": ex_value,
            "span_id": ex.get("spanId"),  # Optional
            "trace_id": ex.get("traceId"),  # Optional
        })
    
    return {
        "attributes": dp_attrs,
        "start_time_unix_nano": start_time,
        "time_unix_nano": time,
        "value": value,
        "exemplars": exemplars if exemplars else [],
        "flags": dp.get("flags", 0),
    }


def flatten_metrics(data: str) -> list[dict]:
    """Flatten OTLP metrics while keeping data points as complete arrays"""
    metrics = json.loads(data)
    flattened = []
    
    for resource_metric in metrics.get("resourceMetrics", []):
        resource = resource_metric.get("resource", {})
        resource_attrs = flatten_attributes(resource.get("attributes", []))
        resource_schema = resource_metric.get("schemaUrl", "")
        
        for scope_metric in resource_metric.get("scopeMetrics", []):
            scope = scope_metric.get("scope", {})
            scope_name = scope.get("name", "")
            scope_version = scope.get("version", "")
            scope_attrs = flatten_attributes(scope.get("attributes", []))
            scope_schema = scope_metric.get("schemaUrl", "")
            
            for metric in scope_metric.get("metrics", []):
                metric_name = metric.get("name", "")
                metric_desc = metric.get("description", "")
                metric_unit = metric.get("unit", "")
                
                # Optional metric metadata
                metadata = flatten_attributes(metric.get("metadata", []))
                
                # Determine metric type and extract data points
                data_points_raw = []
                metric_type = ""
                aggregation_temporality = None
                is_monotonic = None
                
                if "gauge" in metric:
                    metric_type = "gauge"
                    data_points_raw = metric["gauge"].get("dataPoints", [])
                elif "sum" in metric:
                    metric_type = "sum"
                    sum_data = metric["sum"]
                    data_points_raw = sum_data.get("dataPoints", [])
                    aggregation_temporality = safe_int(sum_data.get("aggregationTemporality"), 0)
                    is_monotonic = sum_data.get("isMonotonic", False)
                elif "histogram" in metric:
                    metric_type = "histogram"
                    hist_data = metric["histogram"]
                    data_points_raw = hist_data.get("dataPoints", [])
                    aggregation_temporality = safe_int(hist_data.get("aggregationTemporality"), 0)
                elif "exponentialHistogram" in metric:
                    metric_type = "exponential_histogram"
                    exp_hist_data = metric["exponentialHistogram"]
                    data_points_raw = exp_hist_data.get("dataPoints", [])
                    aggregation_temporality = safe_int(exp_hist_data.get("aggregationTemporality"), 0)
                elif "summary" in metric:
                    metric_type = "summary"
                    data_points_raw = metric["summary"].get("dataPoints", [])
                
                # Process all data points
                data_points = []
                for dp in data_points_raw:
                    processed_dp = process_data_point(dp, metric_type)
                    if processed_dp:  # Skip invalid data points
                        data_points.append(processed_dp)
                
                # Only add metric if it has valid data points
                if data_points:
                    flattened.append({
                        "metric_name": metric_name,
                        "metric_description": metric_desc,
                        "metric_unit": metric_unit,
                        "metric_type": metric_type,
                        "metadata": metadata if metadata else {},
                        "metric_attributes": {
                            "aggregation_temporality": aggregation_temporality,
                            "is_monotonic": is_monotonic,
                        },
                        "data_points": data_points,
                        "resource_attributes": resource_attrs,
                        "resource_schema_url": resource_schema,
                        "scope_name": scope_name,
                        "scope_version": scope_version,
                        "scope_attributes": scope_attrs,
                        "scope_schema_url": scope_schema,
                    })
    
    return flattened

def read_metrics(_,node:OpenTelMetricsNode):
    kafka_metrics = pw.io.kafka.read(
        rdkafka_settings=convert_rdkafka_settings(node.rdkafka_settings),
        topic=node.topic,
        format="plaintext",
    )

    metrics_table = kafka_metrics.select(
        flattened=pw.apply(flatten_metrics, pw.this.data)
    ).flatten(pw.this.flattened).select(
        metric_name=pw.unwrap(pw.this.flattened["metric_name"].as_str()),
        metric_description=pw.unwrap(pw.this.flattened["metric_description"].as_str()),
        metric_unit=pw.unwrap(pw.this.flattened["metric_unit"].as_str()),
        metric_type=pw.unwrap(pw.this.flattened["metric_type"].as_str()),
        metadata=pw.this.flattened["metadata"],
        metric_attributes=pw.this.flattened["metric_attributes"],
        data_points=pw.this.flattened["data_points"],
        resource_attributes=pw.this.flattened["resource_attributes"],
        resource_schema_url=pw.unwrap(pw.this.flattened["resource_schema_url"].as_str()),
        scope_name=pw.unwrap(pw.this.flattened["scope_name"].as_str()),
        scope_version=pw.unwrap(pw.this.flattened["scope_version"].as_str()),
        scope_attributes=pw.this.flattened["scope_attributes"],
        scope_schema_url=pw.unwrap(pw.this.flattened["scope_schema_url"].as_str()),
    )._with_schema(Metric)
    return metrics_table


