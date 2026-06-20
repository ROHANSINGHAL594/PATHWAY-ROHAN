import { useState, useEffect } from "react";
import {
  Box,
  Typography,
  TextField,
  IconButton,
  CircularProgress,
  keyframes,
  Button,
  alpha,
} from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import CheckIcon from "@mui/icons-material/Check";
import CloseIcon from "@mui/icons-material/Close";
import Markdown from "react-markdown";
import { useTheme } from "@mui/material/styles";

// Animated gradient glow keyframes
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

const AIChatbot = ({
  formData,
  onWorkflowGenerated,
  isGenerating,
  setIsGenerating,
  onAccept,
  onDecline,
  chatMessages: externalMessages = [],
  onSendMessage,
  awaitingInput = false,
}) => {
  const theme = useTheme();
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [hasGeneratedWorkflow, setHasGeneratedWorkflow] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // Sync external messages (from WebSocket)
  useEffect(() => {
    if (externalMessages.length > 0) {
      setChatMessages(externalMessages);
    }
  }, [externalMessages]);

  const handleChatSubmit = async (analyzeMode = false) => {
    // Allow submission if awaiting input (even if isGenerating is true) or if not generating
    if ((!chatInput.trim() && !analyzeMode) || (isGenerating && !awaitingInput)) return;

    // If WebSocket is connected, use it
    if (onSendMessage) {
      const message = analyzeMode ? "Analyze and generate workflow" : chatInput;
      onSendMessage(message);
      if (!analyzeMode) {
        setChatInput("");
      }
      return;
    }

    // Fallback to old AI workflow generator
    const userMessage = analyzeMode 
      ? { role: "user", content: "Analyze and generate workflow" }
      : { role: "user", content: chatInput };

    const updatedMessages = [...chatMessages, userMessage];
    setChatMessages(updatedMessages);
    if (!analyzeMode) {
      setChatInput("");
    }
    setIsGenerating(true);
    if (analyzeMode) {
      setIsAnalyzing(true);
    }

    try {
      // Import the API function dynamically to avoid circular dependencies
      const { generateWorkflowFromAI } = await import(
        "../../utils/aiWorkflowGenerator"
      );

      const result = await generateWorkflowFromAI(formData, updatedMessages);

      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: result.message || "Workflow generated successfully!",
        },
      ]);

      // Update nodes/edges if provided
      if (result.nodes && result.edges && onWorkflowGenerated) {
        onWorkflowGenerated(result.nodes, result.edges);
        setHasGeneratedWorkflow(true);
        setIsAnalyzing(false); // Stop animation when workflow is generated
      }
    } catch (error) {
      console.error("Error generating workflow:", error);
      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Error: ${error.message || "Failed to generate workflow"}`,
        },
      ]);
    } finally {
      setIsGenerating(false);
    }
  };

  // Square chatbot: 50vh height, 70vh width
  const chatbotSize = "45vh";
  const chatbotWidth = "30vw";

  return (
    <Box 
      sx={{ 
        display: "flex", 
        flexDirection: "column",
        gap: 2,
        width: chatbotWidth,
        position: "relative",
        flexShrink: 0,
      }}
    >
      {/* Wrapper for gradient border with animated glow */}
      <Box
        sx={{
          borderRadius: "16px",
          height: chatbotSize,
          width: chatbotWidth,
          position: "relative",
          flexShrink: 0,
          overflow: "visible", // Ensure nothing gets clipped
          // Static gradient border wrapper (base layer)
          background: theme.palette.mode === "dark"
            ? "linear-gradient(to bottom, rgba(63, 120, 176, 0.3) 0%, rgba(128, 187, 196, 0) 100%)"
            : "linear-gradient(to bottom, #3F78B0 0%, rgba(128, 187, 196, 0) 100%)",
          padding: "2px", // Reduced from 5px for minimalistic look
          // Animated gradient glow border using pseudo-element
          "&::before": {
            content: '""',
            position: "absolute",
            top: "-2px", // Reduced from -5px
            left: "-2px",
            right: "-2px",
            bottom: "-2px",
            borderRadius: "18px", // 16px + 2px border
            zIndex: -1,
            transition: "opacity 0.5s ease, filter 0.5s ease, background 0.5s ease, background-size 0.5s ease",
            ...(isAnalyzing ? {
              // Animated state - rotating gradient
              background: theme.palette.mode === "dark"
                ? "linear-gradient(45deg, rgba(63, 120, 176, 0.4), rgba(128, 187, 196, 0.3), rgba(63, 120, 176, 0.4), rgba(128, 187, 196, 0.3))"
                : "linear-gradient(45deg, #3F78B0, #80BBC4, #3F78B0, #80BBC4)",
              backgroundSize: "400% 400%",
              animation: `${gradientGlow} 3s ease infinite`,
              filter: "blur(8px)", // Slightly reduced blur
              opacity: 0.7,
            } : {
              // Static state - matching the base gradient
              background: theme.palette.mode === "dark"
                ? "linear-gradient(to bottom, rgba(63, 120, 176, 0.2) 0%, rgba(128, 187, 196, 0) 100%)"
                : "linear-gradient(to bottom, #3F78B0 0%, rgba(128, 187, 196, 0) 100%)",
              backgroundSize: "100% 100%",
              filter: "blur(8px)", // Slightly reduced blur
              opacity: 0.3,
            }),
          },
        }}
      >
        <Box
          sx={{
            bgcolor: "background.paper",
            borderRadius: "14px", // Inner radius (16px - 2px for border)
            height: "100%",
            width: "100%",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            position: "relative",
          }}
        >
        {/* Chat messages area */}
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
                Ask AI to generate or refine your workflow...
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
          {isGenerating && !awaitingInput && (
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1,
                color: "text.secondary",
              }}
            >
              <CircularProgress size={16} />
              <Typography variant="body2">Generating workflow...</Typography>
            </Box>
          )}
          {awaitingInput && !isGenerating && (
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1,
                color: "primary.main",
              }}
            >
              <Typography variant="body2" sx={{ fontStyle: "italic" }}>
                Please type your response above...
              </Typography>
            </Box>
          )}
        </Box>

        {/* Input area */}
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
            placeholder={awaitingInput ? "Type your response and press Enter..." : "Ask AI to generate your workflow..."}
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleChatSubmit();
              }
            }}
            disabled={isGenerating && !awaitingInput}
            InputProps={{
              endAdornment: (
                <IconButton
                  onClick={handleChatSubmit}
                  disabled={(isGenerating && !awaitingInput) || !chatInput.trim()}
                  size="small"
                  sx={{ mr: -1 }}
                  title={awaitingInput ? "Send response" : "Send message"}
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
      
      {/* Buttons - Below chatbot, horizontally aligned on the right */}
      <Box
        sx={{
          display: "flex",
          flexDirection: "row",
          justifyContent: "flex-end",
          gap: 1,
          flexShrink: 0,
          mb: 2, // Add margin bottom to prevent border clipping
        }}
      >
        {/* {!hasGeneratedWorkflow ? (
          // Analyze Button - Show before workflow is generated
          <Box
            sx={{
              borderRadius: "16px",
              background: theme.palette.mode === "dark"
                ? "linear-gradient(to bottom, rgba(63, 120, 176, 0.3) 0%, rgba(128, 187, 196, 0) 100%)"
                : "linear-gradient(to bottom, #3F78B0 0%, rgba(128, 187, 196, 0) 100%)",
              padding: "2px", // Reduced from 5px for minimalistic look
              marginBottom: "2px", // Add spacing to prevent border clipping
            }}
          >
            <Button
              variant="contained"
              onClick={() => {
                handleChatSubmit(true);
              }}
              disabled={isGenerating || isAnalyzing}
              sx={{
                textTransform: "none",
                borderRadius: "14px", // Inner radius (16px - 2px for border)
                px: 3,
                py: 1,
                bgcolor: theme.palette.mode === "dark" 
                  ? "rgba(255, 255, 255, 0.05)" 
                  : "#EBF2F5",
                color: "text.primary",
                fontWeight: 500,
                width: "100%",
                height: "100%",
                "&:hover": {
                  bgcolor: theme.palette.mode === "dark"
                    ? "rgba(255, 255, 255, 0.08)"
                    : "#E0E8EB",
                },
                "&:disabled": {
                  bgcolor: theme.palette.mode === "dark"
                    ? "rgba(255, 255, 255, 0.05)"
                    : "#EBF2F5",
                  opacity: 0.6,
                },
              }}
            >
              {isAnalyzing ? (
                <>
                  <CircularProgress size={16} sx={{ mr: 1, color: "inherit" }} />
                  Analyzing...
                </>
              ) : (
                "Analyze"
              )}
            </Button>
          </Box>
        ) : (
          // Accept/Decline Buttons - Show after workflow is generated
          <>
            <Box
              sx={{
                borderRadius: "16px",
                background: theme.palette.mode === "dark"
                  ? "linear-gradient(to bottom, rgba(63, 120, 176, 0.3) 0%, rgba(128, 187, 196, 0) 100%)"
                  : "linear-gradient(to bottom, #3F78B0 0%, rgba(128, 187, 196, 0) 100%)",
                padding: "2px", // Reduced from 5px for minimalistic look
              }}
            >
              <Button
                variant="outlined"
                onClick={onDecline}
                startIcon={<CloseIcon />}
                sx={{
                  textTransform: "none",
                  borderRadius: "14px", // Inner radius (16px - 2px for border)
                  px: 2,
                  py: 0.75,
                  bgcolor: theme.palette.mode === "dark"
                    ? "rgba(255, 255, 255, 0.05)"
                    : "#EBF2F5",
                  color: "text.primary",
                  border: "none",
                  width: "100%",
                  height: "100%",
                  "&:hover": {
                    bgcolor: theme.palette.mode === "dark"
                      ? "rgba(255, 255, 255, 0.08)"
                      : "#E0E8EB",
                  },
                }}
              >
                Decline
              </Button>
            </Box>
            <Box
              sx={{
                borderRadius: "16px",
                background: theme.palette.mode === "dark"
                  ? "linear-gradient(to bottom, rgba(63, 120, 176, 0.3) 0%, rgba(128, 187, 196, 0) 100%)"
                  : "linear-gradient(to bottom, #3F78B0 0%, rgba(128, 187, 196, 0) 100%)",
                padding: "2px", // Reduced from 5px for minimalistic look
              }}
            >
              <Button
                variant="contained"
                onClick={onAccept}
                startIcon={<CheckIcon />}
                sx={{
                  textTransform: "none",
                  borderRadius: "14px", // Inner radius (16px - 2px for border)
                  px: 2,
                  py: 0.75,
                  bgcolor: theme.palette.mode === "dark"
                    ? "rgba(255, 255, 255, 0.05)"
                    : "#EBF2F5",
                  color: "text.primary",
                  width: "100%",
                  height: "100%",
                  "&:hover": {
                    bgcolor: theme.palette.mode === "dark"
                      ? "rgba(255, 255, 255, 0.08)"
                      : "#E0E8EB",
                  },
                }}
              >
                Accept
              </Button>
            </Box>
          </>
        )} */}
      </Box>
    </Box>
  );
};

export default AIChatbot;

