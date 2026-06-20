import { Typography, Box, useTheme } from "@mui/material";
import { BarChart } from "@mui/x-charts/BarChart";

export function RuntimeChart({ data = [] }) {
  const theme = useTheme();
  
  // Ensure data is an array
  const safeData = Array.isArray(data) ? data : [];
  
  // If no data, show empty state
  if (safeData.length === 0) {
    return (
      <Box
        sx={{
          bgcolor: "background.elevation1",
          p: 4,
          display: "flex",
          flexDirection: "column",
          borderRadius: 2,
          height: "100%",
        }}
      >
        <Typography
          variant="h6"
          sx={{
            fontSize: "1.25rem",
            fontWeight: 700,
            color: "text.primary",
            mb: 0.25,
          }}
        >
          Runtime per Pipeline
        </Typography>
        <Typography
          variant="body2"
          sx={{
            fontSize: "0.875rem",
            color: "text.secondary",
            mb: 2,
          }}
        >
          Total runtime for each pipeline
        </Typography>
        <Box
          sx={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "text.secondary",
          }}
        >
          <Typography>No pipeline data available</Typography>
        </Box>
      </Box>
    );
  }

  // Transform data for BarChart
  const chartDataset = safeData.map((item) => ({
    pipeline: item.pipeline,
    runtime: item.runtime_hours || 0,
  }));

  return (
        <Box
          sx={{
            bgcolor: "background.elevation1",
            p: 4,
            display: "flex",
            flexDirection: "column",
            borderRadius: 2,
            height: "100%",
          }}
        >
      <Typography
        variant="h6"
        sx={{
          fontSize: "1.25rem",
          fontWeight: 700,
          color: "text.primary",
          mb: 0.25,
        }}
      >
        Runtime per Pipeline
      </Typography>
      <Typography
        variant="body2"
        sx={{
          fontSize: "0.875rem",
          color: "text.secondary",
          mb: 2,
        }}
      >
        Total runtime for each pipeline (hours)
      </Typography>

      <Box
        sx={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          minHeight: 250,
        }}
      >
        <BarChart
          dataset={chartDataset}
          xAxis={[
            {
              scaleType: "band",
              dataKey: "pipeline",
              tickLabelStyle: {
                fontSize: 10,
                fill: theme.palette.text.secondary,
              },
              categoryGapRatio: 0.8,
            },
          ]}
          yAxis={[
            {
              tickLabelStyle: {
                fontSize: 10,
                fill: theme.palette.text.secondary,
              },
              label: "Hours",
            },
          ]}
          series={[
            {
              dataKey: "runtime",
              label: "Runtime",
              color: "#86C8BC",
            },
          ]}
          slotProps={{
            legend: {
              hidden: true,
            },
          }}
          margin={{ top: 20, right: 20, bottom: 40, left: 15 }}
          sx={{
            "& .MuiChartsAxis-line": {
              stroke: theme.palette.divider,
            },
            "& .MuiChartsAxis-tick": {
              stroke: theme.palette.divider,
            },
            "& .MuiChartsBar-root": {
              width: "50% !important",
            },
          }}
        />
      </Box>
    </Box>
  );
}
