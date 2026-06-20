import { useState, useEffect } from "react";
import {
  Box,
  Drawer,
  IconButton,
  Typography,
  TextField,
  CircularProgress,
  alpha,
  useTheme,
  keyframes,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import SendIcon from "@mui/icons-material/Send";
import Markdown from "react-markdown";
import { useGlobalWorkflow } from "../../context/GlobalWorkflowContext";

// Animated gradient glow keyframes (matching AIChatbot)
const gradientGlow = keyframes`
  0% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0% 50%;
  }
`;

// Chatbot dimensions - slightly taller than AIChatbot
const chatbotSize = "80vh"; // Increased from 45vh
const chatbotWidth = "30vw";
const DRAWER_WIDTH = "calc(30vw + 80px)";

const WorkflowAIAssistant = ({ open, onClose }) => {
  const theme = useTheme();
  const { id: currentPipelineId } = useGlobalWorkflow();
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSendMessage = async () => {
    if (!chatInput.trim() || isLoading) return;

    // Check if pipeline is selected
    if (!currentPipelineId) {
      setChatMessages((prev) => [
        ...prev,
        { role: "user", content: chatInput.trim() },
        { role: "assistant", content: "No workflow selected. Please select or spin up a workflow first." },
      ]);
      setChatInput("");
      return;
    }

    const userMessage = chatInput.trim();
    setChatInput("");
    
    // Add user message to chat
    setChatMessages((prev) => [
      ...prev,
      { role: "user", content: userMessage },
    ]);

    setIsLoading(true);

    try {
      // Use API gateway to proxy to pipeline container via /action/ router
      const apiServer = import.meta.env.VITE_API_SERVER || "http://localhost:8080";
      
      const response = await fetch(`${apiServer}/action/${currentPipelineId}/prompt`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ prompt: userMessage }), // Backend expects "prompt" field
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorDetail = errorData.detail || `HTTP ${response.status}`;
        if (response.status === 404) {
          throw new Error("Workflow not found or container not running. Please spin up the workflow first.");
        } else if (response.status === 500) {
          throw new Error("Server error. The pipeline container may not be running.");
        }
        throw new Error(`Failed to get response: ${errorDetail}`);
      }

      const data = await response.json();
      
      // Add assistant response to chat
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.message || "I've received your message!" },
      ]);
    } catch (error) {
      console.error("Error sending message:", error);
      // Show error message to user
      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Sorry, I encountered an error: ${error.message}`,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <Drawer
      anchor="left"
      open={open}
      onClose={onClose}
      sx={{
        zIndex: 2600, // Higher than default sidebar (2500)
        "& .MuiDrawer-paper": {
          width: DRAWER_WIDTH,
          bgcolor: "background.paper",
          borderRight: "1px solid",
          borderColor: "divider",
          boxShadow: "2px 0 8px rgba(0, 0, 0, 0.1)",
          left: 0, // Start from leftmost edge, covering default sidebar
        },
      }}
    >
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          height: "100%",
          position: "relative",
          px: 3,
          pt: 4,
          pb: 3,
        }}
      >
        {/* Close button */}
        <Box
          sx={{
            display: "flex",
            justifyContent: "flex-end",
            mb: 2,
          }}
        >
          <IconButton
            onClick={onClose}
            size="small"
            sx={{
              color: "text.secondary",
              "&:hover": { bgcolor: "action.hover" },
            }}
          >
            <CloseIcon />
          </IconButton>
        </Box>

        {/* Chat Container - centered and taller */}
        <Box 
          sx={{ 
            display: "flex", 
            flexDirection: "column",
            gap: 2,
            width: chatbotWidth,
            position: "relative",
            flexShrink: 0,
            margin: "0 auto", // Center align horizontally
          }}
        >
          {/* Wrapper for gradient border with animated glow - matching AIChatbot */}
          <Box
            sx={{
              borderRadius: "16px",
              height: chatbotSize,
              width: chatbotWidth,
              position: "relative",
              flexShrink: 0,
              overflow: "visible",
              // Static gradient border wrapper (base layer)
              background: theme.palette.mode === "dark"
                ? "linear-gradient(to bottom, rgba(63, 120, 176, 0.3) 0%, rgba(128, 187, 196, 0) 100%)"
                : "linear-gradient(to bottom, #3F78B0 0%, rgba(128, 187, 196, 0) 100%)",
              padding: "2px",
              // Animated gradient glow border using pseudo-element
              "&::before": {
                content: '""',
                position: "absolute",
                top: "-2px",
                left: "-2px",
                right: "-2px",
                bottom: "-2px",
                borderRadius: "18px",
                zIndex: -1,
                transition: "opacity 0.5s ease, filter 0.5s ease, background 0.5s ease, background-size 0.5s ease",
                // Static state - matching the base gradient
                background: theme.palette.mode === "dark"
                  ? "linear-gradient(to bottom, rgba(63, 120, 176, 0.2) 0%, rgba(128, 187, 196, 0) 100%)"
                  : "linear-gradient(to bottom, #3F78B0 0%, rgba(128, 187, 196, 0) 100%)",
                backgroundSize: "100% 100%",
                filter: "blur(8px)",
                opacity: 0.3,
              },
            }}
          >
            <Box
              sx={{
                bgcolor: "background.paper",
                borderRadius: "14px",
                height: "100%",
                width: "100%",
                display: "flex",
                flexDirection: "column",
                overflow: "hidden",
                position: "relative",
              }}
            >
              {/* Chat messages area - matching AIChatbot */}
              <Box
                sx={{
                  flex: 1,
                  overflowY: "auto",
                  p: 2,
                  display: "flex",
                  flexDirection: "column",
                  gap: 1.5,
                }}
              >
                {chatMessages.length === 0 && (
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      height: "100%",
                      px: 2,
                    }}
                  >
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{ textAlign: "center" }}
                    >
                      Ask AI to for suggestions about your workflow...
                    </Typography>
                  </Box>
                )}
                {chatMessages.map((msg, idx) => (
                  <Box
                    key={idx}
                    sx={{
                      display: "flex",
                      justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
                    }}
                  >
                    <Box
                      sx={{
                        maxWidth: "70%",
                        p: 1.5,
                        borderRadius: 2,
                        bgcolor:
                          msg.role === "user"
                            ? "primary.main"
                            : "background.elevation1",
                        color:
                          msg.role === "user" ? "common.white" : "text.primary",
                      }}
                    >
                      {msg.role === "assistant" || msg.role === "system" ? (
                        <Typography
                          component="div"
                          variant="body2"
                          sx={{
                            "& p": { m: 0, mb: 1, lineHeight: 1.6, "&:last-child": { mb: 0 } },
                            "& code": {
                              px: 0.75,
                              py: 0.25,
                              borderRadius: 0.5,
                              bgcolor: alpha(
                                msg.role === "user" ? "rgba(255,255,255,0.2)" : theme.palette.action.hover,
                                1
                              ),
                              fontFamily: "monospace",
                              fontSize: "0.8125rem",
                            },
                            "& pre": {
                              p: 1,
                              borderRadius: 1,
                              bgcolor: alpha(theme.palette.action.hover, 1),
                              overflow: "auto",
                              "& code": {
                                bgcolor: "transparent",
                                p: 0,
                              },
                            },
                            "& ul, & ol": {
                              pl: 2,
                              mb: 1,
                            },
                            "& li": {
                              mb: 0.5,
                            },
                            "& strong": {
                              fontWeight: 600,
                            },
                            "& em": {
                              fontStyle: "italic",
                            },
                            "& h1, & h2, & h3, & h4, & h5, & h6": {
                              fontWeight: 600,
                              mt: 1.5,
                              mb: 1,
                              "&:first-child": {
                                mt: 0,
                              },
                            },
                            "& h3": {
                              fontSize: "1rem",
                              fontWeight: 600,
                            },
                          }}
                        >
                          <Markdown>{msg.content}</Markdown>
                        </Typography>
                      ) : (
                        <Typography variant="body2">{msg.content}</Typography>
                      )}
                    </Box>
                  </Box>
                ))}
              </Box>

              {/* Input area - matching AIChatbot */}
              <Box
                sx={{
                  p: 1.5,
                  borderTop: "1px solid",
                  borderColor: "divider",
                  flexShrink: 0,
                  position: "relative",
                }}
              >
                <TextField
                  fullWidth
                  size="small"
                  placeholder="Ask AI to generate your workflow..."
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  disabled={isLoading}
                  InputProps={{
                    endAdornment: (
                      <IconButton
                        onClick={handleSendMessage}
                        disabled={isLoading || !chatInput.trim()}
                        size="small"
                        sx={{ mr: -1 }}
                        title="Send message"
                      >
                        <SendIcon fontSize="small" />
                      </IconButton>
                    ),
                  }}
                  sx={{
                    "& .MuiOutlinedInput-root": {
                      bgcolor: (theme) => theme.palette.mode === "dark" 
                        ? "rgba(255, 255, 255, 0.08)" 
                        : "rgba(0, 0, 0, 0.03)",
                      borderRadius: 2,
                      "& fieldset": {
                        borderColor: (theme) => theme.palette.mode === "dark"
                          ? "rgba(255, 255, 255, 0.1)"
                          : "rgba(0, 0, 0, 0.08)",
                      },
                      "&:hover fieldset": {
                        borderColor: (theme) => theme.palette.mode === "dark"
                          ? "rgba(255, 255, 255, 0.15)"
                          : "rgba(0, 0, 0, 0.12)",
                      },
                      "&.Mui-focused fieldset": {
                        borderColor: "primary.main",
                        borderWidth: 1.5,
                      },
                    },
                  }}
                />
              </Box>
            </Box>
          </Box>
        </Box>
      </Box>
    </Drawer>
  );
};

export default WorkflowAIAssistant;

