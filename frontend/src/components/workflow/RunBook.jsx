import { useState, useEffect, useRef, useCallback } from "react";
import {
  Dialog,
  DialogContent,
  Box,
  Typography,
  IconButton,
  Button,
  Switch,
  Checkbox,
  FormControlLabel,
  TextField,
  Collapse,
  Tabs,
  Tab,
  Card,
  CardContent,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Divider,
  ButtonGroup,
  Chip,
  CircularProgress,
  Alert,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import DeleteIcon from "@mui/icons-material/Delete";
import AddIcon from "@mui/icons-material/Add";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import RefreshIcon from "@mui/icons-material/Refresh";
import { useGlobalWorkflow } from "../../context/GlobalWorkflowContext";

const RunBook = ({ open, onClose, formData = {}, onSave }) => {
  const [activeTab, setActiveTab] = useState(0);
  const { id: currentPipelineId } = useGlobalWorkflow();
  
  // Actions fetched from API (agentic container)
  const [allActionsForDropdown, setAllActionsForDropdown] = useState([]);
  const [actionsLoading, setActionsLoading] = useState(false);
  const [actionsError, setActionsError] = useState(null);
  
  // Error catalog (error-registry) fetched from API (pipeline container)
  const [errorCatalog, setErrorCatalog] = useState([]);
  const [errorCatalogLoading, setErrorCatalogLoading] = useState(false);
  const [errorCatalogError, setErrorCatalogError] = useState(null);
  
  const [name, setName] = useState(formData.name || "");
  const [userConfirmation, setUserConfirmation] = useState(
    formData.userConfirmation || false
  );
  const [errorDescription, setErrorDescription] = useState(
    formData.errorDescription || ""
  );
  const [actionDiscoveryMode, setActionDiscoveryMode] = useState(formData.actionDiscoveryMode || "");

  // Manual action form state
  const [actionId, setActionId] = useState(formData.actionId || "");
  const [serviceName, setServiceName] = useState(formData.serviceName || "");
  const [executionMethod, setExecutionMethod] = useState(formData.executionMethod || "");
  const [riskLevel, setRiskLevel] = useState(formData.riskLevel || "");
  const [requiresApproval, setRequiresApproval] = useState(formData.requiresApproval || false);
  const [secrets, setSecrets] = useState(
    formData.secrets && typeof formData.secrets === 'object'
      ? Object.entries(formData.secrets).map(([key, value]) => ({ key, value }))
      : [{ key: "", value: "" }]
  );
  const [parameters, setParameters] = useState(
    formData.parameters && typeof formData.parameters === 'object' 
      ? Object.entries(formData.parameters).map(([key, value]) => ({ key, value }))
      : [{ key: "", value: "" }]
  );

  // Swagger/OpenAPI form state
  const [swaggerUrl, setSwaggerUrl] = useState(formData.swaggerUrl || "");
  const [swaggerFile, setSwaggerFile] = useState(null);
  const [swaggerFileName, setSwaggerFileName] = useState("");
  const [swaggerServiceName, setSwaggerServiceName] = useState(formData.swaggerServiceName || "");

  // Script Discovery form state
  const [scriptPath, setScriptPath] = useState(formData.scriptPath || "");
  const [scriptServiceName, setScriptServiceName] = useState(formData.scriptServiceName || "");
  const [accessViaSSH, setAccessViaSSH] = useState(formData.accessViaSSH || false);
  const [sshHost, setSshHost] = useState(formData.sshHost || "");
  const [sshUsername, setSshUsername] = useState(formData.sshUsername || "");
  const [sshPassword, setSshPassword] = useState(formData.sshPassword || "");
  const [sshKeyPath, setSshKeyPath] = useState(formData.sshKeyPath || "");
  const [privateKeyPassphrase, setPrivateKeyPassphrase] = useState(formData.privateKeyPassphrase || "");
  const [sshPort, setSshPort] = useState(formData.sshPort || "");

  // Documentation Discovery form state
  const [documentation, setDocumentation] = useState(formData.documentation || "");
  const [documentationFile, setDocumentationFile] = useState(null);
  const [documentationFileName, setDocumentationFileName] = useState("");

  // Run Book form state
  const [runBookName, setRunBookName] = useState(formData.runBookName || "");
  const [runBookErrorDescription, setRunBookErrorDescription] = useState(
    formData.runBookErrorDescription || ""
  );
  const [actions, setActions] = useState(formData.actions || [""]);

  // Save status states
  const [saveLoading, setSaveLoading] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Track previous formData to prevent unnecessary updates
  const prevFormDataRef = useRef(null);

  // Update local state when formData prop changes (only if values actually changed)
  useEffect(() => {
    // Skip if formData hasn't changed or is the same reference
    if (!formData || prevFormDataRef.current === formData) {
      return;
    }

    // Check if any values actually changed
    const prevData = prevFormDataRef.current;
    const hasChanged =
      !prevData ||
      prevData.name !== formData.name ||
      prevData.userConfirmation !== formData.userConfirmation ||
      prevData.errorDescription !== formData.errorDescription ||
      prevData.correctiveMeasures !== formData.correctiveMeasures ||
      prevData.correctiveMeasureMode !== formData.correctiveMeasureMode ||
      prevData.apiKey !== formData.apiKey ||
      prevData.apiValue !== formData.apiValue ||
      prevData.runBookErrorDescription !== formData.runBookErrorDescription ||
      JSON.stringify(prevData.actions) !== JSON.stringify(formData.actions);

    if (hasChanged) {
      setName(formData.name || "");
      setUserConfirmation(formData.userConfirmation || false);
      setErrorDescription(formData.errorDescription || "");
      setRunBookName(formData.runBookName || "");
      setRunBookErrorDescription(formData.runBookErrorDescription || "");
      setActions(formData.actions || [""]);
      setActionDiscoveryMode(formData.actionDiscoveryMode || "");
      setActionId(formData.actionId || "");
      setServiceName(formData.serviceName || "");
      setExecutionMethod(formData.executionMethod || "");
      setRiskLevel(formData.riskLevel || "");
      setRequiresApproval(formData.requiresApproval || false);
      setSecrets(
        formData.secrets && typeof formData.secrets === 'object'
          ? Object.entries(formData.secrets).map(([key, value]) => ({ key, value }))
          : [{ key: "", value: "" }]
      );
      setParameters(
        formData.parameters && typeof formData.parameters === 'object'
          ? Object.entries(formData.parameters).map(([key, value]) => ({ key, value }))
          : [{ key: "", value: "" }]
      );
      setSwaggerUrl(formData.swaggerUrl || "");
      setSwaggerFile(null);
      setSwaggerFileName("");
      setSwaggerServiceName(formData.swaggerServiceName || "");
      setScriptPath(formData.scriptPath || "");
      setScriptServiceName(formData.scriptServiceName || "");
      setAccessViaSSH(formData.accessViaSSH || false);
      setSshHost(formData.sshHost || "");
      setSshUsername(formData.sshUsername || "");
      setSshPassword(formData.sshPassword || "");
      setSshKeyPath(formData.sshKeyPath || "");
      setPrivateKeyPassphrase(formData.privateKeyPassphrase || "");
      setSshPort(formData.sshPort || "");
      setDocumentation(formData.documentation || "");
      setDocumentationFile(null);
      setDocumentationFileName("");
    }
  }, [open]);

  // Fetch actions from agentic container API
  const fetchActions = useCallback(async () => {
    if (!currentPipelineId) {
      console.log("No pipeline ID, skipping actions fetch");
      setActionsError("No pipeline selected. Please select a workflow first.");
      return;
    }
    
    setActionsLoading(true);
    setActionsError(null);
    
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_SERVER}/agentic/${currentPipelineId}/runbook/actions`,
        {
          method: "GET",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorDetail = errorData.detail || `HTTP ${response.status}`;
        if (response.status === 404) {
          throw new Error("Workflow not found or container not running. Please spin up the workflow first.");
        } else if (response.status === 503) {
          throw new Error("Runbook registry not initialized. The container may still be starting up.");
        }
        throw new Error(`Failed to fetch actions: ${errorDetail}`);
      }

      const result = await response.json();
      console.log("Fetched actions:", result);
      setAllActionsForDropdown(result.actions || []);
    } catch (error) {
      console.error("Error fetching actions:", error);
      setActionsError(error.message);
      setAllActionsForDropdown([]);
    } finally {
      setActionsLoading(false);
    }
  }, [currentPipelineId]);

  // Fetch error catalog from pipeline container API
  const fetchErrorCatalog = useCallback(async () => {
    if (!currentPipelineId) {
      console.log("No pipeline ID, skipping error catalog fetch");
      setErrorCatalogError("No pipeline selected. Please select a workflow first.");
      return;
    }
    
    setErrorCatalogLoading(true);
    setErrorCatalogError(null);
    
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_SERVER}/action/${currentPipelineId}/error-registry/mappings`,
        {
          method: "GET",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorDetail = errorData.detail || `HTTP ${response.status}`;
        if (response.status === 404) {
          throw new Error("Workflow not found or container not running. Please spin up the workflow first.");
        } else if (response.status === 503) {
          throw new Error("Error registry not initialized. The container may still be starting up.");
        }
        throw new Error(`Failed to fetch error catalog: ${errorDetail}`);
      }

      const result = await response.json();
      console.log("Fetched error catalog:", result);
      setErrorCatalog(result || []);
    } catch (error) {
      console.error("Error fetching error catalog:", error);
      setErrorCatalogError(error.message);
      setErrorCatalog([]);
    } finally {
      setErrorCatalogLoading(false);
    }
  }, [currentPipelineId]);

  // Fetch data when dialog opens or pipeline changes
  useEffect(() => {
    if (open && currentPipelineId) {
      fetchActions();
      fetchErrorCatalog();
    }
  }, [open, currentPipelineId, fetchActions, fetchErrorCatalog]);

  const handleSave = async () => {
    // Handle Run Book tab (activeTab === 0) - Save to Error Registry
    if (activeTab === 0) {
      const runBookData = {
        error: runBookErrorDescription,
        actions: actions.filter(action => action.trim() !== ""),
        description: runBookName,
        pipeline_id: currentPipelineId || null,
        updated_at: new Date().toISOString(),
      };

      console.log("Run Book Data:", JSON.stringify(runBookData, null, 2));
      
      if (!currentPipelineId) {
        console.error("Pipeline ID is required to save runbook");
        setSaveError("No pipeline selected. Please select a workflow first.");
        return;
      }

      // Validate required fields
      if (!runBookErrorDescription.trim()) {
        setSaveError("Error description is required.");
        return;
      }
      
      const validActions = actions.filter(action => action.trim() !== "");
      if (validActions.length === 0) {
        setSaveError("At least one action is required.");
        return;
      }

      setSaveLoading(true);
      setSaveError(null);
      setSaveSuccess(false);
      
      try {
        // Use the error-registry endpoint to add the error mapping
        const url = `${import.meta.env.VITE_API_SERVER}/action/${currentPipelineId}/error-registry/mappings`;
        console.log("Saving Run Book to:", url);
        
        const response = await fetch(url, {
          method: "POST",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            error: runBookErrorDescription,
            actions: validActions,
            description: runBookName
          }),
        });

        if (!response.ok) {
          let errorMessage = `Failed to save run book (Status: ${response.status})`;
          try {
            const errorData = await response.json();
            if (errorData.detail) {
              errorMessage = errorData.detail;
            }
          } catch (e) {
            // Try text if JSON fails
            try {
              const errorText = await response.text();
              if (errorText) {
                errorMessage = errorText;
              }
            } catch (textErr) { /* ignore */ }
          }
          
          // Map common error codes to user-friendly messages
          if (response.status === 404) {
            errorMessage = "Workflow not found or containers not running. Please spin up the workflow first.";
          } else if (response.status === 503) {
            errorMessage = "Error registry not initialized. The container may still be starting.";
          } else if (response.status === 403) {
            errorMessage = "You don't have permission to modify this workflow.";
          }
          throw new Error(errorMessage);
        }

        const result = await response.json();
        console.log("Run book saved successfully:", result);

        // Refresh the error catalog after successful save
        await fetchErrorCatalog();

        setSaveSuccess(true);
        // Clear success message after 3 seconds
        setTimeout(() => setSaveSuccess(false), 3000);

        if (onSave) {
          onSave(runBookData);
        }
        
        // Clear form after successful save
        setRunBookName("");
        setRunBookErrorDescription("");
        setActions([""]);
      } catch (error) {
        console.error("Error saving run book:", error);
        setSaveError(error.message);
      } finally {
        setSaveLoading(false);
      }
      return;
    }

    // Handle Swagger/OpenAPI mode
    if (actionDiscoveryMode === "swagger") {
      // Read file contents if file is selected
      let swaggerFileContent = null;
      let swaggerDoc = null;
      
      if (swaggerFile) {
        swaggerFileContent = await swaggerFile.text();
        // Parse the file content as JSON
        try {
          swaggerDoc = JSON.parse(swaggerFileContent);
        } catch (e) {
          console.error("Error parsing swagger file as JSON:", e);
          swaggerDoc = swaggerFileContent; // Fallback to raw content if not valid JSON
        }
      }

      // Build the swagger data
      const swaggerData = swaggerFile
        ? {
            swagger_doc: swaggerDoc,
            service_name: swaggerServiceName,
          }
        : {
            swagger_url: swaggerUrl,
            service_name: swaggerServiceName,
          };

      console.log("swaggerData", swaggerData);
      
      if (!currentPipelineId) {
        console.error("Pipeline ID is required for swagger discovery");
        return;
      }
      
      try {
      // Use the agentic proxy to route to the container's swagger discovery endpoint
      const response = await fetch(
        `${import.meta.env.VITE_API_SERVER}/agentic/${currentPipelineId}/runbook/discover/swagger`,
        {
          method: "POST",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(swaggerData),
        }
      );      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
          `Failed to add action: ${errorText || response.status}`
        );
      }

      const result = await response.json();
      console.log("action added successfully:", result);

      if (onSave) {
          onSave(swaggerData);
        }
      } catch (error) {
        console.error("Error saving action:", error);
      }
      return;
    }

    // Handle Script Discovery mode
    if (actionDiscoveryMode === "script") {
      // Build the script discovery data
      const scriptData = {
        host: sshHost,
        scripts_path: scriptPath,
        credentials: {
          username: sshUsername,
          password: sshPassword || "",
          private_key_path: sshKeyPath || "",
          private_key_passphrase: privateKeyPassphrase || "",
          port: sshPort ? parseInt(sshPort) : null,
        },
        service_name: scriptServiceName,
      };

      console.log("scriptData", scriptData);
      
      if (!currentPipelineId) {
        console.error("Pipeline ID is required for SSH discovery");
        return;
      }
      
      try {
        // Use the agentic proxy to route to the container's SSH discovery endpoint
        const response = await fetch(
          `${import.meta.env.VITE_API_SERVER}/agentic/${currentPipelineId}/runbook/discover/ssh`,
          {
            method: "POST",
            credentials: "include",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(scriptData),
          }
        );

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(
            `Failed to add action: ${errorText || response.status}`
          );
        }

        const result = await response.json();
        console.log("action added successfully:", result);

        if (onSave) {
          onSave(scriptData);
        }
      } catch (error) {
        console.error("Error saving action:", error);
      }
      return;
    }

    // Handle Documentation Discovery mode
    if (actionDiscoveryMode === "documentation") {
      // Read file contents if file is selected
      let documentationText = documentation;
      
      if (documentationFile) {
        documentationText = await documentationFile.text();
      }

      if (!documentationText || !documentationText.trim()) {
        console.error("Documentation text is required");
        return;
      }

      // Build the documentation discovery data
      const docData = {
        documentation: documentationText,
        service_name: serviceName, // Use the service name field from manual action form
      };

      console.log("documentationData", docData);
      
      if (!currentPipelineId) {
        console.error("Pipeline ID is required for documentation discovery");
        return;
      }
      
      try {
        // Use the agentic proxy to route to the container's documentation discovery endpoint
        const response = await fetch(
          `${import.meta.env.VITE_API_SERVER}/agentic/${currentPipelineId}/runbook/discover/documentation`,
          {
            method: "POST",
            credentials: "include",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(docData),
          }
        );

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(
            `Failed to discover actions from documentation: ${errorText || response.status}`
          );
        }

        const result = await response.json();
        console.log("documentation discovery completed successfully:", result);

        if (onSave) {
          onSave(docData);
        }
      } catch (error) {
        console.error("Error discovering actions from documentation:", error);
      }
      return;
    }

    // Handle manual mode

    // Transform parameters from key-value pairs to Dict[str, Any]
    const parametersDict = {};
    parameters.forEach((param) => {
      if (param.key.trim() !== "") {
        parametersDict[param.key] = param.value || null;
      }
    });

    // Transform secrets from key-value pairs to List[str] (just the keys/names)
    const secretsList = secrets
      .filter((secret) => secret.key.trim() !== "")
      .map((secret) => secret.key);

    // Build execution object with fixed values
    const execution = {
      endpoint: "/api/cache/clear",
      http_method: "POST",
      base_url: "http://cache-service:8080",
    };

    // Build the action data according to the Pydantic model
    const actionData = {
      action_id: actionId,
      service: serviceName,
      method: executionMethod,
      definition: errorDescription,
      risk_level: riskLevel,
      requires_approval: requiresApproval,
      execution: execution,
      parameters: parametersDict,
      secrets: secretsList,
    };

    console.log("actionData", actionData);
    
    // Get pipelineId from context or formData
    const pipelineId = currentPipelineId || formData.pipelineId || formData.pipeline_id || "";
    
    if (!pipelineId) {
      console.error("Pipeline ID is required");
      return;
    }
    
    try {
      // Use the agentic proxy to route to the container's add action endpoint
      const response = await fetch(
        `${import.meta.env.VITE_API_SERVER}/agentic/${pipelineId}/runbook/actions/add`,
        {
          method: "POST",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(actionData),
        }
      );

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
          `Failed to add action: ${errorText || response.status}`
        );
      }

      const result = await response.json();
      console.log("action added successfully:", result);

      if (onSave) {
        onSave(actionData);
      }
    } catch (error) {
      console.error("Error saving action:", error);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="lg"
      fullWidth
      PaperProps={{
        sx: {
          maxWidth: "80rem",
          width: "100%",
          height: "90vh",
          display: "flex",
          flexDirection: "column",
        },
      }}
    >
      <DialogContent
        sx={{
          p: 0,
          display: "flex",
          flexDirection: "column",
          flex: 1,
          minHaeight: 0,
          maxHeight: "700px",
        }}
      >
        {/* Header with Tabs */}
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            p: 2,
            borderBottom: 1,
            borderColor: "divider",
            position: "relative",
          }}
        >
          <Box
            sx={{
              position: "absolute",
              left: "50%",
              transform: "translateX(-50%)",
            }}
          >
            <Tabs
              value={activeTab}
              onChange={(e, newValue) => setActiveTab(newValue)}
            >
              <Tab label="Run Book" />
              <Tab label="Actions" iconPosition="start" />
            </Tabs>
          </Box>
          <IconButton onClick={onClose} size="small" sx={{ ml: "auto" }}>
            <CloseIcon />
          </IconButton>
        </Box>

        {/* Main Content - Two Column Layout */}
        <Box sx={{ display: "flex", flex: 1, minHeight: 0 }}>
          {/* Left Panel - Protocol Cards or Action Cards */}
          <Box
            sx={{
              width: "50%",
              overflowY: "auto",
              p: 3,
              bgcolor: "background.paper",
            }}
          >
            {activeTab === 0 ? (
              // Error Catalog Cards for Run Book tab
              <>
                {/* Header with refresh button */}
                <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
                  <Typography variant="h6" fontWeight={600}>Error Catalog</Typography>
                  <IconButton 
                    onClick={fetchErrorCatalog} 
                    disabled={errorCatalogLoading}
                    size="small"
                    title="Refresh error catalog"
                  >
                    {errorCatalogLoading ? <CircularProgress size={20} /> : <RefreshIcon />}
                  </IconButton>
                </Box>
                
                {errorCatalogError && (
                  <Typography color="error" variant="body2" sx={{ mb: 2 }}>
                    {errorCatalogError}
                  </Typography>
                )}
                
                {errorCatalogLoading && errorCatalog.length === 0 ? (
                  <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
                    <CircularProgress />
                  </Box>
                ) : errorCatalog.length === 0 ? (
                  <Typography color="text.secondary" variant="body2" sx={{ textAlign: "center", py: 4 }}>
                    No error mappings found. Create one using the form on the right.
                  </Typography>
                ) : (
                  errorCatalog.map((mapping, index) => {
                    const handleCopyMapping = async () => {
                      try {
                        await navigator.clipboard.writeText(JSON.stringify(mapping, null, 2));
                      } catch (err) {
                        console.error("Failed to copy:", err);
                      }
                    };

                    const handleDeleteMapping = async () => {
                      if (!currentPipelineId) {
                        console.error("Pipeline ID is required");
                        setSaveError("No pipeline selected. Please select a workflow first.");
                        return;
                      }

                      try {
                        const url = `${import.meta.env.VITE_API_SERVER}/action/${currentPipelineId}/error-registry/mappings/${encodeURIComponent(mapping.error)}`;
                        console.log("Deleting mapping from:", url);
                        
                        const response = await fetch(url, {
                          method: "DELETE",
                          credentials: "include",
                          headers: {
                            "Content-Type": "application/json",
                          },
                        });

                        if (!response.ok) {
                          let errorMessage = `Failed to delete mapping (Status: ${response.status})`;
                          try {
                            const errorData = await response.json();
                            if (errorData.detail) {
                              errorMessage = errorData.detail;
                            }
                          } catch (e) { /* ignore */ }
                          
                          if (response.status === 404) {
                            errorMessage = "Mapping not found or containers not running.";
                          } else if (response.status === 503) {
                            errorMessage = "Error registry not available. Container may still be starting.";
                          }
                          throw new Error(errorMessage);
                        }

                        console.log("Mapping deleted successfully");
                        // Refresh the error catalog
                        await fetchErrorCatalog();
                      } catch (error) {
                        console.error("Error deleting mapping:", error);
                        setSaveError(error.message);
                      }
                    };

                    return (
                      <Card
                        key={`${mapping.error}-${index}`}
                        sx={{
                          mb: 2,
                          bgcolor: "background.elevation1",
                          borderRadius: 2,
                          border: 1,
                          borderColor: "background.elevation1",
                        }}
                      >
                        <CardContent>
                          <Box
                            sx={{
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "space-between",
                              mb: 1,
                            }}
                          >
                            <Typography variant="subtitle1" fontWeight={600} sx={{ flex: 1, mr: 1, wordBreak: "break-word" }}>
                              {mapping.error || "Unknown Error"}
                            </Typography>
                            <Box sx={{ display: "flex", gap: 0.5 }}>
                              <IconButton
                                size="small"
                                onClick={handleCopyMapping}
                                sx={{
                                  width: 28,
                                  height: 28,
                                  bgcolor: "primary.lighter",
                                  "&:hover": { bgcolor: "primary.light" },
                                  "& svg": { fontSize: "0.875rem" },
                                }}
                              >
                                <ContentCopyIcon />
                              </IconButton>
                              <IconButton
                                size="small"
                                onClick={handleDeleteMapping}
                                sx={{
                                  width: 28,
                                  height: 28,
                                  bgcolor: "error.lighter",
                                  "&:hover": { bgcolor: "error.light" },
                                  "& svg": { fontSize: "0.875rem" },
                                }}
                              >
                                <DeleteIcon />
                              </IconButton>
                            </Box>
                          </Box>
                          {mapping.description && (
                            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                              {mapping.description}
                            </Typography>
                          )}
                          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                            {(mapping.actions || []).map((actionId, actionIdx) => (
                              <Chip
                                key={`${actionId}-${actionIdx}`}
                                label={actionId}
                                size="small"
                                variant="outlined"
                                sx={{ fontSize: "0.75rem" }}
                              />
                            ))}
                          </Box>
                        </CardContent>
                      </Card>
                    );
                  })
                )}
              </>
            ) : (
              // Action Cards for Actions tab
              (() => {
                // Get all actions from API (agentic container)
                const allActions = allActionsForDropdown || [];
                return (
                  <>
                    {/* Header with refresh button */}
                    <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
                      <Typography variant="h6" fontWeight={600}>Actions</Typography>
                      <IconButton 
                        onClick={fetchActions} 
                        disabled={actionsLoading}
                        size="small"
                        title="Refresh actions"
                      >
                        {actionsLoading ? <CircularProgress size={20} /> : <RefreshIcon />}
                      </IconButton>
                    </Box>
                    
                    {actionsError && (
                      <Typography color="error" variant="body2" sx={{ mb: 2 }}>
                        {actionsError}
                      </Typography>
                    )}
                    
                    {actionsLoading && allActions.length === 0 ? (
                      <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
                        <CircularProgress />
                      </Box>
                    ) : allActions.length === 0 ? (
                      <Typography color="text.secondary" variant="body2" sx={{ textAlign: "center", py: 4 }}>
                        No actions found. Discover or add actions using the form on the right.
                      </Typography>
                    ) : (
                      allActions.map((action, index) => {
                  const handleCopy = async () => {
                    try {
                      await navigator.clipboard.writeText(JSON.stringify(action, null, 2));
                    } catch (err) {
                      console.error("Failed to copy:", err);
                    }
                  };

                  const handleDelete = async () => {
                    const pipelineId = currentPipelineId || formData.pipelineId || formData.pipeline_id || "";
                    
                    if (!pipelineId) {
                      console.error("Pipeline ID is required");
                      setSaveError("No pipeline selected. Please select a workflow first.");
                      return;
                    }

                    if (!action.action_id) {
                      console.error("Action ID is required");
                      setSaveError("Action ID is missing. Cannot delete action.");
                      return;
                    }

                    try {
                      const url = `${import.meta.env.VITE_API_SERVER}/agentic/${pipelineId}/runbook/actions/${action.action_id}`;
                      console.log("Deleting action from:", url);
                      
                      const response = await fetch(url, {
                        method: "DELETE",
                        credentials: "include",
                        headers: {
                          "Content-Type": "application/json",
                        },
                      });

                      if (!response.ok) {
                        let errorMessage = `Failed to delete action (Status: ${response.status})`;
                        try {
                          const errorData = await response.json();
                          if (errorData.detail) {
                            errorMessage = errorData.detail;
                          }
                        } catch (e) {
                          try {
                            const errorText = await response.text();
                            if (errorText) {
                              errorMessage = errorText;
                            }
                          } catch (textErr) { /* ignore */ }
                        }
                        
                        if (response.status === 404) {
                          errorMessage = "Action not found or containers not running.";
                        } else if (response.status === 503) {
                          errorMessage = "Action registry not available. Container may still be starting.";
                        }
                        throw new Error(errorMessage);
                      }

                      console.log("Action deleted successfully");
                      // Refresh the actions list after deletion
                      await fetchActions();
                    } catch (error) {
                      console.error("Error deleting action:", error);
                      setSaveError(error.message);
                    }
                  };

                  return (
                    <Card
                      key={`${action.action_id}-${index}`}
                      sx={{
                        mb: 2,
                        bgcolor: "background.elevation1",
                        borderRadius: 2,
                        border: 1,
                        borderColor: "background.elevation1",
                        position: "relative",
                      }}
                    >
                      <CardContent sx={{ position: "relative", pb: 4 }}>
                        <Box sx={{ position: "absolute", top: 8, right: 8, display: "flex", gap: 0.5, zIndex: 10 }}>
                          <IconButton
                            onClick={handleCopy}
                            size="small"
                            sx={{
                              width: 32,
                              height: 32,
                              bgcolor: "primary.lighter",
                              "&:hover": {
                                bgcolor: "primary.light",
                              },
                              "& svg": {
                                fontSize: "1rem",
                              },
                            }}
                          >
                            <ContentCopyIcon />
                          </IconButton>
                          <IconButton
                            onClick={handleDelete}
                            size="small"
                            sx={{
                              width: 32,
                              height: 32,
                              bgcolor: "error.lighter",
                              "&:hover": {
                                bgcolor: "error.light",
                              },
                              "& svg": {
                                fontSize: "1rem",
                              },
                            }}
                          >
                            <DeleteIcon />
                          </IconButton>
                        </Box>
                        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.125 }}>
                          <Typography variant="h6">
                            {action.action_id || "No Action ID"}
                          </Typography>
                        </Box>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 2, fontWeight: 500, fontSize: "0.75rem" }}>
                          service name: {action.service || "No Service"}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {action.definition || "No definition"}
                        </Typography>
                        {action.risk_level && (
                          <Chip
                            label={`${action.risk_level} risk`}
                            sx={{
                              position: "absolute",
                              bottom: 8,
                              right: 8,
                              borderRadius: "12px",
                              height: "20px",
                              fontSize: "0.6875rem",
                              fontWeight: 600,
                              bgcolor: "#F5E8D7",
                              color: "#8B572A",
                              border: "1px solid #E0C7A8",
                              "& .MuiChip-label": {
                                px: 1,
                                py: 0,
                              },
                            }}
                          />
                        )}
                      </CardContent>
                    </Card>
                  );
                })
                    )}
                  </>
                );
              })()
            )}
          </Box>

          {/* Right Panel - Run Book Form */}
          {activeTab === 0 && (
            <Box
              sx={{
                width: "50%",
                display: "flex",
                flexDirection: "column",
                flex: 1,
                minHeight: 0,
                bgcolor: "background.paper",
              }}
            >
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  p: 3,
                }}
              >
                <Typography variant="h5" fontWeight={700}>
                  Run Book
                </Typography>
                <Button 
                  variant="contained" 
                  onClick={handleSave}
                  disabled={saveLoading}
                  startIcon={saveLoading ? <CircularProgress size={20} color="inherit" /> : null}
                >
                  {saveLoading ? "Saving..." : "Save"}
                </Button>
              </Box>

              {/* Save error/success messages */}
              {saveError && (
                <Box sx={{ px: 3, pb: 1 }}>
                  <Alert severity="error" onClose={() => setSaveError(null)}>
                    {saveError}
                  </Alert>
                </Box>
              )}
              {saveSuccess && (
                <Box sx={{ px: 3, pb: 1 }}>
                  <Alert severity="success" onClose={() => setSaveSuccess(false)}>
                    Run book saved successfully!
                  </Alert>
                </Box>
              )}

              <Box
                sx={{
                  flex: 1,
                  overflowY: "auto",
                  overflowX: "visible",
                  p: 3,
                  position: "relative",
                }}
              >
                <Box sx={{ mb: 3 }}>
                  <Typography variant="body2" fontWeight={600} sx={{ mb: 1 }}>
                    Name
                  </Typography>
                  <TextField
                    placeholder="Enter name"
                    value={runBookName}
                    onChange={(e) => setRunBookName(e.target.value)}
                    variant="outlined"
                    fullWidth
                    sx={{
                      "& .MuiOutlinedInput-root": {
                        height: "3rem",
                        bgcolor: "background.elevation1",
                        "& fieldset": {
                          border: "none",
                        },
                        "&:hover fieldset": {
                          border: "none",
                        },
                        "&.Mui-focused fieldset": {
                          border: "none",
                        },
                      },
                    }}
                  />
                </Box>

                <Box sx={{ mb: 3 }}>
                  <Typography variant="body2" fontWeight={600} sx={{ mb: 1 }}>
                    Error Description
                  </Typography>
                  <TextField
                    multiline
                    rows={4}
                    placeholder="Enter error description"
                    value={runBookErrorDescription}
                    onChange={(e) => setRunBookErrorDescription(e.target.value)}
                    variant="outlined"
                    fullWidth
                    sx={{
                      "& .MuiOutlinedInput-root": {
                        bgcolor: "background.elevation1",
                        "& fieldset": {
                          border: "none",
                        },
                        "&:hover fieldset": {
                          border: "none",
                        },
                        "&.Mui-focused fieldset": {
                          border: "none",
                        },
                      },
                    }}
                  />
                </Box>

                {actions.map((action, index) => (
                  <Box key={index} sx={{ mb: 3 }}>
                    <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1 }}>
                      <Typography variant="body2" fontWeight={600}>
                        Action {index + 1}
                      </Typography>
                      {actions.length > 1 && (
                        <IconButton
                          size="small"
                          onClick={() => {
                            const newActions = actions.filter((_, i) => i !== index);
                            setActions(newActions.length > 0 ? newActions : [""]);
                          }}
                          sx={{
                            color: "error.main",
                            "&:hover": {
                              bgcolor: "error.lighter",
                            },
                          }}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      )}
                    </Box>
                    <FormControl fullWidth variant="outlined" sx={{ mb: 1 }}>
                      <Select
                        value={action}
                        onChange={(e) => {
                          const newActions = [...actions];
                          newActions[index] = e.target.value;
                          setActions(newActions);
                        }}
                        displayEmpty
                        variant="outlined"
                        sx={{
                          height: "3rem",
                          bgcolor: "background.elevation1",
                          "& .MuiOutlinedInput-notchedOutline": {
                            border: "none",
                          },
                          "&:hover .MuiOutlinedInput-notchedOutline": {
                            border: "none",
                          },
                          "&.Mui-focused .MuiOutlinedInput-notchedOutline": {
                            border: "none",
                          },
                        }}
                        MenuProps={{
                          disablePortal: false,
                          container: document.body,
                          PaperProps: {
                            sx: {
                              maxHeight: 300,
                              zIndex: 20002,
                            },
                          },
                        }}
                      >
                        <MenuItem value="" disabled>
                          Select an action
                        </MenuItem>
                        {allActionsForDropdown.map((actionItem, actionIndex) => {
                          const menuItemText = `${actionItem.action_id || "No Action ID"} (${actionItem.service || "No Service"}): ${actionItem.definition || "No definition"}`;
                          return (
                            <MenuItem key={`${actionItem.action_id}-${actionIndex}`} value={actionItem.action_id || ""}>
                              {menuItemText}
                            </MenuItem>
                          );
                        })}
                      </Select>
                    </FormControl>
                    {index === actions.length - 1 && action && (
                      <Box
                        sx={{ display: "flex", justifyContent: "flex-start" }}
                      >
                        <Button
                          onClick={() => setActions([...actions, ""])}
                          startIcon={<AddIcon />}
                          sx={{
                            textTransform: "none",
                            bgcolor: "primary.lighter",
                            color: "primary.main",
                            "&:hover": {
                              bgcolor: "primary.light",
                            },
                          }}
                        >
                          Add
                        </Button>
                      </Box>
                    )}
                  </Box>
                ))}
              </Box>
            </Box>
          )}

          {/* Right Panel - Actions Form */}
          {activeTab === 1 && (
            <Box
              sx={{
                width: "50%",
                display: "flex",
                flexDirection: "column",
                flex: 1,
                minHeight: 0,
                bgcolor: "background.paper",
              }}
            >
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  p: 3,
                }}
              >
                <Typography variant="h5" fontWeight={700}>
                  Add Action
                </Typography>
                <Button variant="contained" onClick={handleSave}>
                  Save
                </Button>
              </Box>

              <Box sx={{ flex: 1, overflowY: "auto", px: 3 }}>
                {/* Action Discovery Mode */}
                <Box sx={{ mb: 3 }}>
                  <Typography variant="body2" fontWeight={600} sx={{ mb: 1 }}>
                    Add action method
                  </Typography>
                  <FormControl fullWidth variant="outlined">
                    <Select
                      value={actionDiscoveryMode}
                      onChange={(e) => setActionDiscoveryMode(e.target.value)}
                      displayEmpty
                      variant="outlined"
                    sx={{
                        height: "3rem",
                        bgcolor: "background.elevation1",
                        "& .MuiOutlinedInput-notchedOutline": {
                          border: "none",
                        },
                        "&:hover .MuiOutlinedInput-notchedOutline": {
                          border: "none",
                        },
                        "&.Mui-focused .MuiOutlinedInput-notchedOutline": {
                          border: "none",
                        },
                      }}
                      MenuProps={{
                        disablePortal: false,
                        container: document.body,
                        PaperProps: {
                          sx: {
                            maxHeight: 300,
                            zIndex: 20002,
                          },
                        },
                      }}
                    >
                      <MenuItem value="" disabled>
                        Select an option
                      </MenuItem>
                      <MenuItem value="manual">Add action manually</MenuItem>
                      <MenuItem value="swagger">Discover from Swagger/OpenAI</MenuItem>
                      <MenuItem value="script">Discover from script</MenuItem>
                      <MenuItem value="documentation">Discover from documentation</MenuItem>
                    </Select>
                  </FormControl>
                </Box>

                {/* Manual Action Fields */}
                {actionDiscoveryMode === "manual" && (
                  <Box>
                    {/* Top Section */}
                    <Box sx={{ mb: 3 }}>
                      {/* Service */}
                      <Box sx={{ mb: 2 }}>
                        <Typography variant="body2" fontWeight={600} sx={{ mb: 1 }}>
                          Service
                  </Typography>
                  <TextField
                          placeholder="Enter service"
                          value={serviceName}
                          onChange={(e) => setServiceName(e.target.value)}
                    variant="outlined"
                    fullWidth
                    sx={{
                      "& .MuiOutlinedInput-root": {
                              height: "3rem",
                              bgcolor: "background.elevation1",
                        "& fieldset": {
                          border: "none",
                        },
                        "&:hover fieldset": {
                          border: "none",
                        },
                        "&.Mui-focused fieldset": {
                          border: "none",
                        },
                      },
                    }}
                  />
                </Box>

                      {/* Definition */}
                      <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" fontWeight={600} sx={{ mb: 1 }}>
                          Definition
                  </Typography>
                  <TextField
                    multiline
                    rows={4}
                          placeholder="Definition"
                    value={errorDescription}
                    onChange={(e) => setErrorDescription(e.target.value)}
                    variant="outlined"
                    fullWidth
                    sx={{
                      "& .MuiOutlinedInput-root": {
                              bgcolor: "background.elevation1",
                        "& fieldset": {
                          border: "none",
                        },
                        "&:hover fieldset": {
                          border: "none",
                        },
                        "&.Mui-focused fieldset": {
                          border: "none",
                        },
                      },
                    }}
                  />
                </Box>

                      <Box sx={{ mb: 2 }}>
                        <Typography variant="body2" fontWeight={600} sx={{ mb: 1 }}>
                          Action ID
                        </Typography>
                        <TextField
                          value={actionId}
                          onChange={(e) => setActionId(e.target.value)}
                          variant="outlined"
                          fullWidth
                          placeholder="restart-nginx-service"
                    sx={{
                            "& .MuiOutlinedInput-root": {
                              height: "3rem",
                              bgcolor: "background.elevation1",
                              "& fieldset": {
                                border: "none",
                              },
                              "&:hover fieldset": {
                                border: "none",
                              },
                              "&.Mui-focused fieldset": {
                                border: "none",
                              },
                            },
                          }}
                        />
                      </Box>

                      <Box sx={{ mb: 2 }}>
                        <Typography variant="body2" fontWeight={600} sx={{ mb: 1 }}>
                          Execution Method
                        </Typography>
                        <FormControl fullWidth variant="outlined">
                          <Select
                            value={executionMethod}
                            onChange={(e) => setExecutionMethod(e.target.value)}
                            displayEmpty
                            variant="outlined"
                            sx={{
                              height: "3rem",
                              bgcolor: "background.elevation1",
                              "& .MuiOutlinedInput-notchedOutline": {
                                border: "none",
                              },
                              "&:hover .MuiOutlinedInput-notchedOutline": {
                                border: "none",
                              },
                              "&.Mui-focused .MuiOutlinedInput-notchedOutline": {
                                border: "none",
                              },
                            }}
                            MenuProps={{
                              disablePortal: false,
                              container: document.body,
                              PaperProps: {
                                sx: {
                                  maxHeight: 300,
                                  zIndex: 20002,
                                },
                              },
                            }}
                          >
                            <MenuItem value="">Select method</MenuItem>
                            <MenuItem value="rpc">rpc</MenuItem>
                            <MenuItem value="script">script</MenuItem>
                            <MenuItem value="api">api</MenuItem>
                            <MenuItem value="k8s">k8s</MenuItem>
                            <MenuItem value="command">command</MenuItem>
                          </Select>
                        </FormControl>
                  </Box>
                </Box>

                    {/* Bottom Section - Risk Level, Requires Approval, Secrets */}
                    <Box sx={{ mt: 3 }}>
                      <Box sx={{ mb: 2 }}>
                        <Typography variant="body2" fontWeight={600} sx={{ mb: 1 }}>
                          Risk Level
                        </Typography>
                        <FormControl fullWidth variant="outlined">
                          <Select
                            value={riskLevel}
                            onChange={(e) => setRiskLevel(e.target.value)}
                            displayEmpty
                            variant="outlined"
                    sx={{
                              height: "3rem",
                              bgcolor: "background.elevation1",
                              "& .MuiOutlinedInput-notchedOutline": {
                                border: "none",
                              },
                              "&:hover .MuiOutlinedInput-notchedOutline": {
                                border: "none",
                              },
                              "&.Mui-focused .MuiOutlinedInput-notchedOutline": {
                                border: "none",
                              },
                            }}
                            MenuProps={{
                              disablePortal: false,
                              container: document.body,
                              PaperProps: {
                                sx: {
                                  maxHeight: 300,
                                  zIndex: 20002,
                                },
                              },
                    }}
                  >
                            <MenuItem value="">Select risk level</MenuItem>
                            <MenuItem value="low">low</MenuItem>
                            <MenuItem value="medium">medium</MenuItem>
                            <MenuItem value="high">high</MenuItem>
                          </Select>
                        </FormControl>
                  </Box>

                      <Box sx={{ mb: 2 }}>
                        <FormControlLabel
                          control={
                            <Checkbox
                              checked={requiresApproval}
                              onChange={(e) => setRequiresApproval(e.target.checked)}
                              sx={{
                                color: "primary.main",
                                "&.Mui-checked": {
                                  color: "primary.main",
                                },
                              }}
                            />
                          }
                          label={
                    <Typography variant="body2" fontWeight={600}>
                              Requires Approval
                    </Typography>
                          }
                        />
                      </Box>

                      <Box sx={{ mb: 2 }}>
                        <Typography variant="body2" fontWeight={600} sx={{ mb: 1 }}>
                          Secrets
                        </Typography>
                        {secrets.map((secret, index) => (
                          <Box key={index} sx={{ display: "flex", gap: 1, mb: 1, alignItems: "center" }}>
                            <TextField
                              value={secret.key}
                              onChange={(e) => {
                                const newSecrets = [...secrets];
                                newSecrets[index] = { ...newSecrets[index], key: e.target.value };
                                setSecrets(newSecrets);
                              }}
                              variant="outlined"
                              placeholder="Key"
                              sx={{
                                flex: 1,
                                "& .MuiOutlinedInput-root": {
                                  height: "3rem",
                                  bgcolor: "background.elevation1",
                                  "& fieldset": {
                                    border: "none",
                                  },
                                  "&:hover fieldset": {
                                    border: "none",
                                  },
                                  "&.Mui-focused fieldset": {
                                    border: "none",
                                  },
                                },
                              }}
                            />
                            <TextField
                              type="password"
                              value={secret.value}
                              onChange={(e) => {
                                const newSecrets = [...secrets];
                                newSecrets[index] = { ...newSecrets[index], value: e.target.value };
                                setSecrets(newSecrets);
                              }}
                              variant="outlined"
                              placeholder="Value"
                              sx={{
                                flex: 1,
                                "& .MuiOutlinedInput-root": {
                                  height: "3rem",
                                  bgcolor: "background.elevation1",
                                  "& fieldset": {
                                    border: "none",
                                  },
                                  "&:hover fieldset": {
                                    border: "none",
                                  },
                                  "&.Mui-focused fieldset": {
                                    border: "none",
                                  },
                                },
                              }}
                            />
                            {index === secrets.length - 1 && (
                              <IconButton
                                onClick={() => {
                                  setSecrets([...secrets, { key: "", value: "" }]);
                                }}
                                sx={{
                                  bgcolor: "primary.lighter",
                                  color: "primary.main",
                                  "&:hover": {
                                    bgcolor: "primary.light",
                                  },
                                }}
                      >
                                <AddIcon />
                              </IconButton>
                            )}
                          </Box>
                        ))}
                      </Box>
                    </Box>

                    {/* JSON Configuration Blocks - Last Three Fields */}
                    <Box sx={{ mt: 3 }}>
                      {/* Parameters */}
                      <Box sx={{ mb: 2 }}>
                        <Typography variant="body2" fontWeight={600} sx={{ mb: 1 }}>
                          Parameters
                        </Typography>
                        {parameters.map((param, index) => (
                          <Box key={index} sx={{ display: "flex", gap: 1, mb: 1, alignItems: "center" }}>
                            <TextField
                              value={param.key}
                              onChange={(e) => {
                                const newParameters = [...parameters];
                                newParameters[index] = { ...newParameters[index], key: e.target.value };
                                setParameters(newParameters);
                              }}
                              variant="outlined"
                              placeholder="Key"
                              sx={{
                                flex: 1,
                                "& .MuiOutlinedInput-root": {
                                  height: "3rem",
                                  bgcolor: "background.elevation1",
                                  "& fieldset": {
                                    border: "none",
                                  },
                                  "&:hover fieldset": {
                                    border: "none",
                                  },
                                  "&.Mui-focused fieldset": {
                                    border: "none",
                                  },
                                },
                              }}
                            />
                            <TextField
                              value={param.value}
                              onChange={(e) => {
                                const newParameters = [...parameters];
                                newParameters[index] = { ...newParameters[index], value: e.target.value };
                                setParameters(newParameters);
                              }}
                              variant="outlined"
                              placeholder="Value"
                              sx={{
                                flex: 1,
                                "& .MuiOutlinedInput-root": {
                                  height: "3rem",
                                  bgcolor: "background.elevation1",
                                  "& fieldset": {
                                    border: "none",
                                  },
                                  "&:hover fieldset": {
                                    border: "none",
                                  },
                                  "&.Mui-focused fieldset": {
                                    border: "none",
                                  },
                                },
                              }}
                            />
                            {index === parameters.length - 1 && (
                              <IconButton
                                onClick={() => {
                                  setParameters([...parameters, { key: "", value: "" }]);
                                }}
                                sx={{
                                  bgcolor: "primary.lighter",
                                  color: "primary.main",
                                  "&:hover": {
                                    bgcolor: "primary.light",
                                  },
                                }}
                              >
                                <AddIcon />
                              </IconButton>
                            )}
                  </Box>
                        ))}
                      </Box>
                    </Box>
                  </Box>
                )}

                {/* Swagger/OpenAPI Fields */}
                {actionDiscoveryMode === "swagger" && (
                <Box>
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="body2" fontWeight={600} sx={{ mb: 1 }}>
                        Service Name
                      </Typography>
                  <TextField
                        value={swaggerServiceName}
                        onChange={(e) => setSwaggerServiceName(e.target.value)}
                    variant="outlined"
                    fullWidth
                        placeholder="Enter service name"
                    sx={{
                      "& .MuiOutlinedInput-root": {
                            height: "3rem",
                            bgcolor: "background.elevation1",
                        "& fieldset": {
                          border: "none",
                        },
                        "&:hover fieldset": {
                          border: "none",
                        },
                        "&.Mui-focused fieldset": {
                          border: "none",
                        },
                      },
                    }}
                  />
                </Box>

                    <Box sx={{ mb: 2 }}>
                      <Typography variant="body2" fontWeight={600} sx={{ mb: 1 }}>
                        Swagger/OpenAPI URL
                    </Typography>
                      <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
                        <TextField
                          value={swaggerUrl}
                          onChange={(e) => {
                            setSwaggerUrl(e.target.value);
                            setSwaggerFile(null);
                            setSwaggerFileName("");
                          }}
                          variant="outlined"
                          fullWidth
                          placeholder="http://localhost:8000/openapi.json"
                          disabled={!!swaggerFile}
                    sx={{
                            "& .MuiOutlinedInput-root": {
                              height: "3rem",
                              bgcolor: "background.elevation1",
                              "& fieldset": {
                                border: "none",
                              },
                              "&:hover fieldset": {
                                border: "none",
                              },
                              "&.Mui-focused fieldset": {
                                border: "none",
                              },
                            },
                          }}
                        />
                        <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: "nowrap" }}>
                          or
                        </Typography>
                        <input
                          accept=".json,.yaml,.yml"
                          style={{ display: "none" }}
                          id="swagger-file-upload"
                          type="file"
                          onChange={(e) => {
                            const file = e.target.files[0];
                            if (file) {
                              setSwaggerFile(file);
                              setSwaggerFileName(file.name);
                              setSwaggerUrl("");
                            }
                          }}
                        />
                        <label htmlFor="swagger-file-upload">
                          <Button
                            component="span"
                            variant="outlined"
                            startIcon={<CloudUploadIcon />}
                            sx={{
                              height: "3rem",
                              whiteSpace: "nowrap",
                              color: "#000",
                              borderColor: "#000",
                              "&:hover": {
                                borderColor: "#000",
                                backgroundColor: "rgba(0, 0, 0, 0.04)",
                              },
                            }}
                  >
                            {swaggerFileName || "Upload File"}
                      </Button>
                        </label>
                  </Box>
                      {swaggerFileName && (
                        <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: "block" }}>
                          {swaggerFileName}
                    </Typography>
                      )}
                  </Box>
                  </Box>
                )}

                {/* Script Discovery Fields */}
                {actionDiscoveryMode === "script" && (
                <Box>
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="body2" fontWeight={600} sx={{ mb: 1 }}>
                        Service Name
                      </Typography>
                        <TextField
                        value={scriptServiceName}
                        onChange={(e) => setScriptServiceName(e.target.value)}
                          variant="outlined"
                          fullWidth
                        placeholder="Enter service name"
                          sx={{
                            "& .MuiOutlinedInput-root": {
                            height: "3rem",
                            bgcolor: "background.elevation1",
                              "& fieldset": {
                                border: "none",
                              },
                              "&:hover fieldset": {
                                border: "none",
                              },
                              "&.Mui-focused fieldset": {
                                border: "none",
                              },
                            },
                          }}
                        />
                    </Box>

                    <Box sx={{ mb: 2 }}>
                      <Typography variant="body2" fontWeight={600} sx={{ mb: 1 }}>
                        Script Path
                        </Typography>
                  <TextField
                        value={scriptPath}
                        onChange={(e) => setScriptPath(e.target.value)}
                    variant="outlined"
                    fullWidth
                        placeholder="/path/to/script.sh or /var/scripts/"
                    sx={{
                      "& .MuiOutlinedInput-root": {
                            height: "3rem",
                            bgcolor: "background.elevation1",
                        "& fieldset": {
                          border: "none",
                        },
                        "&:hover fieldset": {
                          border: "none",
                        },
                        "&.Mui-focused fieldset": {
                          border: "none",
                        },
                      },
                    }}
                  />
                      </Box>

                    {/* SSH Configuration Fields */}
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="body2" fontWeight={600} sx={{ mb: 1 }}>
                        SSH Host
                      </Typography>
                        <TextField
                        value={sshHost}
                        onChange={(e) => setSshHost(e.target.value)}
                          variant="outlined"
                          fullWidth
                        placeholder="server.example.com"
                          sx={{
                            "& .MuiOutlinedInput-root": {
                            height: "3rem",
                            bgcolor: "background.elevation1",
                              "& fieldset": {
                                border: "none",
                              },
                              "&:hover fieldset": {
                                border: "none",
                              },
                              "&.Mui-focused fieldset": {
                                border: "none",
                              },
                            },
                          }}
                        />
                    </Box>

                    <Box sx={{ mb: 2 }}>
                      <Typography variant="body2" fontWeight={600} sx={{ mb: 1 }}>
                        SSH Username
                        </Typography>
                      <TextField
                        value={sshUsername}
                        onChange={(e) => setSshUsername(e.target.value)}
                        variant="outlined"
                        fullWidth
                        placeholder="admin"
                        sx={{
                          "& .MuiOutlinedInput-root": {
                            height: "3rem",
                            bgcolor: "background.elevation1",
                            "& fieldset": {
                              border: "none",
                            },
                            "&:hover fieldset": {
                              border: "none",
                            },
                            "&.Mui-focused fieldset": {
                              border: "none",
                            },
                          },
                        }}
                      />
                      </Box>

                    <Box sx={{ mb: 2 }}>
                      <Typography variant="body2" fontWeight={600} sx={{ mb: 1 }}>
                        SSH Password (optional)
                      </Typography>
                        <TextField
                        type="password"
                        value={sshPassword}
                        onChange={(e) => setSshPassword(e.target.value)}
                          variant="outlined"
                          fullWidth
                          sx={{
                            "& .MuiOutlinedInput-root": {
                            height: "3rem",
                            bgcolor: "background.elevation1",
                              "& fieldset": {
                                border: "none",
                              },
                              "&:hover fieldset": {
                                border: "none",
                              },
                              "&.Mui-focused fieldset": {
                                border: "none",
                              },
                            },
                          }}
                        />
                    </Box>

                    <Box sx={{ mb: 2 }}>
                      <Typography variant="body2" fontWeight={600} sx={{ mb: 1 }}>
                        SSH Key Path (optional)
                        </Typography>
                      <TextField
                        value={sshKeyPath}
                        onChange={(e) => setSshKeyPath(e.target.value)}
                        variant="outlined"
                        fullWidth
                        placeholder="/home/user/.ssh/id_rsa"
                        sx={{
                          "& .MuiOutlinedInput-root": {
                            height: "3rem",
                            bgcolor: "background.elevation1",
                            "& fieldset": {
                              border: "none",
                            },
                            "&:hover fieldset": {
                              border: "none",
                            },
                            "&.Mui-focused fieldset": {
                              border: "none",
                            },
                          },
                        }}
                      />
                </Box>

                    <Box sx={{ mb: 2 }}>
                      <Typography variant="body2" fontWeight={600} sx={{ mb: 1 }}>
                        Private Key Passphrase (optional)
                      </Typography>
                      <TextField
                        type="password"
                        value={privateKeyPassphrase}
                        onChange={(e) => setPrivateKeyPassphrase(e.target.value)}
                        variant="outlined"
                        fullWidth
                        placeholder="Enter private key passphrase"
                        sx={{
                          "& .MuiOutlinedInput-root": {
                            height: "3rem",
                            bgcolor: "background.elevation1",
                            "& fieldset": {
                              border: "none",
                            },
                            "&:hover fieldset": {
                              border: "none",
                            },
                            "&.Mui-focused fieldset": {
                              border: "none",
                            },
                          },
                        }}
                      />
                    </Box>
                    </Box>
                )}

                {/* Documentation Discovery Field */}
                {actionDiscoveryMode === "documentation" && (
                  <Box>
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="body2" fontWeight={600} sx={{ mb: 1 }}>
                        Documentation
                      </Typography>
                      <Box sx={{ mb: 1 }}>
                        <input
                          accept=".txt,.md,.pdf"
                          style={{ display: "none" }}
                          id="documentation-file-upload"
                          type="file"
                          onChange={(e) => {
                            const file = e.target.files[0];
                            if (file) {
                              setDocumentationFile(file);
                              setDocumentationFileName(file.name);
                              setDocumentation("");
                            }
                          }}
                        />
                        <label htmlFor="documentation-file-upload">
                          <Button
                            component="span"
                            variant="outlined"
                            startIcon={<CloudUploadIcon />}
                            sx={{
                              mb: 1,
                              color: "#000",
                              borderColor: "#000",
                              "&:hover": {
                                borderColor: "#000",
                                backgroundColor: "rgba(0, 0, 0, 0.04)",
                              },
                            }}
                          >
                            {documentationFileName || "Upload File"}
                          </Button>
                        </label>
                        {documentationFileName && (
                          <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                            {documentationFileName}
                          </Typography>
                        )}
                </Box>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 1, textAlign: "center" }}>
                        or
                      </Typography>
                      <TextField
                        multiline
                        rows={12}
                        value={documentation}
                        onChange={(e) => {
                          setDocumentation(e.target.value);
                          setDocumentationFile(null);
                          setDocumentationFileName("");
                        }}
                        variant="outlined"
                        fullWidth
                        placeholder="Enter documentation..."
                        disabled={!!documentationFile}
                        sx={{
                          "& .MuiOutlinedInput-root": {
                            bgcolor: "background.elevation1",
                            "& fieldset": {
                              border: "none",
                            },
                            "&:hover fieldset": {
                              border: "none",
                            },
                            "&.Mui-focused fieldset": {
                              border: "none",
                            },
                          },
                        }}
                      />
                </Box>
                  </Box>
                )}
              </Box>
            </Box>
          )}
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default RunBook;
