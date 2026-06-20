import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Box,
  Typography,
  Tabs,
  Tab,
  CircularProgress,
  AppBar,
  Toolbar,
  IconButton,
  Paper,
  Grid,
  Button, // <-- Import Button
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { DataGrid } from "@mui/x-data-grid";

// --- Stub Components (Now more professional) ---

// 1. Logs Panel
function LogsPanel({ data }) {
  return (
    <Paper sx={{ p: 3, mt: 2 }}>
      <Typography variant="h5" gutterBottom>
        Execution Logs
      </Typography>

      {/* This Box is the black container. It's a <div>. */}
      <Box
        sx={{
          bgcolor: "grey.900",
          color: "grey.100",
          p: 2, // Apply padding to this container
          borderRadius: 1,
          overflowX: "auto", // The container itself will scroll
          maxHeight: "50vh",
        }}
      >
        {/* The <pre> tag just holds the text and respects whitespace */}
        <pre
          style={{
            fontFamily: "monospace",
            margin: 0, // Reset default <pre> margin
          }}
        >
          {JSON.stringify(data.logs, null, 2)}
        </pre>
      </Box>
    </Paper>
  );
}
// 2. Charts Panel
function ChartsPanel({ data }) {
  // (This component is unchanged)
  return (
    <Paper sx={{ p: 3, mt: 2 }}>
      <Typography variant="h5" gutterBottom>
        Performance Metrics
      </Typography>
      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          <Paper
            sx={{
              p: 2,
              height: 300,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              bgcolor: "grey.100",
            }}
          >
            <Typography variant="body1">
              Chart: Execution Time (Placeholder)
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={6}>
          <Paper
            sx={{
              p: 2,
              height: 300,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              bgcolor: "grey.100",
            }}
          >
            <Typography variant="body1">
              Chart: Success Rate (Placeholder)
            </Typography>
          </Paper>
        </Grid>
      </Grid>
    </Paper>
  );
}

// 3. History Panel (using a data grid for a pro look)
function HistoryPanel({ data }) {
  // (This component is unchanged)
  const columns = [
    { field: "id", headerName: "Run ID", width: 150 },
    { field: "status", headerName: "Status", width: 120 },
    { field: "timestamp", headerName: "Timestamp", width: 200 },
    { field: "triggeredBy", headerName: "Triggered By", width: 150 },
  ];

  const rows = [
    {
      id: "run_a1b2",
      status: "Success",
      timestamp: "2025-11-06T14:30:00Z",
      triggeredBy: "admin@user.com",
    },
    {
      id: "run_c3d4",
      status: "Failed",
      timestamp: "2025-11-06T12:15:00Z",
      triggeredBy: "api",
    },
    {
      id: "run_e5f6",
      status: "Success",
      timestamp: "2025-11-05T18:00:00Z",
      triggeredBy: "admin@user.com",
    },
  ];

  return (
    <Paper sx={{ p: 3, mt: 2, height: 600, width: "100%" }}>
      <Typography variant="h5" gutterBottom>
        Run History
      </Typography>
      <DataGrid
        rows={rows}
        columns={columns}
        pageSizeOptions={[5, 10]}
        checkboxSelection
        disableRowSelectionOnClick
      />
    </Paper>
  );
}

// 4. Human in the Loop (HITL) Panel -- NOW WORKING
function HumanInLoopPanel({ data }) {
  const handleApprove = (reportId) => {
    console.log(`Approving report ${reportId}...`);
    // Add your API call here
    alert(`Approving report ${reportId}`);
  };

  const handleReject = (reportId) => {
    console.log(`Rejecting report ${reportId}...`);
    // Add your API call here
    alert(`Rejecting report ${reportId}`);
  };

  return (
    <Paper sx={{ p: 3, mt: 2 }}>
      <Typography variant="h5" gutterBottom>
        Pending Actions
      </Typography>
      <Box>
        <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
          <Typography variant="h6">Approve Expense Report #451</Typography>
          <Typography variant="body2" sx={{ mb: 2 }}>
            Assigned to: you
          </Typography>
          <Button
            variant="contained"
            sx={{ mr: 1 }}
            onClick={() => handleApprove(451)}
          >
            Approve
          </Button>
          <Button
            variant="outlined"
            color="error"
            onClick={() => handleReject(451)}
          >
            Reject
          </Button>
        </Paper>
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="h6">
            Verify User Registration: 'test@user.com'
          </Typography>
          <Typography variant="body2" sx={{ mb: 2 }}>
            Assigned to: review_team
          </Typography>
          <Button variant="contained" disabled>
            Claim Task
          </Button>
        </Paper>
      </Box>
    </Paper>
  );
}

