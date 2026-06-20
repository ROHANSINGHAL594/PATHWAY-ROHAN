const stringifyProperties = (properties = []) =>
  properties.map((prop) => {
    if (prop.type === "json") {
      if (!prop.value) return { ...prop, value: "" };
      if (typeof prop.value === "string") return { ...prop };
      return { ...prop, value: JSON.stringify(prop.value, null, 2) };
    }
    return { ...prop, value: prop.value ?? "" };
  });

const parseProperties = (properties = []) =>
  properties.map((prop) => {
    if (prop.type === "json") {
      if (!prop.value || !prop.value.toString().trim()) {
        throw new Error(`Property "${prop.label}" requires valid JSON.`);
      }
      return { ...prop, value: JSON.parse(prop.value) };
    }
    return { ...prop, value: prop.value };
  });

const computePropertyStatus = (properties = []) => {
  if (!properties.length) return "incomplete";
  const hasEmpty = properties.some((prop) => {
    if (prop.type === "json") {
      return typeof prop.value === "string" ? !prop.value.trim() : !prop.value;
    }
    return `${prop.value ?? ""}`.trim() === "";
  });
  return hasEmpty ? "incomplete" : "complete";
};

const buildSchemaFromNode = (node, inboundEdgeCount) => {
  const baseProperties = {
    node_id: { const: node.node_id },
    category: { const: node.category },
    n_inputs: { const: inboundEdgeCount },
  };

  node.data?.properties?.forEach((prop) => {
    baseProperties[prop.label] = {
      default: prop.value,
      type: prop.type,
    };
  });

  return {
    title: node.data?.ui?.label ?? node.id,
    node_id: node.node_id,
    properties: baseProperties,
  };
};

const hydrateNodes = (blueprint, generateNode) => {

  const inboundCount = blueprint.edges.reduce((acc, edge) => {
    acc[edge.target] = (acc[edge.target] || 0) + 1;
    return acc;
  }, {});

  const nodes = [];
  blueprint.nodes.forEach((rawNode) => {
    const schema = buildSchemaFromNode(rawNode, inboundCount[rawNode.id] || 0);
    const generated = generateNode(schema, nodes);

    nodes.push({
      ...generated,
      id: rawNode.id,
      position: rawNode.position || generated.position,
      data: {
        ...generated.data,
        ui: {
          ...(generated.data?.ui || {}),
          label: rawNode.data?.ui?.label ?? generated.data?.ui?.label,
          iconUrl: rawNode.data?.ui?.iconUrl ?? generated.data?.ui?.iconUrl,
        },
        properties: rawNode.data?.properties ?? [],
        status: "unvisited",
        visited: false,
        hasSaved: false,
      },
      category: rawNode.category,
      node_id: rawNode.node_id,
    });
  });

  return nodes;
};

const hydrateEdges = (edges = []) =>
  edges.map((edge) => ({ animated: false, type: "smoothstep", ...edge }));

const findNextIncompleteNodeId = (nodes, currentNodeId) => {
  if (!nodes.length) return null;

  const ordered = [...nodes].sort((a, b) => a.id.localeCompare(b.id));
  const currentIdx = currentNodeId ? ordered.findIndex((n) => n.id === currentNodeId) : -1;

  for (let i = currentIdx + 1; i < ordered.length; i++) {
    if (ordered[i].data?.status !== "complete") return ordered[i].id;
  }

  for (let i = 0; i <= currentIdx; i++) {
    if (ordered[i].data?.status !== "complete") return ordered[i].id;
  }

  return null;
};

export {
  stringifyProperties,
  parseProperties,
  computePropertyStatus,
  hydrateNodes,
  hydrateEdges,
  findNextIncompleteNodeId,
};

