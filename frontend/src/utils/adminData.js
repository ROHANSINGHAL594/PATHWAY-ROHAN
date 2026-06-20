import PieChartOutlineIcon from "@mui/icons-material/PieChartOutline";
import AutoGraphIcon from "@mui/icons-material/AutoGraph";
import EqualizerIcon from "@mui/icons-material/Equalizer";
import PercentIcon from "@mui/icons-material/Percent";

// Mock data for KPI cards
export const kpiData = [
  {
    id: 1,
    title: "Pipeline Running",
    value: "35",
    description: "Total number of pipeline running",
    icon: PieChartOutlineIcon,
    iconClass: "blue",
  },
  {
    id: 2,
    title: "MTTR",
    value: "32 min",
    description: "Average Time",
    icon: AutoGraphIcon,
    iconClass: "blue",
  },
  {
    id: 3,
    title: "Alerts",
    value: "07",
    description: "No. of alerts today",
    icon: EqualizerIcon,
    iconClass: "blue",
    cardClass: "alerts",
  },
  {
    id: 4,
    title: "SLA Compliance",
    value: "92.4%",
    description: "SLA Compliance Insights",
    icon: PercentIcon,
    iconClass: "blue",
  },
];

// Mock data for alerts chart (values based on y-axis 10-35)
export const alertsChartData = [
  { workflow: "Workflow A", warning: 20, critical: 12, low: 17 },
  { workflow: "Workflow B", warning: 19, critical: 14, low: 18 },
  { workflow: "Workflow C", warning: 22, critical: 12, low: 16 },
  { workflow: "Workflow D", warning: 20, critical: 15, low: 19 },
  { workflow: "Workflow E", warning: 18, critical: 12, low: 21 },
  { workflow: "Workflow F", warning: 22, critical: 14, low: 17 },
  { workflow: "Workflow G", warning: 20, critical: 15, low: 20 },
  { workflow: "Workflow H", warning: 21, critical: 13, low: 18 },
];

// Mock data for pipeline stats
export const pipelineStatsData = {
  successful: 18,
  errors: 10,
  warning: 7,
};

// Mock data for MTTR chart
export const mttrChartData = {
  labels: ["10:00 AM", "11:30 AM", "1:00 PM", "2:15 PM", "3:40 PM", "5:45 PM", "7:35 PM", "8:30 PM"],
  datasets: [
    { color: "#4ade80", values: [8, 14, 12, 14, 20, 27, 16, 22] },
    { color: "#fb923c", values: [12, 13, 15, 16, 40, 35, 55, 35] },
    { color: "#f87171", values: [10, 12, 14, 20, 22, 27, 25, 30] },
    { color: "#c084fc", values: [11, 14, 13, 18, 38, 50, 27, 32] },
  ],
};

// Mock data for SLA Compliance chart
export const slaComplianceData = {
  overall: 98,
  stats: [
    { label: "Prediction", value: "23%", change: "6.01%", color: "#fbbf24" },
    { label: "In SLA", value: "30.1%", change: "4.12%", color: "#22c55e" },
    { label: "Out of SLA", value: "22.1%", change: "3.91%", color: "#ef4444" },
  ],
  donutSegments: [
    { percent: 22.1, color: "#ef4444" },
    { percent: 23, color: "#fbbf24" },
    { percent: 30.1, color: "#22c55e" },
  ],
};

