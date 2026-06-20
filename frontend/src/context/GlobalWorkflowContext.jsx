import { createContext, useContext, useState } from "react";
import { useReactFlow } from "@xyflow/react";

const GlobalWorkflowContext = createContext();

export function useGlobalWorkflow() {
  return useContext(GlobalWorkflowContext);
}

export const GlobalWorkflowProvider = ({ children }) => {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [id, setId] = useState(null);
  const [versionId, setVersionId] = useState(null);
  const [workflowData, setWorkflowData] = useState({})
  const [status, setStatus] = useState("Stopped");
  const [rfInstance, setRfInstance] = useState(null);
  // Full pipeline data (preserves additional fields like 'agents' that React Flow doesn't track)
  const [fullPipeline, setFullPipeline] = useState(null);
  const { setViewport } = useReactFlow();

  const value = {
    // Workflow state
    nodes,
    setNodes,
    edges,
    setEdges,
    id,
    setId,
    versionId,
    setVersionId,
    status,
    setStatus,
    rfInstance,
    setRfInstance,
    setViewport,
    workflowData,
    setWorkflowData,
    // Full pipeline (for preserving extra fields like 'agents')
    fullPipeline,
    setFullPipeline
  };

  return (
    <GlobalWorkflowContext.Provider value={value}>
      {children}
    </GlobalWorkflowContext.Provider>
  );
};





