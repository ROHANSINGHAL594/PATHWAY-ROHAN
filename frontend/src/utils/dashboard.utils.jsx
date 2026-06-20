import { BaseNode } from "../components/workflow/BaseNode";

// TODO: As the nodeTypes is a in memory, it is lost when i leave the page for some time,
// hence the ui resets to simple rectangle box
export const nodeTypes = {};

// Fetch all node types from the API
export const fetchNodeTypes = async () => {
  try {
    const res = await fetch(`${import.meta.env.VITE_API_SERVER}/schema/all`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data;
  } catch (err) {
    console.error("Error fetching node types:", err);
    return null;
  }
};

// Fetch schema for a specific node
export const fetchNodeSchema = async (nodeName) => {
  try {
    const res = await fetch(
      `${import.meta.env.VITE_API_SERVER}/schema/${nodeName}`
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const schema = await res.json();
    return schema;
  } catch (err) {
    console.error(`Error fetching schema for ${nodeName}:`, err);
    return null;
  }
};

const fixPydanticSchema = (schema) => {
  // Create a deep copy to avoid mutating the original
  const newSchema = JSON.parse(JSON.stringify(schema));

  if (newSchema.properties) {
    Object.keys(newSchema.properties).forEach((key) => {
      const prop = newSchema.properties[key];

      // Check if the property uses 'anyOf', its of 2 length and one of it is null
      if (
        prop.anyOf &&
        Array.isArray(prop.anyOf) &&
        Array.from(prop.anyOf).length == 2
      ) {
        // Find the non-null option (e.g., the string, integer, or array definition)
        const realTypeOption = prop.anyOf.find((opt) => opt.type !== "null");
        // Find if there is a null option (confirming it's just an optional field)
        const hasNullOption = prop.anyOf.some((opt) => opt.type === "null");

        // If we found a real type and a null option, flatten it!
        if (realTypeOption && hasNullOption) {
          delete prop.anyOf; // Remove the dropdown trigger

          // Copy the properties from the real type (type, title, items, format, etc.)
          Object.assign(prop, realTypeOption);

          // Preserve the original title/description if the anyOf option didn't have one
          // (Pydantic usually puts title on the parent, so we are safe)

          // If the default is null, we must remove it because 'null' is not valid
          // for type 'string', 'integer', or 'array' (which we just assigned above).
          if (prop.default === null) {
            delete prop.default;
          }
        }
      }
    });
  }

  return newSchema;
};

export const generateNode = (schema, nodes) => {
  // TODO: later correct the naming of properties fields (currently code is very messy)
  const data = {
    ui: {
      label: `${schema.title || schema.node_id || "Unnamed"} Node`,
      iconUrl: "",
    },
  };

  const type = schema.properties.node_id.const;

  if (!nodeTypes[type]) addNodeType(schema);

  // TODO: Random position to better method
  const node = {
    id: `n${nodes.length + 1}`,
    schema: fixPydanticSchema(schema),
    type: type,
    position: { x: Math.random() * 300, y: Math.random() * 300 },
    node_id: schema.properties.node_id.const,
    category: schema.properties.category.const,
    data,
  };
  return node;
};

export const addNodeType = (schema) => {
  const type = schema.properties.node_id.const;

  nodeTypes[type] = (props) => {
    const { id, data, selected, onEditClick } = props;

    const nInputs = schema.properties.n_inputs?.const || 0;
    const categoryColor = hashColor(
      schema.properties.category.const == "io"
        ? schema.properties.n_inputs.const
          ? "output"
          : "input"
        : schema.properties.category.const
    );

    const statusStyles = {
      complete: {
        borderColor: "#22c55e",
        bgColor: "#ecfdf5",
        hoverBgColor: "#d1fae5",
        color: "#15803d",
      },
      incomplete: {
        borderColor: "#f97316",
        bgColor: "#fff7ed",
        hoverBgColor: "#fed7aa",
        color: "#c2410c",
      },
      unvisited: {
        borderColor: "#ef4444",
        bgColor: "#fee2e2",
        hoverBgColor: "#fecaca",
        color: "#b91c1c",
      },
      error: {
        borderColor: "#ef4444",
        bgColor: "#fee2e2",
        hoverBgColor: "#fecaca",
        color: "#b91c1c",
      },
    };

    const defaultStyles = {
      bgColor: categoryColor,
      hoverBgColor: categoryColor,
      color: categoryColor,
      borderColor: categoryColor,
    };

    const mergedStyles =
      (data?.status && statusStyles[data.status]) || defaultStyles;

    return (
      <BaseNode
        id={id}
        data={data}
        selected={selected}
        category={schema.properties.category?.const}
        nodeType={type}
        onEditClick={onEditClick}
        styles={{
          bgColor: categoryColor, // solid color
          hoverBgColor: categoryColor,
          color: categoryColor,
          borderColor: categoryColor,
        }}
        inputs={
          nInputs > 0
            ? Array.from({ length: nInputs }).map((_, i) => ({
                id: `in_${i}`,
                color: "#9E9E9E",
              }))
            : []
        }
        outputs={
          ["io", "action"].includes(schema.properties.category?.const) &&
          schema.properties.n_inputs?.const == 1
            ? []
            : [
                { id: "out", color: "#4CAF50" }, // Green
              ]
        }
        properties={data.properties}
      />
    );
  };
};

const hashColor = (str) => {
  // Category-based color mapping matching the image design
  const categoryColors = {
    // Input nodes (blue - matching image)
    "input": "#93C5FD",  // Light blue
    // Output nodes (pink - matching image)
    "output": "#FDA4AF",  // Pink
    // Table/transformation nodes (teal/green)
    "table": "#86EFAC",  // Light green
    // Windowing nodes (orange - matching image)
    "temporal": "#FDB87E",  // Orange/peach
    // Logic/control flow (purple - matching image)
    "logic": "#C4B5FD",  // Lavender purple
    // Agent nodes (purple)
    "agent": "#C4B5FD",  // Lavender purple
    // Action nodes (orange/peach)
    "action": "#FDB87E",  // Orange/peach
    // Default fallback
    "default": "#94A3B8",  // Slate grey
  };

  return categoryColors[str] || categoryColors["default"];
};
