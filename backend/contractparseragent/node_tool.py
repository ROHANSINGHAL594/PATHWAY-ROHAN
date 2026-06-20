from typing import Dict, Any, List, Optional

from lib.utils import get_node_class_map

# Mapping of all available nodes
NODE_CLASSES = get_node_class_map()

def get_node_pydantic_schema(node_name: str) -> Dict[str, Any]:
    """
    Get the EXACT Pydantic JSON schema for a node, including all $defs.
    This returns the raw schema that the LLM should match exactly.
    
    Args:
        node_name: The node_id of the node (e.g., 'kafka', 'http', 'filter', 'window_by')
    
    Returns:
        Complete Pydantic JSON schema with properties, $defs, and required fields
    """
    node_name_lower = node_name.lower()
    
    if node_name_lower not in NODE_CLASSES:
        available_nodes = ", ".join(sorted(NODE_CLASSES.keys()))
        return {
            "error": f"Node '{node_name}' not found",
            "available_nodes": available_nodes
        }
    
    node_class = NODE_CLASSES[node_name_lower]
    schema = node_class.model_json_schema()
    
    # Return the complete schema including definitions
    return {
        "node_id": node_name_lower,
        "schema": schema,
        "instructions": (
            "The 'properties' dict in your node output MUST exactly match the fields in schema['properties']. "
            "Pay special attention to nested types defined in schema['$defs'] - use the exact field names and structure. "
            "For example, window_by expects 'window' to have 'duration' and 'window_type', NOT 'length' and 'type'."
        )
    }


def get_node_parameters_concise(node_name: str) -> Dict[str, Any]:
    """
    Get node parameters in a format optimized for LLM structured output generation.
    Returns the exact structure needed to create a valid node in flowchart format.
    
    Args:
        node_name: The node_id of the node (e.g., 'kafka', 'http', 'filter', 'window_by')
    
    Returns:
        Dictionary showing the exact node structure with field descriptions
    """
    node_name_lower = node_name.lower()
    
    if node_name_lower not in NODE_CLASSES:
        available_nodes = ", ".join(sorted(NODE_CLASSES.keys()))
        return {
            "error": f"Node '{node_name}' not found",
            "available_nodes": available_nodes
        }
    
    node_class = NODE_CLASSES[node_name_lower]
    schema = node_class.model_json_schema()
    
    # Get category
    category = schema.get("properties", {}).get("category", {}).get("const", "io")
    
    # Extract fields
    required_fields = schema.get("required", [])
    all_properties = schema.get("properties", {})
    definitions = schema.get("$defs", {})
    
    # Build the node structure template
    node_structure = {
        "node_id": {
            "value": node_name_lower,
            "description": "Fixed identifier for this node type"
        },
        "category": {
            "value": category,
            "description": "Node category (io, table, temporal, agent)"
        },
        "properties": {}
    }
    
    # CRITICAL: Map Pydantic field names to flowchart JSON field names
    # input_schema (Pydantic) -> input_schema (Flowchart JSON) - NO MAPPING NEEDED
    field_name_mapping = {}
    
    # Add each field with type info and examples
    for field_name, field_info in all_properties.items():
        # Skip the structural fields we've already added
        if field_name in {"node_id", "category", "n_inputs"}:
            continue
        
        # Skip fields that are marked as SkipJsonSchema (like table_schema in Pydantic model)
        # These are internal fields that don't appear in JSON
        if field_name == "table_schema":
            continue
        
        # Map to flowchart field name if needed
        output_field_name = field_name_mapping.get(field_name, field_name)
        
        is_required = field_name in required_fields
        
        # Build field specification
        field_spec = {
            "required": is_required,
            "type": _get_simple_type(field_info, definitions),
        }
        
        # Add description if available
        if field_info.get("description"):
            field_spec["description"] = field_info["description"]
        
        # Add constraints
        if "enum" in field_info:
            field_spec["allowed_values"] = field_info["enum"]
            field_spec["example"] = field_info["enum"][0]
        elif "const" in field_info:
            field_spec["value"] = field_info["const"]
        elif "default" in field_info:
            field_spec["default"] = field_info["default"]
        
        # Add example value based on type
        if "example" not in field_spec and "value" not in field_spec:
            # Special handling for input_schema
            if output_field_name == "input_schema":
                field_spec["example"] = [
                    {"key": "column1", "value": "str"},
                    {"key": "column2", "value": "int"},
                    {"key": "timestamp", "value": "int"}
                ]
            else:
                field_spec["example"] = _generate_example_value(field_info, definitions)
        
        # Use the mapped field name in output
        node_structure["properties"][output_field_name] = field_spec
    
    return node_structure


