import { addNodeType, fetchNodeSchema } from "./dashboard.utils";

//Create a pipeline first to avoid the error of using a random id
// TODO: a user should only first create a piepline thn use these fucntion, useing currentPipelineId or version id uses random and undefined values
//----------------------- Create Pipeline--------------------------------//

const create_pipeline = async (
  name,
  setCurrentPipelineId,
  setCurrentVersionId,
  setError,
  setLoading
) => {
  setLoading(true);
  try {
    const response = await fetch(
      `${
        import.meta.env.VITE_API_SERVER
      }/version/create_pipeline?name=${encodeURIComponent(name)}`,
      {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
      }
    );

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(
        `Failed to create pipeline: ${errText || response.status}`
      );
    }

    const data = await response.json();
    if (data.id) {
      setCurrentPipelineId(data.id);
      if (data.current_version_id) {
        setCurrentVersionId(data.current_version_id);
      } else if (data.version_id) {
        setCurrentVersionId(data.version_id);
      }
    }
  } catch (err) {
    setError(err.message);
  } finally {
    setLoading(false);
  }
};

//----------------------- Save pipeline and Drafts---------------------------------------//

const savePipelineAPI = async (
  rfInstance,
  currentPipelineId,
  setCurrentPipelineId,
  currentVersionId,
  setCurrentVersionId,
  setError,
  setLoading
) => {
  if (!(currentPipelineId && currentVersionId && rfInstance)) {
    return;
  }
  try {
    setLoading(true);
    const flow = rfInstance.toObject();
    const response = await fetch(
      `${import.meta.env.VITE_API_SERVER}/version/save`,
      {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          version_updated_at: new Date().toISOString(),
          version_description: "",
          current_version_id: currentVersionId,
          workflow_id: currentPipelineId,
          pipeline: flow,
        }),
      }
    );

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Failed to save pipeline: ${errText || response.status}`);
    }
    const data = await response.json();
    if (data.pipeline_id) {
      setCurrentPipelineId(data.pipeline_id);
    }
    if (data.version_id) {
      setCurrentVersionId(data.version_id);
    }
  } catch (err) {
    console.error("Save failed:", err);
    if (setError) {
      setError(err.message);
    }
  } finally {
    setLoading(false);
  }
};

const saveDraftsAPI = async (
  version_id,
  rfInstance,
  setCurrentVersionId,
  pipeline_id,
  setLoading,
  setError,
  description = "",
  existingPipeline = null // Optional: existing pipeline to preserve additional fields like 'agents'
) => {
  if (!version_id || !pipeline_id || !rfInstance) {
    if (setError)
      setError(
        "Can't save draft: missing version_id, pipeline_id, or rfInstance"
      );
    if (setLoading) setLoading(false);
    return null;
  }

  if (setLoading) setLoading(true);
  try {
    const flow = rfInstance.toObject();
    
    // Merge flow data with existing pipeline to preserve additional fields (e.g., agents)
    const pipelineToSave = existingPipeline 
      ? { ...existingPipeline, ...flow }  // Preserve existingPipeline fields, but override nodes/edges/viewport
      : flow;
    
    const response = await fetch(
      `${import.meta.env.VITE_API_SERVER}/version/save_draft`,
      {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          version_id: version_id,
          pipeline_id: pipeline_id,
          version_description: description || "",
          pipeline: pipelineToSave,
        }),
      }
    );
    if (!response.ok) {
      throw new Error(`Failed to save draft: ${response.status}`);
    }

    const data = await response.json();

    if (data.version_id && setCurrentVersionId) {
      setCurrentVersionId(data.version_id);
    }
    return data;
  } catch (err) {
    if (setError) setError(err.message);
    return null;
  } finally {
    if (setLoading) setLoading(false);
  }
};

//-------------------------------- Retrieve Pipeline at a version---------------------------------//

async function fetchAndSetPipeline(pipeline_id, version_id, setters) {
  const {
    setCurrentPipelineId,
    setCurrentVersionId,
    setError,
    setLoading,
    setCurrentEdges,
    setCurrentNodes,
    setViewport,
    setCurrentPipelineStatus,
    setContainerId,
    setFullPipeline, // Optional: for storing full pipeline data (including agents, etc.)
  } = setters;

  if (!pipeline_id || !version_id) {
    return;
  }

  setLoading(true);
  const res = await fetch(
    `${import.meta.env.VITE_API_SERVER}/version/retrieve_pipeline`,
    {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        workflow_id: pipeline_id,
        version_id: version_id,
      }),
    }
  );

  if (!res.ok) {
    throw new Error("Unable to fetch pipeline");
  }
  const result = await res.json();
  const workflow = result["workflow"];
  const version = result["version"];

  if (!workflow || !version) {
    setLoading(false);
    return null;
  }

  // Extract pipeline data from version - the version has a 'pipeline' key containing the actual flow data
  const pipelineData = version?.pipeline;

  // Get version_id from version object
  if (version) {
    const vid = version["_id"] || version["version_id"];
    if (vid) {
      setCurrentVersionId(String(vid));
    }
  }

  // Get pipeline_id from workflow object
  if (workflow) {
    const pid = workflow["_id"] || workflow["pipeline_id"];
    if (pid) {
      setCurrentPipelineId(String(pid));
    }
    if (workflow["status"]) {
      setCurrentPipelineStatus(workflow["status"]);
    }
    if (workflow["container_id"]) {
      setContainerId(workflow["container_id"]);
    }
  }

  if (pipelineData && typeof pipelineData === "object") {
    const nodes = pipelineData["nodes"] || [];
    const edges = pipelineData["edges"] || [];
    const viewport = pipelineData["viewport"];

    console.log("Loading pipeline data:", {
      nodesCount: nodes.length,
      edgesCount: edges.length,
      viewport,
      sampleNode: nodes[0],
    });

    // Process nodes first
    if (nodes.length > 0) {
      await add_to_node_types(nodes);

      // Validate and ensure nodes have required properties
      const validatedNodes = nodes.map((node, index) => {
        // Ensure node has required properties
        if (!node.id) {
          console.warn("Node missing id:", node);
          node.id = node.id || `node-${index}`;
        }

        // Ensure position exists
        if (
          !node.position ||
          typeof node.position.x !== "number" ||
          typeof node.position.y !== "number"
        ) {
          console.warn("Node missing or invalid position:", node);
          node.position = node.position || { x: index * 250, y: index * 150 };
        }

        // Ensure type exists - use node_id if type is missing
        if (!node.type && node.node_id) {
          console.log("Setting node type from node_id:", node.node_id);
          node.type = node.node_id;
        } else if (!node.type) {
          console.warn("Node missing both type and node_id:", node);
          node.type = "default";
        }

        // Ensure data exists
        if (!node.data) {
          node.data = {};
        }

        return node;
      });

      console.log("Validated nodes:", validatedNodes);
      setCurrentNodes(validatedNodes);
    } else {
      setCurrentNodes([]);
    }

    // Set edges
    console.log("Setting edges:", edges);
    setCurrentEdges(edges || []);

    // Set viewport if available (only if setViewport is provided)
    if (setViewport) {
      if (viewport) {
        setViewport(viewport);
      } else {
        // Default viewport if not provided
        setViewport({ x: 0, y: 0, zoom: 1 });
      }
    }
    
    // Store full pipeline data (preserves additional fields like 'agents')
    if (setFullPipeline) {
      setFullPipeline(pipelineData);
    }
  } else {
    console.warn("No pipeline data found in version:", {
      hasVersion: !!version,
      hasPipeline: !!version?.pipeline,
      pipelineDataType: typeof version?.pipeline,
    });
    
    // Clear full pipeline if no data
    if (setFullPipeline) {
      setFullPipeline(null);
    }
  }

  setLoading(false);
  return result;
}

//------------------------------Delete Pipeline and Drafts-----------------------------------//

async function deletePipeline(
  pipeline_id,
  currentPipelineId,
  setCurrentPipelineId,
  setCurrentVersionId,
  setContainerId,
  setAgentContainer,
  setCurrentEdges,
  setCurrentNodes,
  setCurrentPipelineStatus,
  setLoading,
  setError
) {
  setLoading(true);
  try {
    if (!pipeline_id) {
      setError("Cannot delete pipeline - ID is required");
      return null;
    }
    const res = await fetch(
      `${
        import.meta.env.VITE_API_SERVER
      }/version/delete_pipeline?workflow_id=${pipeline_id}`,
      {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
      }
    );

    if (!res.ok) {
      throw new Error(`Unable to delete file, status: ${res.status}`);
    }

    const result = await res.json();
    if (pipeline_id === currentPipelineId) {
      setCurrentPipelineId(null);
      setCurrentEdges([]);
      setCurrentNodes([]);
      setCurrentVersionId(null);
      setCurrentPipelineStatus(null);
    }
    setLoading(false);
    setContainerId(null);
    setAgentContainer(null);
  } catch (err) {
    console.error("delete failed:", err);
    setError(err.message);
  } finally {
    setLoading(false);
  }
}

async function deleteDrafts(
  pipeline_id,
  currentPipelineId,
  setCurrentVersionId,
  setCurrentEdges,
  setCurrentNodes,
  setCurrentPipelineStatus,
  setLoading,
  setError
) {
  setLoading(true);
  try {
    if (!pipeline_id) {
      throw new Error("Pipeline ID is required");
    }
    const res = await fetch(
      `${
        import.meta.env.VITE_API_SERVER
      }/version/delete_draft?workflow_id=${pipeline_id}`,
      {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
      }
    );

    if (res.ok) {
      if (pipeline_id === currentPipelineId) {
        const result = await res.json();
        const version = result["version"];

        if (version) {
          const pipelineData = version?.pipeline;

          if (result["version_id"]) {
            setCurrentVersionId(String(result["version_id"]));
          }

          if (pipelineData && typeof pipelineData === "object") {
            await add_to_node_types(pipelineData?.nodes || []);
            setCurrentNodes(pipelineData["nodes"] || []);
            setCurrentEdges(pipelineData["edges"] || []);
          }
        }

        setCurrentPipelineStatus(null);
      }
      setLoading(false);
    } else {
      const errText = await res.text();
      throw new Error(`Failed to delete draft: ${errText || res.status}`);
    }
  } catch (err) {
    console.error("delete failed:", err);
    setError(err.message);
  } finally {
    setLoading(false);
  }
}

//--------------------------pipeline docker APIs----------------------------------------------//

async function toggleStatus(id, currentStatus) {
  const endpoint = currentStatus === "Running" ? "stop" : "run";
  const res = await fetch(
    `${import.meta.env.VITE_API_SERVER}/pipelines/${endpoint}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ pipeline_id: id }),
    }
  );
  if (!res.ok) {
    throw new Error(`Unable to toggle status, status: ${res.status}`);
  }
  return await res.json();
}

