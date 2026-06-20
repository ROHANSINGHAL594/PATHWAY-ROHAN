import { useState } from "react";
import {
  Box,
  Paper,
  IconButton,
  TextField,
  Button,
  Typography,
  CircularProgress,
} from "@mui/material";
import CheckIcon from "@mui/icons-material/Check";
import CloseIcon from "@mui/icons-material/Close";
import SendIcon from "@mui/icons-material/Send";

/**
 * Node Approval Popup Component
 * Shows tick/cross buttons near a proposed node for approval/rejection
 */
const NodeApprovalPopup = ({
  nodeId,
  position,
  onApprove,
  onReject,
  isRendering = false,
}) => {
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedback, setFeedback] = useState("");

  const handleApprove = () => {
    onApprove();
  };

  const handleReject = () => {
    if (!showFeedback) {
      setShowFeedback(true);
    } else if (feedback.trim()) {
      onReject(feedback);
      setFeedback("");
      setShowFeedback(false);
    }
  };

  const handleSendFeedback = () => {
    if (feedback.trim()) {
      onReject(feedback);
      setFeedback("");
      setShowFeedback(false);
    }
  };

  // Position is already in screen coordinates relative to ReactFlow container
  const screenPosition = position || { x: 0, y: 0 };
  
  return (
    <Paper
      elevation={8}
      sx={{
        position: "absolute",
        left: `${screenPosition.x}px`,
        top: `${screenPosition.y}px`,
        p: 2,
        minWidth: 280,
        bgcolor: "background.paper",
        borderRadius: 2,
        border: "1px solid",
        borderColor: "divider",
        zIndex: 10000,
        pointerEvents: "auto", // Enable interactions
        // No transform needed - position is already calculated to be above the node
      }}
    >
      {isRendering ? (
        <>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
            <CircularProgress size={20} />
            <Typography variant="body2" sx={{ fontWeight: 500 }}>
              Rendering node...
            </Typography>
          </Box>
        </>
      ) : !showFeedback ? (
        <>
          <Typography variant="body2" sx={{ mb: 2, fontWeight: 500 }}>
            Accept this node?
          </Typography>
          <Box sx={{ display: "flex", gap: 1, justifyContent: "flex-end" }}>
            <IconButton
              onClick={handleReject}
              size="small"
              color="error"
              disabled={isRendering}
              sx={{
                bgcolor: "error.light",
                color: "error.contrastText",
                "&:hover": { bgcolor: "error.main" },
                "&:disabled": { opacity: 0.5 },
              }}
            >
              <CloseIcon fontSize="small" />
            </IconButton>
            <IconButton
              onClick={handleApprove}
              size="small"
              color="success"
              disabled={isRendering}
              sx={{
                bgcolor: "success.light",
                color: "success.contrastText",
                "&:hover": { bgcolor: "success.main" },
                "&:disabled": { opacity: 0.5 },
              }}
            >
              <CheckIcon fontSize="small" />
            </IconButton>
          </Box>
        </>
      ) : (
        <>
          <Typography variant="body2" sx={{ mb: 1.5, fontWeight: 500 }}>
            Provide feedback:
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={3}
            size="small"
            placeholder="Enter your feedback..."
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            sx={{ mb: 1.5 }}
          />
          <Box sx={{ display: "flex", gap: 1, justifyContent: "flex-end" }}>
            <Button
              size="small"
              onClick={() => {
                setShowFeedback(false);
                setFeedback("");
              }}
            >
              Cancel
            </Button>
            <Button
              size="small"
              variant="contained"
              onClick={handleSendFeedback}
              disabled={!feedback.trim()}
              startIcon={<SendIcon />}
            >
              Send
            </Button>
          </Box>
        </>
      )}
    </Paper>
  );
};

export default NodeApprovalPopup;

