import { Typography, Box, useTheme } from "@mui/material";

export function RCAChart({ data = {} }) {
  const theme = useTheme();
  
  // Ensure data has required structure
  const safeData = {
    total: data?.total || 0,
    time_series: data?.time_series || {
      labels: ["10:00 AM", "11:00 AM", "12:00 PM", "1:00 PM", "2:00 PM", "3:00 PM"],
      datasets: [{ color: "#A2B8F4", values: [0, 0, 0, 0, 0, 0] }],
    },
    stats: data?.stats || [],
  };

  const chartHeight = 200;
  const chartWidth = 500;
  const padding = { top: 20, right: 20, bottom: 40, left: 40 };

  const innerWidth = chartWidth - padding.left - padding.right;
  const innerHeight = chartHeight - padding.top - padding.bottom;

  const labels = safeData.time_series.labels;
  const values = safeData.time_series.datasets[0]?.values || [];
  const maxValue = Math.max(...values, 10); // At least 10 for scale
  const minValue = 0;

  const xStep = labels.length > 1 ? innerWidth / (labels.length - 1) : innerWidth;

  const getY = (value) => {
    return (
      padding.top +
      innerHeight -
      ((value - minValue) / (maxValue - minValue)) * innerHeight
    );
  };

  const getPath = (vals) => {
    return vals
      .map((val, i) => {
        const x = padding.left + i * xStep;
        const y = getY(val);
        return `${i === 0 ? "M" : "L"} ${x} ${y}`;
      })
      .join(" ");
  };

  const dividerColor = theme.palette.divider;
  const textSecondaryColor = theme.palette.text.secondary;

  return (
    <Box
      sx={{
        bgcolor: "background.elevation1",
        p: 2.5,
        display: "flex",
        flexDirection: "column",
        borderRadius: 2,
        height: "100%",
      }}
    >
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          mb: 2,
        }}
      >
        <Box>
          <Typography
            variant="h6"
            sx={{
              fontSize: "1.25rem",
              fontWeight: 700,
              color: "text.primary",
              mb: 0.25,
            }}
          >
            RCA Triggers
          </Typography>
          <Typography
            variant="body2"
            sx={{
              fontSize: "0.875rem",
              color: "text.secondary",
            }}
          >
            Root cause analysis triggers over time
          </Typography>
        </Box>
        <Box
          sx={{
            bgcolor: "background.elevation2",
            px: 2,
            py: 1,
            borderRadius: 1,
            textAlign: "center",
          }}
        >
          <Typography
            sx={{
              fontSize: "1.5rem",
              fontWeight: 700,
              color: "text.primary",
              lineHeight: 1,
            }}
          >
            {safeData.total}
          </Typography>
          <Typography
            sx={{
              fontSize: "0.625rem",
              color: "text.secondary",
              textTransform: "uppercase",
            }}
          >
            Total
          </Typography>
        </Box>
      </Box>

      <Box
        sx={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Box
          component="svg"
          viewBox={`0 0 ${chartWidth} ${chartHeight}`}
          sx={{
            width: "100%",
            height: "auto",
            maxHeight: "15rem",
          }}
        >
          {/* Horizontal grid lines */}
          {[...Array(5)].map((_, i) => {
            const val = minValue + ((maxValue - minValue) / 4) * i;
            return (
              <g key={i}>
                <line
                  x1={padding.left}
                  y1={getY(val)}
                  x2={chartWidth - padding.right}
                  y2={getY(val)}
                  stroke={dividerColor}
                  strokeWidth="1"
                />
                <text
                  x={padding.left - 10}
                  y={getY(val) + 4}
                  fill={textSecondaryColor}
                  fontSize="10"
                  textAnchor="end"
                >
                  {Math.round(val)}
                </text>
              </g>
            );
          })}

          {/* Vertical grid lines */}
          {labels.map((label, i) => (
            <line
              key={i}
              x1={padding.left + i * xStep}
              y1={padding.top}
              x2={padding.left + i * xStep}
              y2={chartHeight - padding.bottom}
              stroke={dividerColor}
              strokeWidth="1"
            />
          ))}

          {/* Border */}
          <rect
            x={padding.left}
            y={padding.top}
            width={innerWidth}
            height={innerHeight}
            fill="none"
            stroke={dividerColor}
            strokeWidth="1"
          />

          {/* Area fill */}
          <path
            d={`${getPath(values)} L ${padding.left + (values.length - 1) * xStep} ${
              chartHeight - padding.bottom
            } L ${padding.left} ${chartHeight - padding.bottom} Z`}
            fill={safeData.time_series.datasets[0]?.color || "#A2B8F4"}
            opacity={0.2}
          />

          {/* Line */}
          <path
            d={getPath(values)}
            fill="none"
            stroke={safeData.time_series.datasets[0]?.color || "#A2B8F4"}
            strokeWidth="2"
          />

          {/* Data points */}
          {values.map((val, i) => (
            <circle
              key={i}
              cx={padding.left + i * xStep}
              cy={getY(val)}
              r={4}
              fill={safeData.time_series.datasets[0]?.color || "#A2B8F4"}
            />
          ))}

          {/* X-axis labels */}
          {labels.map((label, i) => (
            <text
              key={i}
              x={padding.left + i * xStep}
              y={chartHeight - 10}
              fill={textSecondaryColor}
              fontSize="9"
              textAnchor="middle"
            >
              {label}
            </text>
          ))}
        </Box>
      </Box>

      {/* Stats breakdown */}
      {safeData.stats.length > 0 && (
        <Box
          sx={{
            display: "flex",
            flexWrap: "wrap",
            gap: 2,
            mt: 2,
            pt: 2,
            borderTop: "1px solid",
            borderColor: "divider",
          }}
        >
          {safeData.stats.slice(0, 4).map((stat, idx) => (
            <Box
              key={idx}
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1,
              }}
            >
              <Typography
                sx={{
                  fontSize: "0.75rem",
                  color: "text.secondary",
                }}
              >
                {stat.workflow}:
              </Typography>
              <Typography
                sx={{
                  fontSize: "0.875rem",
                  fontWeight: 600,
                  color: "text.primary",
                }}
              >
                {stat.count}
              </Typography>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
}