async function spinupPipeline(id) {
  const res = await fetch(
    `${import.meta.env.VITE_API_SERVER}/pipelines/spinup`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ pipeline_id: id }),
    }
  );
  if (!res.ok) {
    throw new Error(`Unable to spin up pipeline, status: ${res.status}`);
  }
  return await res.json();
}

async function spindownPipeline(id) {
  const res = await fetch(
    `${import.meta.env.VITE_API_SERVER}/pipelines/spindown`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ pipeline_id: id }),
    }
  );
  if (!res.ok) {
    throw new Error(`Unable to spin down pipeline, status: ${res.status}`);
  }
  return await res.json();
}

async function add_to_node_types(nodes = []) {
  if (!Array.isArray(nodes) || !nodes.length) return;

  const uniqueNodeIds = Array.from(
    new Set(nodes.map((node) => node?.node_id).filter(Boolean))
  );

  await Promise.all(
    uniqueNodeIds.map(async (nodeId) => {
      const schema = await fetchNodeSchema(nodeId);
      if (schema?.properties?.node_id?.const) {
        addNodeType(schema);
      }
    })
  );
}

/**
 * Fetch pipeline details including creation time and alerts
 * @param {string|Object} pipelineId - The pipeline ID (string or object with id/_id property)
 * @returns {Promise<Object>} Pipeline details with created_at and alerts
 */
