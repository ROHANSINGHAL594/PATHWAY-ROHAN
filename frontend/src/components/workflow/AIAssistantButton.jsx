import { Box, Button, keyframes, Typography } from "@mui/material";
import AutoAwesomeOutlinedIcon from "@mui/icons-material/AutoAwesomeOutlined";
import { useTheme } from "@mui/material/styles";

// Animated gradient border keyframes - rotating through colors
const gradientRotate = keyframes`
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

// Shining/glowing effect for the border
const borderShine = keyframes`
  0%, 100% {
    opacity: 0.8;
    filter: brightness(1);
  }
  50% {
    opacity: 1;
    filter: brightness(1.3);
  }
`;

const AIAssistantButton = ({ onClick }) => {
  const theme = useTheme();

  return (
    <Box
      sx={{
        position: "fixed",
        bottom: 40,
        left: 100,
        zIndex: 1000,
      }}
    >
      {/* Gradient border wrapper */}
      <Box
        sx={{
          position: "relative",
          borderRadius: "24px", // Pill shape
          padding: "3px", // Border width
          background: "linear-gradient(90deg, #00BCD4 0%, #4CAF50 30%, #FFEB3B 60%, #FF9800 100%)",
          backgroundSize: "200% 100%",
          animation: `${gradientRotate} 3s ease infinite, ${borderShine} 2s ease-in-out infinite`,
          boxShadow: "0 2px 8px rgba(0, 0, 0, 0.15)",
          "&:hover": {
            boxShadow: "0 4px 12px rgba(0, 0, 0, 0.2)",
            transform: "translateY(-2px)",
          },
          transition: "all 0.3s ease",
        }}
      >
        {/* White inner button */}
        <Button
          onClick={onClick}
          disableRipple
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1,
            bgcolor: "white",
            borderRadius: "21px", // 24px - 3px padding
            px: 2.5,
            py: 1,
            border: "none",
            cursor: "pointer",
            minWidth: "auto",
            textTransform: "none",
            "&:hover": {
              bgcolor: "#fafafa",
            },
            "&:active": {
              bgcolor: "#f5f5f5",
            },
            transition: "background-color 0.2s ease",
          }}
        >
          {/* Sparkle icons */}
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: 0.3,
              position: "relative",
              width: 24,
              height: 24,
            }}
          >
            {/* Large sparkle in center */}
            <AutoAwesomeOutlinedIcon
              sx={{
                fontSize: 18,
                color: "#333",
                position: "absolute",
                top: "50%",
                left: "50%",
                transform: "translate(-50%, -50%)",
              }}
            />
            {/* Small sparkle above */}
            <AutoAwesomeOutlinedIcon
              sx={{
                fontSize: 10,
                color: "#333",
                position: "absolute",
                top: 0,
                left: "50%",
                transform: "translateX(-50%)",
              }}
            />
            {/* Small sparkle below */}
            <AutoAwesomeOutlinedIcon
              sx={{
                fontSize: 10,
                color: "#333",
                position: "absolute",
                bottom: 0,
                left: "50%",
                transform: "translateX(-50%)",
              }}
            />
          </Box>
          
          {/* AI Text */}
          <Typography
            component="span"
            sx={{
              fontSize: "0.9375rem",
              fontWeight: 700,
              color: "#333",
              letterSpacing: "0.02em",
            }}
          >
            AI
          </Typography>
        </Button>
      </Box>
    </Box>
  );
};

export default AIAssistantButton;