// --- Main Analytics Page Component ---

export default function NotificationPage() {
  const [tab, setTab] = useState("logs");
  const [loading, setLoading] = useState(false);
  const [analyticsData, setAnalyticsData] = useState(null);

  const { flowId } = useParams();
  const navigate = useNavigate();

  useEffect(() => {
    if (flowId) {
      const fetchAnalytics = async () => {
        setLoading(true);
        try {
          // Mock data for demonstration
          const mockData = {
            id: flowId,
            logs: [
              {
                timestamp: "2025-11-12T12:00:00Z",
                level: "info",
                message: "Flow started",
              },
              {
                timestamp: "2025-11-12T12:00:01Z",
                level: "info",
                message: "Fetching data...",
              },
              {
                timestamp: "2025-11-12T12:00:02Z",
                level: "info",
                message: "Data fetched successfully",
              },
              {
                timestamp: "2025-11-12T12:00:03Z",
                level: "info",
                message: "Processing completed",
              },
              {
                timestamp: "2025-11-12T12:00:03Z",
                level: "info",
                message: "Flow finished with status: SUCCESS",
              },
            ],
          };
          await new Promise((resolve) => setTimeout(resolve, 500));
          setAnalyticsData(mockData);
        } catch (error) {
          console.error("Failed to fetch analytics:", error);
          setAnalyticsData(null);
        } finally {
          setLoading(false);
        }
      };

      fetchAnalytics();
    }
  }, [flowId]);

  const handleTabChange = (event, newValue) => {
    setTab(newValue);
  };

  const handleClose = () => {
    navigate("/"); // Go back to the dashboard
  };

  return (
    <Box sx={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      <AppBar
        position="static"
        color="inherit"
        elevation={1}
        sx={{
          borderBottom: 1,
          borderColor: "divider",
          bgcolor: "background.paper",
        }}
      >
        <Toolbar
          sx={{
            display: "flex",
            height: "12vh",
            justifyContent: "space-between",
          }}
        >
          <Typography variant="h6" color="text.primary" sx={{ px: 3 }}>
            {" "}
            {/* Added padding */}
            Flow Analytics {flowId && `(ID: ${flowId.slice(0, 8)}...)`}
          </Typography>
          <IconButton
            edge="in_0"
            color="inherit"
            onClick={handleClose}
            aria-label="close"
            sx={{ mr: 2 }} // Added margin
          >
            <CloseIcon />
          </IconButton>
        </Toolbar>
      </AppBar>

      {/* --- TABS BAR FIX --- */}
      <Box
        sx={{
          borderBottom: 1,
          borderColor: "divider",
          bgcolor: "background.paper",
          px: 3,
        }}
      >
        {/* Removed <Container> and added px: 3 to the Box */}
        <Tabs value={tab} onChange={handleTabChange}>
          <Tab label="Logs" value="logs" />
          <Tab label="Charts" value="charts" />
          <Tab label="History" value="history" />
          <Tab label="Human in the Loop" value="hitl" />
        </Tabs>
      </Box>

      {/* --- MAIN CONTENT AREA FIX --- */}
      <Box
        sx={{
          flexGrow: 1,
          overflow: "auto",
          bgcolor: "background.default", // Light grey background
          py: 2, // Add vertical padding
          px: 3, // Add horizontal padding
        }}
      >
        {/* Removed <Container> and added px: 3 to the Box */}
        {loading && (
          <Box
            sx={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              height: "100%",
              mt: 5,
            }}
          >
            <CircularProgress />
          </Box>
        )}

        {!loading && analyticsData && (
          <>
            {tab === "logs" && <LogsPanel data={analyticsData} />}
            {tab === "charts" && <ChartsPanel data={analyticsData} />}
            {tab === "history" && <HistoryPanel data={analyticsData} />}
            {tab === "hitl" && <HumanInLoopPanel data={analyticsData} />}
          </>
        )}

        {!loading && !analyticsData && (
          <Paper sx={{ p: 3, mt: 2 }}>
            <Typography>No analytics data available for this flow.</Typography>
          </Paper>
        )}
      </Box>
    </Box>
  );
}
