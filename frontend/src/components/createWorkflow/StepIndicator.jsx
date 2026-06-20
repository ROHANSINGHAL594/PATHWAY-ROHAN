import { Box, Typography } from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import aiIcon from "../../assets/ai_icon.svg";

const StepIndicator = ({
  step,
  stepStatus,
  isSidebarCollapsed,
  isLastStep,
  isStep2WithChatbot,
  children, // For chatbot or other content
}) => {
  const isCompleted = stepStatus === "completed";
  const isCurrent = stepStatus === "current";

  return (
    <Box sx={{ display: "flex", flexDirection: "column", position: "relative", zIndex: 1 }}>
      {/* Connecting line segment - rendered after step content */}
      {!isLastStep && !isSidebarCollapsed && (
        <Box
          sx={{
            position: "absolute",
            left: "11px",
            top: isStep2WithChatbot ? "56px" : "48px",
            bottom: isStep2WithChatbot ? "-16px" : "-20px",
            width: 2,
            borderRadius: 1,
            bgcolor: isCompleted 
              ? "success.main" 
              : (theme) => theme.palette.dividerLight,
            zIndex: 0,
          }}
        />
      )}
      
      <Box
        sx={{
          display: "flex",
          alignItems: "flex-start",
          gap: 2,
          py: 1,
          justifyContent: isSidebarCollapsed ? "center" : "flex-start",
          position: "relative",
          zIndex: 2,
        }}
      >
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
            position: "relative",
            zIndex: 3,
            bgcolor: "background.paper",
            borderRadius: "50%",
          }}
        >
          {isCompleted ? (
            <CheckCircleIcon
              sx={{
                color: "success.main",
                fontSize: 24,
              }}
            />
          ) : (
            <Box
              sx={{
                width: 24,
                height: 24,
                borderRadius: "50%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 14,
                fontWeight: 500,
                bgcolor: isCurrent 
                  ? "primary.main" 
                  : "action.hover",
                color: isCurrent 
                  ? "common.white" 
                  : "text.primary",
              }}
            >
              {step.id}
            </Box>
          )}
        </Box>
        {!isSidebarCollapsed && (
          <Box 
            sx={{ 
              display: "flex", 
              flexDirection: "column", 
              gap: 0.125,
              opacity: 1,
              transition: "opacity 0.2s ease",
              flex: 1,
            }}
          >
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <Typography
                variant="body2"
                sx={{
                  color: "text.primary",
                  fontWeight: isCompleted ? 600 : 500,
                }}
              >
                {step.label}
              </Typography>
              {step.id === 2 && (
                <Box
                  component="img"
                  src={aiIcon}
                  alt="AI"
                  sx={{
                    width: 16,
                    height: 16,
                  }}
                />
              )}
            </Box>
          </Box>
        )}
      </Box>
      
      {/* Additional content (like chatbot) */}
      {children}
      
      {/* Collapsed state line */}
      {!isLastStep && isSidebarCollapsed && (
        <Box
          sx={{
            width: 2,
            height: 32,
            mx: "auto",
            my: 0.75,
            borderRadius: 1,
            bgcolor: isCompleted 
              ? "success.main" 
              : (theme) => theme.palette.dividerLight,
          }}
        />
      )}
    </Box>
  );
};

export default StepIndicator;

