
import "@xyflow/react/dist/style.css";
import { Box, useTheme } from "@mui/material";
import { useLocation, useNavigate } from "react-router-dom";
import WorkflowHeader from "./developerDashboardProject/WorkflowHeader";
import WorkflowWorkspace from "./developerDashboardProject/WorkflowWorkspace";
import useWorkflowState from "./developerDashboardProject/useWorkflowState";
import { nodeTypes } from "../utils/dashboard.utils";

export const DeveloperDashboardProject = () => {
  const theme = useTheme();
  const { state } = useLocation();
  const navigate = useNavigate();

  const {
    workflowName,
    nodes,
    edges,
    selectedNode,
    selectedNodeId,
    propertyDrafts,
    primaryActionLabel,
    snackbar,
    setSelectedNodeId,
    handleNodesChange,
    handleEdgesChange,
    handleConnect,
    handleNodeClick,
    handlePropertyChange,
    handleCancel,
    handleSaveNode,
    handleCloseSnackbar,
  } = useWorkflowState({
    blueprint: state?.workflowBlueprint,
    navigate,
  });

  return (
    <Box
      sx={{
        bgcolor: theme.palette.background.default,
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <WorkflowHeader
        workflowName={workflowName}
        nodes={nodes}
        selectedNodeId={selectedNodeId}
        onSelectNode={setSelectedNodeId}
      />

      <WorkflowWorkspace
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        selectedNode={selectedNode}
        propertyDrafts={propertyDrafts}
        primaryActionLabel={primaryActionLabel}
        snackbar={snackbar}
        onPropertyChange={handlePropertyChange}
        onCancel={handleCancel}
        onSave={handleSaveNode}
        onNodesChange={handleNodesChange}
        onEdgesChange={handleEdgesChange}
        onConnect={handleConnect}
        onNodeClick={handleNodeClick}
        onCloseSnackbar={handleCloseSnackbar}
      />
    </Box>
  );
};

export default DeveloperDashboardProject;