// Mock data for workflows
export const workflowsData = [
  {
    id: 1,
    name: "Workflow A",
    members: [1, 2, 3],
    lastActivity: "28 Nov 2025, 11:20 AM",
    state: "Done",
  },
  {
    id: 2,
    name: "Workflow B",
    members: [1, 2, 3, 4, 5],
    lastActivity: "28 Nov 2025, 08:40 AM",
    state: "Overdue",
  },
  {
    id: 3,
    name: "Workflow C",
    members: [1, 2, 3],
    lastActivity: "27 Nov 2025, 4:02 PM",
    state: "Done",
  },
  {
    id: 4,
    name: "Workflow D",
    members: [1, 2],
    lastActivity: "18 Nov 2025, 5:00 PM",
    state: "Overdue",
  },
  {
    id: 5,
    name: "Workflow E",
    members: [1, 2, 3, 4],
    lastActivity: "25 Nov 2025, 2:30 PM",
    state: "Done",
  },
  {
    id: 6,
    name: "Workflow F",
    members: [1, 2],
    lastActivity: "24 Nov 2025, 10:15 AM",
    state: "Done",
  },
  {
    id: 7,
    name: "Workflow G",
    members: [1, 2, 3, 4, 5, 6],
    lastActivity: "23 Nov 2025, 3:45 PM",
    state: "Overdue",
  },
  {
    id: 8,
    name: "Workflow H",
    members: [1, 2, 3],
    lastActivity: "22 Nov 2025, 9:00 AM",
    state: "Done",
  },
  {
    id: 9,
    name: "Workflow I",
    members: [1, 2, 3, 4],
    lastActivity: "21 Nov 2025, 1:20 PM",
    state: "Done",
  },
  {
    id: 10,
    name: "Workflow J",
    members: [1, 2],
    lastActivity: "20 Nov 2025, 4:50 PM",
    state: "Overdue",
  },
  {
    id: 11,
    name: "Workflow K",
    members: [1, 2, 3, 4, 5],
    lastActivity: "19 Nov 2025, 11:30 AM",
    state: "Done",
  },
  {
    id: 12,
    name: "Workflow L",
    members: [1, 2, 3],
    lastActivity: "18 Nov 2025, 2:00 PM",
    state: "Done",
  },
];

// Mock data for members
export const membersData = [
  {
    id: 1,
    name: "Prashant Kashyap",
    code: "DEV -101",
    access: "Admin",
    envAccess: "Prod, Staging, Dev",
    assignedPipelines: 12,
    status: "Active",
  },
  {
    id: 2,
    name: "Mansi Yadav",
    code: "DEV -204",
    access: "Developer",
    envAccess: "Staging, Dev",
    assignedPipelines: 7,
    status: "Active",
  },
  {
    id: 3,
    name: "Niya Sharma",
    code: "DEV -333",
    access: "QA Tester",
    envAccess: "Dev",
    assignedPipelines: 3,
    status: "Active",
  },
  {
    id: 4,
    name: "Ravi Bhushan",
    code: "DEV -033",
    access: "Viewer",
    envAccess: "Dev",
    assignedPipelines: 0,
    status: "Suspended",
  },
  {
    id: 5,
    name: "Amit Kumar",
    code: "DEV -105",
    access: "Developer",
    envAccess: "Prod, Dev",
    assignedPipelines: 9,
    status: "Active",
  },
  {
    id: 6,
    name: "Priya Singh",
    code: "DEV -210",
    access: "Admin",
    envAccess: "Prod, Staging, Dev",
    assignedPipelines: 15,
    status: "Active",
  },
  {
    id: 7,
    name: "Rahul Verma",
    code: "DEV -156",
    access: "Developer",
    envAccess: "Staging, Dev",
    assignedPipelines: 5,
    status: "Active",
  },
  {
    id: 8,
    name: "Sneha Patel",
    code: "DEV -089",
    access: "QA Tester",
    envAccess: "Dev",
    assignedPipelines: 4,
    status: "Active",
  },
  {
    id: 9,
    name: "Vikram Joshi",
    code: "DEV -222",
    access: "Developer",
    envAccess: "Prod, Staging",
    assignedPipelines: 8,
    status: "Suspended",
  },
  {
    id: 10,
    name: "Ananya Gupta",
    code: "DEV -301",
    access: "Viewer",
    envAccess: "Dev",
    assignedPipelines: 2,
    status: "Active",
  },
  {
    id: 11,
    name: "Karan Mehta",
    code: "DEV -178",
    access: "Developer",
    envAccess: "Staging, Dev",
    assignedPipelines: 6,
    status: "Active",
  },
  {
    id: 12,
    name: "Divya Reddy",
    code: "DEV -245",
    access: "Admin",
    envAccess: "Prod, Staging, Dev",
    assignedPipelines: 11,
    status: "Active",
  },
];

