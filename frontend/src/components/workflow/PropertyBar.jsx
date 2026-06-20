import { useState } from "react";
import Markdown from "react-markdown";
import {
  Drawer,
  Box,
  Typography,
  Button,
  Alert,
  Snackbar,
  IconButton,
  useTheme,
  alpha,
} from "@mui/material";
import { Close as CloseIcon } from "@mui/icons-material";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

export const PropertyBar = ({
  open,
  selectedNode,
  onClose,
  onUpdateProperties,
  anchor = "right",
  drawerWidth = 360,
  variant = "persistent",
  readOnly = false,
  zIndex,
}) => {
  const theme = useTheme();
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: "",
    severity: "success",
  });

  // FIX: For backend to work, we need those
  // Filter out non-editable fields from schema
  const getEditableSchema = (schema) => {
    if (!schema || !schema.properties) return schema;

    const filteredSchema = {
      ...schema,
      properties: { ...schema.properties },
      required: schema.required ? [...schema.required] : [],
    };

    // Remove node_id, category from properties
    delete filteredSchema.properties.node_id;
    delete filteredSchema.properties.category;
    delete filteredSchema.properties.n_inputs;

    // Remove from required array if present
    filteredSchema.required = filteredSchema.required.filter(
      (field) => !["node_id", "category"].includes(field)
    );

    return filteredSchema;
  };

  // Custom Markdown Description Component
  const MarkdownDescriptionField = ({ description, id }) => {
    if (!description) return null;

    return (
      <Box
        id={id}
        sx={{
          mb: 2,
          p: 1.5,
          borderRadius: 1.5,
          bgcolor: alpha(theme.palette.primary.main, 0.04),
          border: `1px solid ${alpha(theme.palette.primary.main, 0.08)}`,
        }}
      >
        <Typography
          component="div"
          variant="body2"
          color="text.secondary"
          sx={{
            "& p": { m: 0, lineHeight: 1.6 },
            "& code": {
              px: 0.75,
              py: 0.25,
              borderRadius: 0.5,
              bgcolor: "action.hover",
              fontFamily: "monospace",
              fontSize: "0.8125rem",
            },
          }}
        >
          <Markdown>{description}</Markdown>
        </Typography>
      </Box>
    );
  };

  const handleSave = ({ formData }) => {
    if (!selectedNode) return;

    try {
      onUpdateProperties(selectedNode.id, formData);
      setSnackbar({
        open: true,
        message: "Properties saved successfully!",
        severity: "success",
      });
      onClose();
    } catch (error) {
      setSnackbar({
        open: true,
        message: "Error parsing JSON. Please check the format.",
        severity: "error",
      });
    }
  };

  const handleCloseSnackbar = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  // Form styles using sx prop
  const formContainerSx = {
    flex: 1,
    overflow: "auto",
    px: 3,
    py: 2,
    // RJSF Form Overrides
    "& .MuiTextField-root": {
      mb: 1.5,
    },
    "& .MuiOutlinedInput-root": {
      borderRadius: 1.5,
      transition: "all 0.2s ease",
      "&:hover": {
        borderColor: "primary.main",
      },
    },
    "& .MuiOutlinedInput-input": {
      py: 1.5,
      px: 1.5,
      fontSize: "0.875rem",
    },
    "& .MuiFilledInput-root": {
      borderRadius: 1.5,
      "&:before, &:after": {
        display: "none",
      },
    },
    "& .MuiFilledInput-input": {
      py: 1.25,
      px: 1.5,
      fontSize: "0.875rem",
    },
    "& .MuiInputLabel-root": {
      fontSize: "0.875rem",
      fontWeight: 500,
      position: "relative",
      transform: "none",
      mb: 0.5,
      color: "text.secondary",
      "&.Mui-focused": {
        color: "primary.main",
      },
      "&.MuiInputLabel-shrink": {
        transform: "none",
      },
    },
    // Stack label above input
    "& .MuiFormControl-root": {
      "& > .MuiInputLabel-root": {
        position: "static",
        transform: "none",
        mb: 0.5,
      },
    },
    "& .MuiFormHelperText-root": {
      fontSize: "0.75rem",
      mt: 0.5,
      mx: 0,
    },
    // Fieldset styling
    "& fieldset.MuiOutlinedInput-notchedOutline": {
      borderColor: "divider",
      top: 0,
      "& legend": {
        display: "none",
      },
    },
    "& > fieldset": {
      border: "none",
      p: 0,
      m: 0,
      mb: 1,
    },
    "& legend": {
      fontWeight: 600,
      fontSize: "0.875rem",
      mb: 1,
      color: "text.primary",
    },
    // Select styling
    "& .MuiSelect-select": {
      py: 1.5,
      px: 1.5,
      fontSize: "0.875rem",
    },
    // Submit button
    "& button[type='submit']": {
      width: "100%",
      mt: 2,
      py: 1.25,
      px: 3,
      borderRadius: 2,
      fontWeight: 600,
      fontSize: "0.875rem",
      textTransform: "none",
      bgcolor: "primary.main",
      color: "primary.contrastText",
      border: "none",
      cursor: "pointer",
      transition: "all 0.2s ease",
      "&:hover": {
        bgcolor: "primary.dark",
        boxShadow: theme.shadows[4],
      },
    },
    // Array item styling
    "& .array-item": {
      p: 1.5,
      borderRadius: 1.5,
      mb: 1,
      bgcolor: "action.hover",
      border: `1px solid`,
      borderColor: "divider",
    },
    // Object property styling
    "& .object-property": {
      p: 1.5,
      borderRadius: 1.5,
      mb: 1.5,
      bgcolor: alpha(theme.palette.background.paper, 0.5),
    },
    // Add/Remove buttons for arrays
    "& .MuiButton-root[type='button']": {
      borderRadius: 1.5,
      textTransform: "none",
      fontWeight: 500,
      py: 0.75,
      px: 1.5,
      mt: 1,
      fontSize: "0.8125rem",
    },
    // Disabled fields
    "& .Mui-disabled": {
      cursor: "not-allowed",
    },
  };

  return (
    <>
      <Drawer
        anchor={anchor}
        open={open}
        onClose={onClose}
        variant={variant}
        hideBackdrop
        ModalProps={{ keepMounted: true }}
        sx={{
          zIndex: zIndex || theme.zIndex.drawer + 1,
          "& .MuiDrawer-paper": {
            width: drawerWidth,
            bgcolor: "background.paper",
            boxShadow: theme.shadows[8],
            borderLeft: `1px solid`,
            borderColor: "divider",
            transition: "transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
          },
        }}
      >
        {!selectedNode ? (
          <Box
            sx={{
              p: 3,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
            }}
          >
            <Alert
              severity="info"
              sx={{
                borderRadius: 2,
                width: "100%",
              }}
            >
              Select a node to view its properties.
            </Alert>
          </Box>
        ) : (
          <Box
            sx={{ height: "100%", display: "flex", flexDirection: "column" }}
          >
            {/* Header */}
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: { xs: "16px 16px", md: "17px 24px" },
                borderBottom: `2px solid`,
                borderColor: "divider",
                bgcolor: "background.elevation1",
              }}
            >
              <Box>
                <Typography variant="h6" fontWeight={700} color="text.primary">
                  Properties
                </Typography>
                {/* <Typography variant="caption" color="text.secondary">
                  {selectedNode?.data?.label || selectedNode?.type || "Node"}
                </Typography> */}
              </Box>
              <IconButton
                onClick={onClose}
                size="small"
                sx={{
                  color: "text.secondary",
                  bgcolor: "action.hover",
                  "&:hover": {
                    bgcolor: "action.selected",
                    color: "text.primary",
                  },
                }}
              >
                <CloseIcon fontSize="small" />
              </IconButton>
            </Box>

            {/* Form Content */}
            <Box sx={formContainerSx}>
              <Form
                schema={getEditableSchema(selectedNode?.schema)}
                validator={validator}
                formData={selectedNode?.data?.properties}
                onSubmit={handleSave}
                disabled={readOnly}
                templates={{
                  DescriptionFieldTemplate: MarkdownDescriptionField,
                }}
              />
            </Box>
          </Box>
        )}
      </Drawer>

      {/* Success/Error Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: "top", horizontal: "center" }}
      >
        <Alert
          onClose={handleCloseSnackbar}
          severity={snackbar.severity}
          variant="filled"
          sx={{ borderRadius: 2 }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </>
  );
};
