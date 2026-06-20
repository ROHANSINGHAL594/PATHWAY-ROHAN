import { useState } from "react";
import {
  Typography,
  Button,
  IconButton,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Box,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
} from "@mui/material";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import SortByAlphaIcon from "@mui/icons-material/SortByAlpha";
import SortIcon from "@mui/icons-material/Sort";
import ArrowUpwardIcon from "@mui/icons-material/ArrowUpward";
import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward";
import { AvatarStack } from "./AvatarStack";
import { StatusChip } from "./StatusChip";

// Format pipeline name - show name if exists, otherwise show "Pipeline ...eb3"
const formatPipelineName = (workflow, workflowNames = {}) => {
  // Check if name exists in workflowNames map (from retrieve_pipeline API)
  const name = workflowNames[workflow?._id] || workflow?.name;
  if (name) {
    return `${name} Pipeline`;
  }
  if (!workflow?._id) return "Pipeline";
  const lastThree = workflow._id.slice(-3);
  return `Pipeline ...${lastThree}`;
};

// Format date for Last Activity
const formatLastActivity = (dateString) => {
  if (!dateString) return "N/A";
  try {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  } catch (e) {
    return "N/A";
  }
};

export function WorkflowsTable({ data = [], onWorkflowSelect, selectedWorkflowId, workflowNames = {} }) {
  const [currentPage, setCurrentPage] = useState(1);
  const [showAll, setShowAll] = useState(false);
  const [menuAnchor, setMenuAnchor] = useState(null);
  const [sortBy, setSortBy] = useState(null); // null, 'name-asc', 'name-desc', 'date-asc', 'date-desc'
  const itemsPerPage = 5;

  // Helper function to get workflow name for sorting
  const getWorkflowName = (workflow) => {
    const name = workflowNames[workflow?._id] || workflow?.name;
    if (name) {
      return name.toLowerCase();
    }
    if (!workflow?._id) return "pipeline";
    const lastThree = workflow._id.slice(-3);
    return `pipeline ...${lastThree}`;
  };

  // Sort data based on sortBy
  const sortedData = [...data].sort((a, b) => {
    if (!sortBy) return 0;
    
    if (sortBy === 'name-asc') {
      const nameA = getWorkflowName(a);
      const nameB = getWorkflowName(b);
      return nameA.localeCompare(nameB);
    }
    
    if (sortBy === 'name-desc') {
      const nameA = getWorkflowName(a);
      const nameB = getWorkflowName(b);
      return nameB.localeCompare(nameA);
    }
    
    if (sortBy === 'date-asc') {
      const dateA = new Date(a.last_updated || 0).getTime();
      const dateB = new Date(b.last_updated || 0).getTime();
      return dateA - dateB;
    }
    
    if (sortBy === 'date-desc') {
      const dateA = new Date(a.last_updated || 0).getTime();
      const dateB = new Date(b.last_updated || 0).getTime();
      return dateB - dateA;
    }
    
    return 0;
  });

  const totalItems = sortedData.length;
  const totalPages = Math.ceil(totalItems / itemsPerPage);

  // Get current page data
  const getCurrentPageData = () => {
    if (showAll) return sortedData;
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    return sortedData.slice(startIndex, endIndex);
  };

  const displayedData = getCurrentPageData();
  
  // Calculate empty rows needed to maintain consistent height
  const emptyRows = showAll ? 0 : itemsPerPage - displayedData.length;

  const handlePrevPage = () => setCurrentPage((prev) => Math.max(1, prev - 1));
  const handleNextPage = () => setCurrentPage((prev) => Math.min(totalPages, prev + 1));
  const handleShowAll = () => {
    setShowAll(!showAll);
    setCurrentPage(1);
  };

  const handleMenuOpen = (event) => {
    setMenuAnchor(event.currentTarget);
  };

  const handleMenuClose = () => {
    setMenuAnchor(null);
  };

  const handleSort = (sortType) => {
    setSortBy(sortType);
    setCurrentPage(1); // Reset to first page when sorting
    handleMenuClose();
  };

  return (
    <Box
      className="admin-workflows-section"
      sx={{
        bgcolor: 'background.paper',
        p: 2.5,
        width: { xs: '100%', lg: '50%' },
      }}
    >
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          mb: 2,
        }}
      >
        <Box>
          <Typography
            variant="h6"
            sx={{
              fontSize: '1.125rem',
              fontWeight: 600,
              color: 'text.primary',
            }}
          >
            Workflows
          </Typography>
          <Typography
            variant="body2"
            sx={{
              fontSize: '0.75rem',
              color: 'text.secondary',
              mt: 0.125,
            }}
          >
            Total No. of Pipelines: {totalItems}
          </Typography>
        </Box>
        <IconButton 
          size="small" 
          sx={{ color: 'text.secondary' }}
          onClick={handleMenuOpen}
        >
          <MoreHorizIcon />
        </IconButton>
        <Menu
          anchorEl={menuAnchor}
          open={Boolean(menuAnchor)}
          onClose={handleMenuClose}
          transformOrigin={{ horizontal: 'right', vertical: 'top' }}
          anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
          slotProps={{
            paper: {
              elevation: 3,
              sx: {
                mt: 1,
                minWidth: 220,
                borderRadius: 2,
                '& .MuiMenuItem-root': {
                  px: 2,
                  py: 1.5,
                  borderRadius: 1,
                  mx: 1,
                  my: 0.5,
                },
              },
            },
          }}
        >
          <MenuItem onClick={() => handleSort('name-asc')}>
            <ListItemIcon>
              <SortByAlphaIcon fontSize="small" sx={{ color: 'text.secondary' }} />
            </ListItemIcon>
            <ListItemText>Sort by Name (A-Z)</ListItemText>
          </MenuItem>
          <MenuItem onClick={() => handleSort('name-desc')}>
            <ListItemIcon>
              <SortByAlphaIcon fontSize="small" sx={{ transform: 'scaleX(-1)', color: 'text.secondary' }} />
            </ListItemIcon>
            <ListItemText>Sort by Name (Z-A)</ListItemText>
          </MenuItem>
          <MenuItem onClick={() => handleSort('date-desc')}>
            <ListItemIcon>
              <ArrowDownwardIcon fontSize="small" sx={{ color: 'text.secondary' }} />
            </ListItemIcon>
            <ListItemText>Sort by Last Activity (Newest First)</ListItemText>
          </MenuItem>
          <MenuItem onClick={() => handleSort('date-asc')}>
            <ListItemIcon>
              <ArrowUpwardIcon fontSize="small" sx={{ color: 'text.secondary' }} />
            </ListItemIcon>
            <ListItemText>Sort by Last Activity (Oldest First)</ListItemText>
          </MenuItem>
        </Menu>
      </Box>
      <TableContainer
        sx={{
          boxShadow: 'none',
        }}
      >
        <Table size="small" sx={{ borderCollapse: 'separate', borderSpacing: '0 0.75rem' }}>
          <TableHead>
            <TableRow>
              <TableCell
                sx={{
                  bgcolor: 'transparent',
                  fontWeight: 600,
                  color: 'text.secondary',
                  fontSize: '0.75rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.025rem',
                  py: 1.5,
                  borderBottom: 'none',
                }}
              >
                Workflow
              </TableCell>
              <TableCell
                sx={{
                  bgcolor: 'transparent',
                  fontWeight: 600,
                  color: 'text.secondary',
                  fontSize: '0.75rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.025rem',
                  py: 1.5,
                  borderBottom: 'none',
                }}
              >
                Members
              </TableCell>
              <TableCell
                sx={{
                  bgcolor: 'transparent',
                  fontWeight: 600,
                  color: 'text.secondary',
                  fontSize: '0.75rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.025rem',
                  py: 1.5,
                  borderBottom: 'none',
                }}
              >
                Last Activity
              </TableCell>
              <TableCell
                sx={{
                  bgcolor: 'transparent',
                  fontWeight: 600,
                  color: 'text.secondary',
                  fontSize: '0.75rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.025rem',
                  py: 1.5,
                  borderBottom: 'none',
                }}
              >
                State
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {displayedData.map((workflow) => {
              const memberCount = (workflow.owner_ids?.length || 0) + (workflow.viewer_ids?.length || 0);
              const isSelected = selectedWorkflowId === workflow._id;
              
              return (
              <TableRow
                  key={workflow._id}
                  onClick={() => onWorkflowSelect && onWorkflowSelect(workflow)}
                sx={{
                    cursor: 'pointer',
                  transition: 'background-color 0.2s ease',
                    bgcolor: isSelected ? 'action.selected' : 'transparent',
                  '&:hover .MuiTableCell-root': {
                      bgcolor: isSelected ? 'action.selected' : 'action.hover',
                  },
                  '&:active .MuiTableCell-root': {
                    bgcolor: 'action.selected',
                  },
                  '& .MuiTableCell-root': {
                    borderBottom: 'none',
                      bgcolor: isSelected ? 'action.selected' : 'background.elevation1',
                    '&:first-of-type': {
                      borderTopLeftRadius: '0.75rem',
                      borderBottomLeftRadius: '0.75rem',
                    },
                    '&:last-of-type': {
                      borderTopRightRadius: '0.75rem',
                      borderBottomRightRadius: '0.75rem',
                    },
                  },
                }}
              >
                <TableCell
                  sx={{
                    py: 1.75,
                    fontSize: '0.875rem',
                  }}
                >
                  <Typography
                    sx={{
                      color: 'text.primary',
                      fontWeight: 500,
                    }}
                  >
                      {formatPipelineName(workflow, workflowNames)}
                  </Typography>
                </TableCell>
                <TableCell
                  sx={{
                    py: 1.75,
                    fontSize: '0.875rem',
                  }}
                >
                    <AvatarStack count={memberCount} />
                </TableCell>
                <TableCell
                  sx={{
                    py: 1.75,
                    fontSize: '0.875rem',
                    color: 'text.primary',
                  }}
                >
                    {formatLastActivity(workflow.last_updated)}
                </TableCell>
                <TableCell
                  sx={{
                    py: 1.75,
                    fontSize: '0.875rem',
                  }}
                >
                    <StatusChip status={workflow.status || "Stopped"} />
                </TableCell>
              </TableRow>
              );
            })}
            {/* Empty rows to maintain consistent table height */}
            {emptyRows > 0 && Array.from({ length: emptyRows }).map((_, index) => (
              <TableRow
                key={`empty-${index}`}
                sx={{
                  '& .MuiTableCell-root': {
                    borderBottom: 'none',
                    bgcolor: 'transparent',
                    py: 1.75,
                  },
                }}
              >
                <TableCell colSpan={4} sx={{ height: '3.5rem' }} />
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          pt: 2,
          mt: 0.5,
        }}
      >
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1,
            fontSize: '0.75rem',
            color: 'text.secondary',
          }}
        >
          <span>
            {showAll 
              ? <>Showing <strong>all {totalItems} items</strong></>
              : <>Showing <strong>page {currentPage} out of {totalPages}</strong></>
            }
          </span>
          <Button
            size="small"
            onClick={handleShowAll}
            sx={{
              color: 'primary.main',
              textTransform: 'none',
              fontSize: '0.75rem',
              p: 0,
              minWidth: 'auto',
            }}
          >
            {showAll ? 'Show less' : 'Show all'}
          </Button>
        </Box>
        {!showAll && (
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 0.5,
            }}
          >
            <Button
              size="small"
              onClick={handlePrevPage}
              disabled={currentPage === 1}
              sx={{
                textTransform: 'none',
                fontSize: '0.75rem',
                color: currentPage === 1 ? 'text.disabled' : 'text.secondary',
              }}
            >
              <ChevronLeftIcon sx={{ fontSize: "1rem" }} />
              Previous
            </Button>
            <Button
              size="small"
              onClick={handleNextPage}
              disabled={currentPage === totalPages}
              sx={{
                textTransform: 'none',
                fontSize: '0.75rem',
                color: currentPage === totalPages ? 'text.disabled' : 'primary.main',
              }}
            >
              Next
              <ChevronRightIcon sx={{ fontSize: "1rem" }} />
            </Button>
          </Box>
        )}
      </Box>
    </Box>
  );
}