def _get_simple_type(field_info: Dict[str, Any], definitions: Dict[str, Any]) -> str:
    """Extract a simple, readable type description."""
    if "const" in field_info:
        return f"literal[{field_info['const']}]"
    elif "enum" in field_info:
        vals = field_info["enum"][:3]
        return f"enum[{', '.join(map(str, vals))}{'...' if len(field_info['enum']) > 3 else ''}]"
    elif "$ref" in field_info:
        ref_name = field_info["$ref"].split("/")[-1]
        # Try to expand simple refs
        if ref_name in definitions:
            ref_def = definitions[ref_name]
            if "properties" in ref_def:
                props = list(ref_def["properties"].keys())[:3]
                return f"dict[{', '.join(props)}{'...' if len(ref_def['properties']) > 3 else ''}]"
        return ref_name
    elif "anyOf" in field_info:
        types = []
        for option in field_info["anyOf"]:
            if "type" in option:
                types.append(option["type"])
            elif "$ref" in option:
                types.append(option["$ref"].split("/")[-1])
        return " | ".join(types) if types else "union"
    elif field_info.get("type") == "array":
        items = field_info.get("items", {})
        item_type = _get_simple_type(items, definitions)
        return f"list[{item_type}]"
    elif field_info.get("type") == "object":
        if "properties" in field_info:
            props = list(field_info["properties"].keys())[:2]
            return f"dict[{', '.join(props)}...]"
        return "dict"
    else:
        return field_info.get("type", "any")


def _generate_example_value(field_info: Dict[str, Any], definitions: Dict[str, Any]) -> Any:
    """Generate an example value for a field."""
    if "enum" in field_info:
        return field_info["enum"][0]
    elif "const" in field_info:
        return field_info["const"]
    elif "default" in field_info:
        return field_info["default"]
    
    field_type = field_info.get("type")
    
    if field_type == "string":
        return "<value>"
    elif field_type == "integer":
        return 0
    elif field_type == "number":
        return 0.0
    elif field_type == "boolean":
        return False
    elif field_type == "array":
        items = field_info.get("items", {})
        if "$ref" in items:
            ref_name = items["$ref"].split("/")[-1]
            if ref_name in definitions:
                return [_create_example_from_ref(ref_name, definitions)]
        return []
    elif field_type == "object":
        if "$ref" in field_info:
            ref_name = field_info["$ref"].split("/")[-1]
            return _create_example_from_ref(ref_name, definitions)
        return {}
    elif "anyOf" in field_info:
        # Use first option
        for option in field_info["anyOf"]:
            if option.get("type") == "null":
                continue
            return _generate_example_value(option, definitions)
    
    return None


def _create_example_from_ref(ref_name: str, definitions: Dict[str, Any]) -> Dict[str, Any]:
    """Create an example object from a $ref definition."""
    if ref_name not in definitions:
        return {}
    
    ref_def = definitions[ref_name]
    example = {}
    
    if "properties" in ref_def:
        for prop_name, prop_info in ref_def["properties"].items():
            if "enum" in prop_info:
                example[prop_name] = prop_info["enum"][0]
            elif "const" in prop_info:
                example[prop_name] = prop_info["const"]
            elif prop_info.get("type") == "string":
                example[prop_name] = f"<{prop_name}>"
            elif prop_info.get("type") in ["integer", "number"]:
                example[prop_name] = 0
    
    return example