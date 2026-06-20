import { Box, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";

const MetricCard = ({ title, subtitle, value, change }) => {
  const theme = useTheme();

  return (
    <Box sx={{ bgcolor: 'background.paper', border: "1px solid", borderColor: 'divider', borderRadius: 0, borderLeft: "none", p: 2 }}>
      <Typography variant="h6" sx={{ fontWeight: 600, fontSize: "0.9375rem", color: "text.primary", mb: 0.5 }}>
        {title}
      </Typography>
      <Typography variant="body2" sx={{ color: "text.secondary", fontSize: "0.75rem", mb: 1.5 }}>
        {subtitle}
      </Typography>
      <Typography variant="h5" sx={{ fontWeight: 600, color: "text.primary", mb: 0.75, fontSize: "1.75rem" }}>
        {value}
      </Typography>
      <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, flexWrap: "wrap" }}>
        <Typography
          variant="caption"
          sx={{
            color: "success.main",
            fontSize: "0.75rem",
            fontWeight: 600,
            bgcolor:"success.lighter",
            px: 0.75,
            py: 0.25,
            borderRadius: "2px",
          }}
        >
          {change}
        </Typography>
        <Typography variant="caption" sx={{ color: "text.secondary", fontSize: "0.75rem" }}>
          vs last month
        </Typography>
      </Box>
    </Box>
  );
};

export default MetricCard;

