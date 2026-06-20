import { Typography, Box, Chip, useTheme } from "@mui/material";

export function SLAComplianceChart({ data }) {
  const theme = useTheme();
  const size = 180;
  const strokeWidth = 20;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  
  // Calculate stroke-dasharray for each segment
  let currentOffset = 0;
  const segments = data.donutSegments.map((segment) => {
    const dashLength = (segment.percent / 100) * circumference;
    const offset = currentOffset;
    currentOffset += dashLength;
    return { ...segment, dashLength, offset };
  });

  const bgCircleColor = theme.palette.mode === 'dark' 
    ? theme.palette.background.elevation2 
    : theme.palette.background.elevation1;

  return (
    <Box
      sx={{
        bgcolor: 'background.elevation1',
        p: 2.5,
        display: 'flex',
        flexDirection: 'column',
        borderRadius: 2,
        height: '100%',
      }}
    >
      <Typography
        variant="h6"
        sx={{
          fontSize: '1.25rem',
          fontWeight: 700,
          color: 'text.primary',
          mb: 3,
        }}
      >
        SLA compliance(%)
      </Typography>
      
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 4,
          flex: 1,
          flexDirection: { xs: 'column', md: 'row' },
        }}
      >
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            gap: 2.5,
          }}
        >
          {data.stats.map((stat, idx) => (
            <Box
              key={idx}
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 1.5,
                py: 1,
                borderBottom: '1px solid',
                borderColor: 'divider',
              }}
            >
              <Box
                sx={{
                  width: '0.25rem',
                  height: '2rem',
                  borderRadius: '2px',
                  bgcolor: stat.color,
                }}
              />
              <Typography
                sx={{
                  fontSize: '0.9375rem',
                  color: 'text.primary',
                  minWidth: '5rem',
                }}
              >
                {stat.label}
              </Typography>
              <Typography
                sx={{
                  fontSize: '1.125rem',
                  fontWeight: 600,
                  color: 'text.primary',
                  minWidth: '4rem',
                }}
              >
                {stat.value}
              </Typography>
              <Chip
                label={`${stat.change}×`}
                size="small"
                color="success"
                variant="soft"
                sx={{
                  fontSize: '0.75rem',
                  fontWeight: 500,
                  height: 'auto',
                  py: 0.5,
                }}
              />
            </Box>
          ))}
        </Box>
        
        <Box
          sx={{
            position: 'relative',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Box
            component="svg"
            width={size}
            height={size}
            viewBox={`0 0 ${size} ${size}`}
            sx={{
              transform: 'rotate(0deg)',
            }}
          >
            {/* Background circle */}
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke={bgCircleColor}
              strokeWidth={strokeWidth}
            />
            
            {/* Segments */}
            {segments.map((segment, idx) => (
              <circle
                key={idx}
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="none"
                stroke={segment.color}
                strokeWidth={strokeWidth}
                strokeDasharray={`${segment.dashLength} ${circumference - segment.dashLength}`}
                strokeDashoffset={-segment.offset}
                transform={`rotate(-90 ${size / 2} ${size / 2})`}
                strokeLinecap="round"
              />
            ))}
          </Box>
          <Box
            sx={{
              position: 'absolute',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              textAlign: 'center',
            }}
          >
            <Typography
              sx={{
                fontSize: '2.5rem',
                fontWeight: 700,
                color: 'text.primary',
                lineHeight: 1,
              }}
            >
              {data.overall}%
            </Typography>
            <Typography
              sx={{
                fontSize: '0.75rem',
                color: 'text.secondary',
                maxWidth: '6rem',
                textAlign: 'center',
                mt: 0.25,
              }}
            >
              SLA Compliance Insight
            </Typography>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}

