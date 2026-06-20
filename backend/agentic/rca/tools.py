from typing import List, Union, Dict, Any
from typing_extensions import TypedDict
from sqlalchemy import text
from postgres_util import postgre_engine
import asyncio
from functools import wraps
class TablePayload(TypedDict):
    table_name: str

def retry_on_falsy(max_retries: int = 3, delay_seconds: int = 2):
    """
    Decorator that retries a function if its result is falsy.
    Sleeps for delay_seconds before each attempt.
    
    Args:
        max_retries: Maximum number of attempts (default 3 for 6 seconds total)
        delay_seconds: Seconds to sleep before each attempt (default 2)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                await asyncio.sleep(delay_seconds)
                result = await func(*args, **kwargs)
                if bool(result):
                    return result
            return result  # Return the final result even if falsy
        return wrapper
    return decorator

@retry_on_falsy()
async def get_logs_for_trace_ids(trace_ids: Union[List[str], str], logs_table: TablePayload) -> List[Dict[str, Any]]:
    """
    Query logs for given trace IDs using SQLAlchemy.
    
    Args:
        trace_ids: Single trace_id string or list of trace_ids
        logs_table: TablePayload containing logs table information
        
    Returns:
        List of dictionaries containing log records
    """
    # Normalize trace_ids to list
    if isinstance(trace_ids, str):
        trace_ids = [trace_ids]
    if not trace_ids:
        return []
    
    # Build SQL query with proper escaping
    trace_ids_str = "', '".join(trace_ids)
    sql_query = f"""
    SELECT 
        time_unix_nano,
        observed_time_unix_nano,
        _open_tel_trace_id,
        _open_tel_span_id,
        body,
        _open_tel_service_name,
        _open_tel_service_namespace,
        severity_number,
        severity_text,
        scope_name
    FROM {logs_table["table_name"]}
    WHERE _open_tel_trace_id IN ('{trace_ids_str}')
    ORDER BY observed_time_unix_nano
    """
    
    with postgre_engine.connect() as conn:
        result = conn.execute(text(sql_query))
        rows = [dict(row._mapping) for row in result]
    
    return rows

@retry_on_falsy()
async def get_error_logs_for_trace_ids(trace_ids: Union[List[str], str], logs_table: TablePayload, severity_number: int) -> List[Dict[str, Any]]:
    """
    Query error logs for given trace IDs using SQLAlchemy.
    Filters for severity_number >= 13 (ERROR level and above).
    
    Args:
        trace_ids: Single trace_id string or list of trace_ids
        logs_table: TablePayload containing logs table information
        
    Returns:
        List of dictionaries containing error log records
    """
    # Normalize trace_ids to list
    if isinstance(trace_ids, str):
        trace_ids = [trace_ids]
    if not trace_ids:
        return []
    print("Getting error logs for trace ids")
    # Build SQL query with proper escaping
    trace_ids_str = "', '".join(trace_ids)
    sql_query = f"""
    SELECT 
        time_unix_nano,
        observed_time_unix_nano,
        _open_tel_trace_id,
        _open_tel_span_id,
        body,
        _open_tel_service_name,
        _open_tel_service_namespace,
        severity_number,
        severity_text,
        scope_name
    FROM {logs_table["table_name"]}
    WHERE _open_tel_trace_id IN ('{trace_ids_str}')
        AND severity_number >= {severity_number}
    ORDER BY observed_time_unix_nano
    """
    
    with postgre_engine.connect() as conn:
        result = conn.execute(text(sql_query))
        rows = [dict(row._mapping) for row in result]
    print(f"Retreived error logs: {rows}")
    return rows

@retry_on_falsy()
async def get_error_spans_for_trace_ids(trace_ids: Union[List[str], str], spans_table: TablePayload, min_status_code: int = 2) -> List[Dict[str, Any]]:
    """
    Query error spans for given trace IDs using SQLAlchemy.
    Filters for status_code >= min_status_code (default 2 = ERROR status).
    
    Args:
        trace_ids: Single trace_id string or list of trace_ids
        spans_table: TablePayload containing spans table information
        min_status_code: Minimum status code to filter (default 2, where 2=ERROR)
        
    Returns:
        List of dictionaries containing error span records with status messages
    """
    # Normalize trace_ids to list
    if isinstance(trace_ids, str):
        trace_ids = [trace_ids]
    if not trace_ids:
        return []
    
    print(f"Getting error spans for trace ids with status_code >= {min_status_code}")
    # Build SQL query with proper escaping
    trace_ids_str = "', '".join(trace_ids)
    sql_query = f"""
    SELECT 
        _open_tel_trace_id,
        _open_tel_span_id,
        _open_tel_parent_span_id,
        _open_tel_service_name,
        _open_tel_service_namespace,
        name,
        kind,
        start_time_unix_nano,
        end_time_unix_nano,
        status_code,
        status_message,
        scope_name
    FROM {spans_table["table_name"]}
    WHERE _open_tel_trace_id IN ('{trace_ids_str}')
        AND status_code >= {min_status_code}
    ORDER BY start_time_unix_nano
    """
    
    with postgre_engine.connect() as conn:
        result = conn.execute(text(sql_query))
        rows = [dict(row._mapping) for row in result]
    
    print(f"Retrieved error spans: {len(rows)} spans with errors")
    return rows

@retry_on_falsy()
async def get_parent_chain(span_id: str, trace_id: str, spans_table: TablePayload) -> List[Dict[str, Any]]:
    """
    Build an ordered list of parent spans from the given span_id up to the root span.
    Uses PostgreSQL recursive CTE to traverse the parent hierarchy.
    """
    sql_query = f"""
    WITH RECURSIVE parent_chain AS (
        -- Base case: start with the given span
        SELECT 
            _open_tel_span_id,
            _open_tel_parent_span_id,
            _open_tel_trace_id,
            _open_tel_service_name,
            _open_tel_service_namespace,
            name,
            kind,
            start_time_unix_nano,
            end_time_unix_nano,
            status_code,
            status_message,
            scope_name,
            1 as depth
        FROM {spans_table["table_name"]}
        WHERE _open_tel_span_id = '{span_id}' 
            AND _open_tel_trace_id = '{trace_id}'
        
        UNION ALL
        
        -- Recursive case: get parent spans
        SELECT 
            s._open_tel_span_id,
            s._open_tel_parent_span_id,
            s._open_tel_trace_id,
            s._open_tel_service_name,
            s._open_tel_service_namespace,
            s.name,
            s.kind,
            s.start_time_unix_nano,
            s.end_time_unix_nano,
            s.status_code,
            s.status_message,
            s.scope_name,
            pc.depth + 1
        FROM {spans_table["table_name"]} s
        INNER JOIN parent_chain pc ON s._open_tel_span_id = pc._open_tel_parent_span_id
        WHERE s._open_tel_trace_id = '{trace_id}'
            AND pc._open_tel_parent_span_id != ''
    )
    SELECT * FROM parent_chain
    ORDER BY depth DESC;
    """
    
    with postgre_engine.connect() as conn:
        result = conn.execute(text(sql_query))
        rows = [dict(row._mapping) for row in result]
    
    return rows


@retry_on_falsy()
async def get_child_tree(span_id: str, trace_id: str, spans_table: TablePayload) -> List[Dict[str, Any]]:
    """
    Build a tree of all child spans for the given span_id.
    Uses PostgreSQL recursive CTE to traverse the child hierarchy.
    """
    sql_query = f"""
    WITH RECURSIVE child_tree AS (
        -- Base case: start with the given span
        SELECT 
            _open_tel_span_id,
            _open_tel_parent_span_id,
            _open_tel_trace_id,
            _open_tel_service_name,
            _open_tel_service_namespace,
            name,
            kind,
            start_time_unix_nano,
            end_time_unix_nano,
            status_code,
            status_message,
            scope_name,
            0 as depth,
            _open_tel_span_id as path
        FROM {spans_table["table_name"]}
        WHERE _open_tel_span_id = '{span_id}' 
            AND _open_tel_trace_id = '{trace_id}'
        
        UNION ALL
        
        -- Recursive case: get child spans
        SELECT 
            s._open_tel_span_id,
            s._open_tel_parent_span_id,
            s._open_tel_trace_id,
            s._open_tel_service_name,
            s._open_tel_service_namespace,
            s.name,
            s.kind,
            s.start_time_unix_nano,
            s.end_time_unix_nano,
            s.status_code,
            s.status_message,
            s.scope_name,
            ct.depth + 1,
            ct.path || ' -> ' || s._open_tel_span_id
        FROM {spans_table["table_name"]} s
        INNER JOIN child_tree ct ON s._open_tel_parent_span_id = ct._open_tel_span_id
        WHERE s._open_tel_trace_id = '{trace_id}'
    )
    SELECT * FROM child_tree
    ORDER BY path, depth;
    """
    
    with postgre_engine.connect() as conn:
        result = conn.execute(text(sql_query))
        rows = [dict(row._mapping) for row in result]
    
    return rows


@retry_on_falsy()
async def get_full_span_tree(trace_id: str, spans_table: TablePayload) -> List[Dict[str, Any]]:
    """
    Build the complete span tree for a given trace_id, showing all parent-child relationships.
    Uses PostgreSQL recursive CTE starting from root spans (spans with no parent).
    """
    sql_query = f"""
    WITH RECURSIVE span_tree AS (
        -- Base case: start with root spans (no parent or empty parent)
        SELECT 
            _open_tel_span_id,
            _open_tel_parent_span_id,
            _open_tel_trace_id,
            _open_tel_service_name,
            _open_tel_service_namespace,
            name,
            kind,
            start_time_unix_nano,
            end_time_unix_nano,
            status_code,
            status_message,
            attributes,
            events,
            links,
            scope_name,
            0 as depth,
            _open_tel_span_id as path,
            ARRAY[start_time_unix_nano] as time_path
        FROM {spans_table["table_name"]}
        WHERE _open_tel_trace_id = '{trace_id}'
            AND (_open_tel_parent_span_id = '' OR _open_tel_parent_span_id IS NULL)
        
        UNION ALL
        
        -- Recursive case: get child spans
        SELECT 
            s._open_tel_span_id,
            s._open_tel_parent_span_id,
            s._open_tel_trace_id,
            s._open_tel_service_name,
            s._open_tel_service_namespace,
            s.name,
            s.kind,
            s.start_time_unix_nano,
            s.end_time_unix_nano,
            s.status_code,
            s.status_message,
            s.attributes,
            s.events,
            s.links,
            s.scope_name,
            st.depth + 1,
            st.path || ' -> ' || s._open_tel_span_id,
            st.time_path || s.start_time_unix_nano
        FROM {spans_table["table_name"]} s
        INNER JOIN span_tree st ON s._open_tel_parent_span_id = st._open_tel_span_id
        WHERE s._open_tel_trace_id = '{trace_id}'
    )
    SELECT 
        *
    FROM span_tree
    ORDER BY time_path, depth;
    """
    
    with postgre_engine.connect() as conn:
        result = conn.execute(text(sql_query))
        rows = [dict(row._mapping) for row in result]
    
    return rows

@retry_on_falsy()
async def get_logs_in_time_window(
    start_time: int,
    end_time: int,
    logs_table: TablePayload,
    min_severity: int = 0,
    max_results: int = 1000
) -> List[Dict[str, Any]]:
    """
    Query logs within a time window with optional severity filtering.
    
    Args:
        start_time: Start time in Unix nanoseconds
        end_time: End time in Unix nanoseconds
        logs_table: TablePayload containing logs table information
        min_severity: Minimum severity number to include (default 0 = all)
        max_results: Maximum number of results to return (default 1000)
        
    Returns:
        List of dictionaries containing log records
    """
    sql_query = f"""
    SELECT 
        time_unix_nano,
        observed_time_unix_nano,
        _open_tel_trace_id,
        _open_tel_span_id,
        body,
        _open_tel_service_name,
        _open_tel_service_namespace,
        severity_number,
        severity_text,
        scope_name
    FROM {logs_table["table_name"]}
    WHERE observed_time_unix_nano >= {start_time}
        AND observed_time_unix_nano <= {end_time}
        AND severity_number >= {min_severity}
    ORDER BY observed_time_unix_nano
    LIMIT {max_results}
    """
    
    with postgre_engine.connect() as conn:
        result = conn.execute(text(sql_query))
        rows = [dict(row._mapping) for row in result]
    
    return rows

@retry_on_falsy()
async def get_error_spans_in_time_window(
    start_time: int,
    end_time: int,
    spans_table: TablePayload,
    min_status_code: int = 2
) -> List[Dict[str, Any]]:
    """
    Query error spans within a time window with status code filtering.
    
    Args:
        start_time: Start time in Unix nanoseconds
        end_time: End time in Unix nanoseconds
        spans_table: TablePayload containing spans table information
        min_status_code: Minimum status code to include (default 2 = ERROR)
        
    Returns:
        List of dictionaries containing error span records with status messages
    """
    sql_query = f"""
    SELECT 
        _open_tel_trace_id,
        _open_tel_span_id,
        _open_tel_parent_span_id,
        _open_tel_service_name,
        _open_tel_service_namespace,
        name,
        kind,
        start_time_unix_nano,
        end_time_unix_nano,
        status_code,
        status_message,
        scope_name
    FROM {spans_table["table_name"]}
    WHERE start_time_unix_nano >= {start_time}
        AND start_time_unix_nano <= {end_time}
        AND status_code >= {min_status_code}
    ORDER BY start_time_unix_nano
    """
    
    with postgre_engine.connect() as conn:
        result = conn.execute(text(sql_query))
        rows = [dict(row._mapping) for row in result]
    
    print(f"Retrieved error spans in time window: {len(rows)} spans with errors")
    return rows

@retry_on_falsy()
async def get_downtime_timestamps(
    trace_ids: Union[List[str], str],
    column_name: str,
    sla_trigger_table: TablePayload
) -> List[Dict[str, Any]]:
    """
    Query SLA metric trigger table to get timestamps for downtime incidents.
    
    Args:
        trace_ids: Single trace_id string or list of trace_ids
        column_name: Name of the column containing trace_ids
        sla_trigger_table: TablePayload for SLA metric trigger table
        
    Returns:
        List of dictionaries with trace_id and timestamp information
    """
    # Normalize trace_ids to list
    if isinstance(trace_ids, str):
        trace_ids = [trace_ids]
    if not trace_ids:
        return []
    
    # Build SQL query to get timestamps
    # Assuming the SLA trigger table has a time column and the trace_id column
    trace_ids_str = "', '".join(trace_ids)
    sql_query = f"""
    SELECT 
        {column_name} as trace_id,
        start_time_unix_nano as time
    FROM {sla_trigger_table["table_name"]}
    WHERE {column_name} IN ('{trace_ids_str}')
    ORDER BY start_time_unix_nano
    """
    
    with postgre_engine.connect() as conn:
        result = conn.execute(text(sql_query))
        rows = [dict(row._mapping) for row in result]
    
    return rows

@retry_on_falsy()
async def get_spans_for_trace_ids(trace_ids: Union[List[str], str], spans_table: TablePayload) -> List[Dict[str, Any]]:
    """
    Query spans for given trace IDs using SQLAlchemy, returning only schema fields.
    """
    if isinstance(trace_ids, str):
        trace_ids = [trace_ids]
    if not trace_ids:
        return []

    trace_ids_str = "', '".join(trace_ids)
    sql_query = f"""
    SELECT 
        _open_tel_trace_id,
        _open_tel_span_id,
        _open_tel_parent_span_id,
        _open_tel_service_name,
        _open_tel_service_namespace,
        name,
        kind,
        start_time_unix_nano,
        end_time_unix_nano,
        status_code,
        status_message,
        attributes,
        events,
        links,
        scope_name
    FROM {spans_table["table_name"]}
    WHERE _open_tel_trace_id IN ('{trace_ids_str}')
    ORDER BY start_time_unix_nano
    """

    with postgre_engine.connect() as conn:
        result = conn.execute(text(sql_query))
        rows = [dict(row._mapping) for row in result]

    return rows

async def get_top_latency_traces(
    start_time_utc: str, # ISO format 
    end_time_utc: str, # ISO format
    spans_table: TablePayload,
    limit: int = 5,
) -> List[Dict]:
    """
    Finds the trace IDs with the highest end-to-end latency for a given workflow
    within a specific time window.
    """
    with postgre_engine.connect() as conn:
        query = f"""
            WITH TraceDurations AS (
                SELECT
                    _open_tel_trace_id as trace_id,
                    (MAX(end_time_unix_nano) - MIN(start_time_unix_nano)) AS duration_ns,
                    MAX(CASE WHEN status_code = 'ERROR' THEN 1 ELSE 0 END) as has_error,
                    (array_agg(name ORDER BY start_time_unix_nano) FILTER (WHERE status_code = 'ERROR'))[1] as error_span,
                    (array_agg(status_message ORDER BY start_time_unix_nano) FILTER (WHERE status_code = 'ERROR'))[1] as error_message
                FROM
                    {spans_table["table_name"]}
                WHERE
                    start_time_unix_nano >= (extract(epoch from %s::timestamp) * 1e9)
                    AND end_time_unix_nano <= (extract(epoch from %s::timestamp) * 1e9)
                GROUP BY
                    _open_tel_trace_id
            )
            SELECT * FROM TraceDurations
            ORDER BY
                duration_ns DESC
            LIMIT {limit};
        """
        
        result = conn.execute(text(query), (start_time_utc, end_time_utc))
        rows = [dict(row._mapping) for row in result]
    
    return rows
