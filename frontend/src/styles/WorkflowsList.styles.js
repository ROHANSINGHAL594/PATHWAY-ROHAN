// WorkflowsList Component Styles

export const styles = {
  // Main Container
  mainContainer: {
    display: "flex",
    height: "100vh",
    bgcolor: "#ffffff",
    position: "relative",
  },

  // Floating Menu Button
  floatingMenuButton: {
    position: "fixed",
    top: 16,
    left: 16,
    zIndex: 1300,
    bgcolor: "#3b82f6",
    color: "#ffffff",
    boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
    "&:hover": {
      bgcolor: "#2563eb",
    },
  },

  // Drawer/Sidebar
  drawer: (sidebarWidth) => ({
    width: sidebarWidth,
    flexShrink: 0,
    '& .MuiDrawer-paper': {
      width: sidebarWidth,
      overflowX: 'hidden',
      backgroundColor: '#f8f9fa',
      borderRight: '1px solid #e0e0e0',
      boxShadow: '4px 0 16px rgba(0,0,0,0.15)',
    },
  }),

  drawerClosed: {
    '& .MuiDrawer-paper': {
      backgroundColor: '#fff',
    },
  },

  // Drawer Header
  drawerHeader: (sidebarOpen) => ({
    display: 'flex',
    alignItems: 'center',
    justifyContent: sidebarOpen ? 'space-between' : 'center',
    padding: sidebarOpen ? 2 : 1,
    minHeight: 64,
    borderBottom: sidebarOpen ? '1px solid #e0e0e0' : 'none',
  }),

  logo: {
    height: 18,
    width: 'auto',
    objectFit: 'contain',
  },

  toggleButton: {
    color: '#1976d2',
  },

  // List Items
  listItemButton: (isActive, sidebarOpen) => ({
    minHeight: 48,
    justifyContent: sidebarOpen ? 'initial' : 'center',
    px: sidebarOpen ? 3 : 1,
    my: 0.5,
    mx: sidebarOpen ? 1 : 0.5,
    borderRadius: 1,
    backgroundColor: isActive ? '#EAF3FD' : 'transparent',
    '&:hover': {
      backgroundColor: isActive ? '#EAF3FD' : '#f5f5f5',
    },
  }),

  listItemIcon: (isActive, sidebarOpen) => ({
    minWidth: 0,
    mr: sidebarOpen ? 3 : 'auto',
    justifyContent: 'center',
    color: isActive ? '#1976d2' : '#666',
  }),

  listItemText: (isActive) => ({
    color: isActive ? '#1976d2' : '#374151',
    fontWeight: isActive ? 600 : 400,
    fontSize: '0.8rem',
  }),

  // Main Content Area
  mainContentArea: {
    display: "flex",
    flexDirection: { xs: "column", lg: "row" },
    height: "100vh",
    bgcolor: "#ffffff",
    width: "calc(100vw - 64px)",
    gap: 0,
    overflow: "hidden",
  },

  // Workflows List Section
  workflowsListSection: {
    width: { xs: "100%", lg: "33%" },
    height: { xs: "40vh", lg: "100vh" },
    minWidth: { lg: 350 },
    maxWidth: { lg: 500 },
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
    p: 3,
    pl: 3,
    bgcolor: "#ffffff",
    borderRight: { xs: "none", lg: "1px solid #e5e7eb" },
    borderBottom: { xs: "1px solid #e5e7eb", lg: "none" },
  },

  // Header Section
  headerTitle: {
    fontWeight: 600,
    color: "#111827",
    fontSize: "1.125rem",
  },

  addButton: {
    textTransform: "none",
    bgcolor: "#3b82f6",
    borderRadius: "6px",
    px: 2,
    py: 0.5,
    fontWeight: 500,
    fontSize: "0.8125rem",
    boxShadow: "none",
    minWidth: "auto",
    "&:hover": { bgcolor: "#2563eb" },
  },

  headerSubtitle: {
    color: "#6b7280",
    fontSize: "0.8125rem",
    mb: 2,
  },

  // Search Bar
  searchField: {
    bgcolor: "#f9fafb",
    borderRadius: "6px",
    fontSize: "0.8125rem",
    "& fieldset": { borderColor: "#e5e7eb" },
    "& input": { padding: "8px 12px" },
  },

  searchIcon: {
    color: "#9ca3af",
    fontSize: 18,
  },

  filterButton: {
    minWidth: "auto",
    px: 1.5,
    py: 0.75,
    bgcolor: "#f9fafb",
    color: "#6b7280",
    borderRadius: "6px",
    "&:hover": { bgcolor: "#f3f4f6" },
  },

  // Tabs
  tabs: {
    mb: 1.5,
    minHeight: "36px",
    "& .MuiTab-root": {
      textTransform: "none",
      fontWeight: 500,
      fontSize: "0.8125rem",
      color: "#6b7280",
      minHeight: "36px",
      py: 0.5,
      px: 2,
      "&.Mui-selected": { color: "#111827" },
    },
    "& .MuiTabs-indicator": { bgcolor: "#3b82f6", height: "2px" },
  },

  // Workflow Card
  workflowCard: (isSelected) => ({
    cursor: "pointer",
    borderRadius: "8px",
    bgcolor: isSelected ? "#EBF2F5" : "#F7FAFC",
    border: "none",
    boxShadow: "none",
    transition: "all 0.2s ease",
    "&:hover": {
      bgcolor: "#EBF2F5",
    },
  }),

  workflowCardContent: {
    p: 2,
    "&:last-child": { pb: 2 },
  },

  workflowName: {
    fontWeight: 600,
    fontSize: "0.9375rem",
    mb: 0.5,
    color: "#111827",
  },

  workflowCategory: {
    color: "#6b7280",
    fontSize: "0.8125rem",
    mb: 1.5,
  },

  avatarGroup: {
    "& .MuiAvatar-root": {
      width: 24,
      height: 24,
      fontSize: "0.625rem",
      border: "2px solid white",
    },
  },

  statusChip: (status) => ({
    bgcolor: status === "Active" ? "#d1fae5" : "#e5e7eb",
    color: status === "Active" ? "#065f46" : "#6b7280",
    fontWeight: 500,
    fontSize: "0.6875rem",
    height: "22px",
    borderRadius: "4px",
  }),

  moreButton: {
    color: "#9ca3af",
    ml: 1,
  },

  // Right Details Section
  detailsSection: {
    flex: 1,
    height: { xs: "60vh", lg: "100vh" },
    bgcolor: "#ffffff",
    overflow: "auto",
    display: "flex",
    flexDirection: "column",
    p: 3,
    '&::-webkit-scrollbar': {
      width: '8px',
    },
    '&::-webkit-scrollbar-track': {
      background: 'transparent',
    },
    '&::-webkit-scrollbar-thumb': {
      background: 'transparent',
      borderRadius: '4px',
    },
    '&:hover::-webkit-scrollbar-thumb': {
      background: '#cbd5e0',
    },
    '&::-webkit-scrollbar-thumb:hover': {
      background: '#a0aec0',
    },
  },

  detailsTitle: {
    fontWeight: 600,
    color: "#111827",
    fontSize: "1.125rem",
  },

  detailsAvatarGroup: {
    "& .MuiAvatar-root": {
      width: 32,
      height: 32,
      fontSize: "0.75rem",
    },
  },

  iconButton: {
    color: "#6b7280",
  },

  descriptionLabel: {
    fontWeight: 600,
    color: "#111827",
    mb: 1,
    fontSize: "0.875rem",
  },

  descriptionText: {
    color: "#6b7280",
    fontSize: "0.875rem",
    lineHeight: 1.6,
  },

  // Grid Section
  gridContainer: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr 1fr",
    gap: 2,
    mb: 3,
  },

  gridBox: {
    bgcolor: "#ffffff",
    border: "1px solid #e5e7eb",
    borderRadius: "8px",
    p: 2,
  },

  gridTitle: {
    fontWeight: 600,
    fontSize: "0.9375rem",
    color: "#111827",
  },

  gridSubtitle: {
    color: "#9ca3af",
    fontSize: "0.75rem",
    mb: 1.5,
  },

  openButton: {
    textTransform: "none",
    color: "#3b82f6",
    fontSize: "0.8125rem",
    fontWeight: 500,
    minWidth: "auto",
    p: 0,
    "&:hover": { bgcolor: "transparent" },
  },

  previewPaper: {
    height: 100,
    bgcolor: "#f9fafb",
    border: "1px solid #e5e7eb",
    borderRadius: "6px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    cursor: "pointer",
    transition: "all 0.2s ease",
    "&:hover": {
      borderColor: "#3b82f6",
      bgcolor: "#EAF3FD",
    },
  },

  previewText: {
    color: "#9ca3af",
    fontSize: "0.8125rem",
  },

  metricValue: {
    fontWeight: 600,
    fontSize: "1.875rem",
    color: "#111827",
    mb: 0.5,
  },

  metricChange: (isPositive) => ({
    display: "inline-block",
    color: isPositive ? "#10b981" : "#ef4444",
    bgcolor: isPositive ? "#d1fae5" : "#fee2e2",
    px: 0.75,
    py: 0.25,
    fontSize: "0.75rem",
    fontWeight: 500,
    borderRadius: "4px",
  }),

  metricLabel: {
    color: "#9ca3af",
    fontSize: "0.75rem",
  },

  // Action Required & Logs Section
  twoColumnsGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: 2,
    flex: 1,
    overflow: "hidden",
  },

  actionBox: {
    flexDirection: "column",
    bgcolor: "#ffffff",
    border: "1px solid #e5e7eb",
    borderRadius: "8px",
    overflow: "hidden",
  },

  actionHeader: {
    p: 2,
    borderBottom: "1px solid #e5e7eb",
    display: "flex",
    alignItems: "center",
    gap: 1,
  },

  actionTitle: {
    fontWeight: 600,
    fontSize: "0.9375rem",
    color: "#111827",
  },

  filterActionButton: (isActive) => ({
    textTransform: "none",
    bgcolor: isActive ? "#EAF3FD" : "transparent",
    color: isActive ? "#1e40af" : "#6b7280",
    fontSize: "0.75rem",
    fontWeight: 500,
    px: 1.5,
    py: 0.5,
    minWidth: "auto",
    borderRadius: "6px",
    "&:hover": {
      bgcolor: isActive ? "#EAF3FD" : "#f3f4f6",
    },
  }),

  actionContent: {
    flex: 1,
    overflowY: "auto",
    p: 2,
    '&::-webkit-scrollbar': {
      width: '6px',
    },
    '&::-webkit-scrollbar-track': {
      background: 'transparent',
    },
    '&::-webkit-scrollbar-thumb': {
      background: 'transparent',
      borderRadius: '3px',
    },
    '&:hover::-webkit-scrollbar-thumb': {
      background: '#cbd5e0',
    },
    '&::-webkit-scrollbar-thumb:hover': {
      background: '#a0aec0',
    },
  },

  actionLabel: {
    color: "#6b7280",
    fontSize: "0.75rem",
    mb: 1.5,
    display: "block",
    textTransform: "capitalize",
  },

  actionItem: {
    p: 1.5,
    bgcolor: "#F7FAFC",
    border: "1px solid #e5e7eb",
    borderRadius: "6px",
  },

  actionItemTitle: {
    fontWeight: 600,
    fontSize: "0.8125rem",
    color: "#111827",
    mb: 0.5,
  },

  actionItemSubtext: {
    color: "#6b7280",
    fontSize: "0.75rem",
  },

  logItem: {
    p: 1.5,
    bgcolor: "#F7FAFC",
    border: "1px solid #e5e7eb",
    borderRadius: "6px",
    color: "#374151",
    fontSize: "0.8125rem",
    lineHeight: 1.5,
  },
};

