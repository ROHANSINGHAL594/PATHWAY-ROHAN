import { Box, Typography, Button } from "@mui/material";
import { ArrowForward as ArrowForwardIcon } from "@mui/icons-material";
import { useNavigate } from "react-router-dom";
import pipelineImage from "../../assets/workflowImage.png";

const PipelinePreview = ({ workflowId }) => {
  const navigate = useNavigate();

  return (
    <Box 
      onClick={() => navigate(`/workflows/${workflowId}`)}
      sx={{ 
        bgcolor: 'background.paper', 
        border: "1px solid", 
        borderColor: 'divider', 
        borderRadius: 0, 
        p: 2,
        background: 'linear-gradient(to bottom, rgba(135, 206, 250, 0.02) 0%, rgba(135, 206, 250, 0.05) 50%, rgba(135, 206, 250, 0.15) 100%)',
        cursor: "pointer",
        transition: "all 0.2s ease",
        "&:hover": {
          borderColor: "primary.main",
          background: 'linear-gradient(to bottom, rgba(135, 206, 250, 0.05) 0%, rgba(135, 206, 250, 0.1) 50%, rgba(135, 206, 250, 0.2) 100%)',
        },
      }}
    >
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1.5 }}>
        <Typography variant="h6" sx={{ fontWeight: 600, fontSize: "0.9375rem", color: "text.primary" }}>
          Pipeline
        </Typography>
        <Button
          variant="text"
          size="small"
          endIcon={<ArrowForwardIcon sx={{ fontSize: 14 }} />}
          onClick={(e) => {
            e.stopPropagation();
            navigate(`/workflows/${workflowId}`);
          }}
          sx={{
            minWidth: "auto",
            color: 'primary.main',
            bgcolor: 'rgba(25, 118, 210, 0.08)',
            px: 1.5,
            py: 0.5,
            borderRadius: "6px",
            '&:hover': {
              bgcolor: 'rgba(25, 118, 210, 0.16)',
            },
          }}
        >
          Open
        </Button>
      </Box>
      <Box
        sx={{
          height: 150,
          overflow: "hidden",
          borderRadius: "4px",
        }}
      >
        <img 
          src={pipelineImage} 
          alt="Pipeline Preview"
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'contain',
            display: 'block',
          }}
        />
      </Box>
    </Box>
  );
};

export default PipelinePreview;

