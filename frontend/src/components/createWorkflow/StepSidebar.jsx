import { Box, Typography, IconButton } from "@mui/material";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import StepIndicator from "./StepIndicator";
import AIChatbot from "./AIChatbot";

const STEP_SIDEBAR_COLLAPSED_WIDTH = 64;
const STEP_SIDEBAR_DEFAULT_WIDTH = 360; // Default width when chatbot is not visible
// Chatbot width is 40vh, plus sidebar padding (24px left + 24px right = 48px) + left margin (32px) = 80px total
// Width should just fit the chatbot with padding
const STEP_SIDEBAR_WITH_CHATBOT_WIDTH = "calc(30vw + 80px)";

const StepSidebar = ({
  steps,
  currentStep,
  isSidebarCollapsed,
  onToggleCollapse,
  getStepStatus,
  formData,
  onWorkflowGenerated,
  isGenerating,
  setIsGenerating,
  currentStepValue,
  onAcceptWorkflow,
  onDeclineWorkflow,
  chatMessages = [],
  onSendMessage,
  awaitingInput = false,
}) => {
  // Determine if chatbot is visible (step 2 and sidebar not collapsed)
  const isChatbotVisible = currentStepValue === 2 && !isSidebarCollapsed;
  
  // Calculate dynamic width
  const sidebarWidth = isSidebarCollapsed 
    ? STEP_SIDEBAR_COLLAPSED_WIDTH 
    : isChatbotVisible 
      ? STEP_SIDEBAR_WITH_CHATBOT_WIDTH 
      : STEP_SIDEBAR_DEFAULT_WIDTH;

  return (
    <Box
      sx={{
        width: sidebarWidth,
        bgcolor: "background.paper",
        borderRight: "1px solid",
        borderColor: "divider",
        px: isSidebarCollapsed ? 1.5 : 3,
        pt: 4,
        pb: 3,
        display: "flex",
        flexDirection: "column",
        position: currentStepValue === 1 ? "relative" : "absolute",
        left: currentStepValue === 1 ? "auto" : 0,
        top: currentStepValue === 1 ? "auto" : 0,
        bottom: currentStepValue === 1 ? "auto" : 0,
        zIndex: currentStepValue === 1 ? "auto" : 10002,
        flexShrink: currentStepValue === 1 ? 0 : "none",
        transition: "width 0.3s ease, padding 0.3s ease, position 0.3s ease",
        boxShadow: currentStepValue === 1 || isSidebarCollapsed ? "none" : "2px 0 8px rgba(0, 0, 0, 0.1)",
      }}
    >
      {/* Toggle Button */}
      <IconButton
        onClick={onToggleCollapse}
        sx={{
          position: "absolute",
          top: "50%",
          right: -16,
          transform: "translateY(-50%)",
          width: 32,
          height: 32,
          bgcolor: "background.paper",
          border: "1px solid",
          borderColor: "divider",
          boxShadow: 1,
          zIndex: 10003,
          "&:hover": {
            bgcolor: "action.hover",
          },
        }}
      >
        {isSidebarCollapsed ? (
          <ChevronRightIcon sx={{ fontSize: 18 }} />
        ) : (
          <ChevronLeftIcon sx={{ fontSize: 18 }} />
        )}
      </IconButton>

      <Box sx={{ flex: 1, overflow: "hidden" }}>
        {!isSidebarCollapsed && (
          <Typography
            variant="h6"
            sx={{
              fontWeight: 700,
              color: "text.primary",
              mb: 3,
              transition: "opacity 0.2s ease",
            }}
          >
            Details
          </Typography>
        )}
        
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5, position: "relative" }}>
          {steps.map((step, index) => {
            const isLastStep = index === steps.length - 1;
            const stepStatus = getStepStatus(step.id);
            const isStep2WithChatbot = step.id === 2 && currentStepValue === 2;
            
            return (
              <StepIndicator
                key={step.id}
                step={step}
                stepStatus={stepStatus}
                isSidebarCollapsed={isSidebarCollapsed}
                isLastStep={isLastStep}
                isStep2WithChatbot={isStep2WithChatbot}
              >
                {/* AI Chatbot - Show inline with step 2 */}
                {!isSidebarCollapsed && step.id === 2 && currentStepValue === 2 && (
                  <Box
                    sx={{
                      ml: "32px",
                      mt: 2,
                      mb: 1,
                      display: "flex",
                      justifyContent: "center",
                      alignItems: "flex-start",
                    }}
                  >
                    <AIChatbot
                      formData={formData}
                      onWorkflowGenerated={onWorkflowGenerated}
                      isGenerating={isGenerating}
                      setIsGenerating={setIsGenerating}
                      onAccept={onAcceptWorkflow}
                      onDecline={onDeclineWorkflow}
                      chatMessages={chatMessages}
                      onSendMessage={onSendMessage}
                      awaitingInput={awaitingInput}
                    />
                  </Box>
                )}
              </StepIndicator>
            );
          })}
        </Box>
      </Box>
    </Box>
  );
};

export { STEP_SIDEBAR_COLLAPSED_WIDTH, STEP_SIDEBAR_DEFAULT_WIDTH };
export default StepSidebar;