async function fetchPipelineDetails(pipelineId) {
  // Ensure pipelineId is a string - handle both string and object cases
  let idString;
  if (typeof pipelineId === "string") {
    idString = pipelineId;
  } else if (pipelineId && typeof pipelineId === "object") {
    // If it's an object, try to extract the ID
    idString = String(pipelineId.id || pipelineId._id || pipelineId);
  } else {
    idString = String(pipelineId || "");
  }

  // Validate that we have a valid ID string (not empty and not '[object Object]')
  if (!idString || idString === "[object Object]" || idString.trim() === "") {
    throw new Error(`Invalid pipeline ID: ${pipelineId}`);
  }

  const response = await fetch(
    `${import.meta.env.VITE_API_SERVER}/version/pipeline/${idString}/details`,
    {
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
    }
  );

  if (!response.ok) {
    throw new Error("Failed to fetch pipeline details");
  }

  return await response.json();
}

export {
  savePipelineAPI,
  fetchAndSetPipeline,
  toggleStatus,
  spinupPipeline,
  spindownPipeline,
  create_pipeline,
  saveDraftsAPI,
  deleteDrafts,
  deletePipeline,
  fetchPipelineDetails,
  add_to_node_types,
};

/**
                 <Button
                variant="outlined"
                onClick={() =>
                  create_pipeline(
                    setCurrentPipelineId,
                    setCurrentVersionId,
                    setError,
                    setLoading,
                )}
                disabled={loading}
              >
                Create Pipeline
              </Button>
              <Button
                variant="outlined"
                onClick={() =>
                  saveDraftsAPI(
                  currentVersionId,
                  rfInstance,
                  setCurrentVersionId,
                  currentPipelineId,
                  setLoading,
                  setError,
                )}
                disabled={loading}
              >
                Save Draft
              </Button>
              <Button
                variant="outlined"
                onClick={() => fetchAndSetPipeline(
                  currentPipelineId, currentVersionId,{
                  setCurrentPipelineId,
                  setCurrentVersionId,
                  setError,
                  setLoading,
                  setCurrentEdges,
                  setCurrentNodes,
                  setViewport,
                  setCurrentPipelineStatus,
                  setContainerId,
                })}
                disabled={loading}
              >
                Fetch
              </Button>
              <Button
                variant="outlined"
                onClick={() =>
                  deleteDrafts(
                  currentPipelineId,
                  currentPipelineId,
                  setCurrentVersionId,
                  setCurrentEdges,
                  setCurrentNodes,
                  setCurrentPipelineStatus,
                  setLoading,
                  setError
                )}
                disabled={loading}
              >
                Delete Draft
              </Button>

 */
