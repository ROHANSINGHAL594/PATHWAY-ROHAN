import { Typography, Box, useTheme } from "@mui/material";

export function MTTRChart({ data = {} }) {
  const theme = useTheme();

  // Ensure data has required structure
  const safeData = {
    labels: data?.labels || [
      "10:00 AM",
      "11:00 AM",
      "12:00 PM",
      "1:00 PM",
      "2:00 PM",
      "3:00 PM",
    ],
    datasets: data?.datasets || [
      { color: "#4ade80", values: [0, 0, 0, 0, 0, 0] },
    ],
  };

  const maxValue = 60;
  const minValue = 0;
  const chartHeight = 200;
  const chartWidth = 500;
  const padding = { top: 20, right: 20, bottom: 40, left: 40 };

  const innerWidth = chartWidth - padding.left - padding.right;
  const innerHeight = chartHeight - padding.top - padding.bottom;

  const xStep =
    safeData.labels.length > 1
      ? innerWidth / (safeData.labels.length - 1)
      : innerWidth;

  const getY = (value) => {
    return (
      padding.top +
      innerHeight -
      ((value - minValue) / (maxValue - minValue)) * innerHeight
    );
  };

  const getPath = (values) => {
    return values
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
          height: "100%",
          display: "flex",
          flexDirection: "column",
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
          MTTR
        </Typography>
        <Typography
          variant="body2"
          sx={{
            fontSize: "0.875rem",
            color: "text.secondary",
            mb: 2,
          }}
        >
          Total profit gained
        </Typography>

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
            {/* Grid lines */}
            {[60, 45, 30, 15].map((val) => (
              <g key={val}>
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
                  {val}
                </text>
              </g>
            ))}

            {/* Vertical grid lines */}
            {data.labels.map((label, i) => (
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

            {/* Lines */}
            {data.datasets.map((dataset, idx) => (
              <path
                key={idx}
                d={getPath(dataset.values)}
                fill="none"
                stroke={dataset.color}
                strokeWidth="2"
              />
            ))}

            {/* X-axis labels */}
            {data.labels.map((label, i) => (
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
      </Box>
    </Box>
  );
}
