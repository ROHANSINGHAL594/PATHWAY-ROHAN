import { useState, useEffect, useContext } from "react";
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
  TextField,
  InputAdornment,
  CircularProgress,
  Menu,
  MenuItem,
  Snackbar,
  Alert,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import KeyboardDoubleArrowLeftIcon from "@mui/icons-material/KeyboardDoubleArrowLeft";
import KeyboardDoubleArrowRightIcon from "@mui/icons-material/KeyboardDoubleArrowRight";
import { Avatar } from "@mui/material";
import { fetchUserById, removeViewerFromPipeline } from "../../utils/developerDashboard.api";
import { AuthContext } from "../../context/AuthContext";


// Format pipeline name as "Pipeline ...eb3"
const formatPipelineName = (pipelineId) => {
  if (!pipelineId) return "Pipeline";
  const lastThree = pipelineId.slice(-3);
  return `Pipeline ...${lastThree}`;
};

export function MembersTable({ workflow, onWorkflowUpdate }) {
  const [currentPage, setCurrentPage] = useState(1);
  const [showAll, setShowAll] = useState(false);
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [menuAnchor, setMenuAnchor] = useState(null);
  const [selectedMember, setSelectedMember] = useState(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: "", severity: "success" });
  const [searchQuery, setSearchQuery] = useState("");
  const { user } = useContext(AuthContext);
  const itemsPerPage = 5;

  // Check if current user is an owner of the workflow
  const isOwner = workflow && user && workflow.owner_ids?.includes(String(user.id));
  
  // Check if a member is the current logged-in user
  const isCurrentUser = (member) => {
    if (!user || !member) return false;
    return String(member.id) === String(user.id) || member.email === user.email;
  };

  // Fetch user details for owner_ids and viewer_ids
  useEffect(() => {
    const fetchMembers = async () => {
      if (!workflow) {
        setMembers([]);
        return;
      }

      setLoading(true);
      const membersList = [];

      // Fetch owner details
      if (workflow.owner_ids && workflow.owner_ids.length > 0) {
        const ownerPromises = workflow.owner_ids.map(async (ownerId) => {
          try {
            const userData = await fetchUserById(ownerId);
            return {
              id: userData.id || ownerId,
              name: userData.full_name || `User ${ownerId}`,
              email: userData.email || `user${ownerId}@example.com`,
              access: "Owner",
            };
          } catch (error) {
            console.error(`Error fetching owner ${ownerId}:`, error);
            return {
              id: ownerId,
              name: `Owner ${ownerId}`,
              email: `user${ownerId}@example.com`,
              access: "Owner",
            };
          }
        });
        const owners = await Promise.all(ownerPromises);
        membersList.push(...owners);
      }

      // Fetch viewer details
      if (workflow.viewer_ids && workflow.viewer_ids.length > 0) {
        const viewerPromises = workflow.viewer_ids.map(async (viewerId) => {
          try {
            const userData = await fetchUserById(viewerId);
            return {
              id: userData.id || viewerId,
              name: userData.full_name || `User ${viewerId}`,
              email: userData.email || `user${viewerId}@example.com`,
              access: "Viewer",
            };
          } catch (error) {
            console.error(`Error fetching viewer ${viewerId}:`, error);
            return {
              id: viewerId,
              name: `Viewer ${viewerId}`,
              email: `user${viewerId}@example.com`,
              access: "Viewer",
            };
          }
        });
        const viewers = await Promise.all(viewerPromises);
        membersList.push(...viewers);
      }

      setMembers(membersList);
      setLoading(false);
    };

    fetchMembers();
  }, [workflow]);

  // Filter members based on search query
  const filteredMembers = members.filter((member) => {
    if (!searchQuery.trim()) return true;
    const query = searchQuery.toLowerCase();
    const name = (member.name || "").toLowerCase();
    const email = (member.email || "").toLowerCase();
    const access = (member.access || "").toLowerCase();
    return name.includes(query) || email.includes(query) || access.includes(query);
  });

  const data = filteredMembers;
  const totalItems = data.length;
  const totalPages = Math.ceil(totalItems / itemsPerPage);

  // Get current page data
  const getCurrentPageData = () => {
    if (showAll) return data;
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    return data.slice(startIndex, endIndex);
  };

  const displayedData = getCurrentPageData();
  
  // Reset to first page when search changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery]);
  
  // Calculate empty rows needed to maintain consistent height
  const emptyRows = showAll ? 0 : itemsPerPage - displayedData.length;

  const handleFirstPage = () => setCurrentPage(1);
  const handleLastPage = () => setCurrentPage(totalPages);
  const handlePrevPage = () => setCurrentPage((prev) => Math.max(1, prev - 1));
  const handleNextPage = () => setCurrentPage((prev) => Math.min(totalPages, prev + 1));
  const handlePageClick = (page) => setCurrentPage(page);
  const handleShowAll = () => {
    setShowAll(!showAll);
    setCurrentPage(1);
  };

  // Generate page numbers to display
  const getPageNumbers = () => {
    const pages = [];
    for (let i = 1; i <= totalPages; i++) {
      pages.push(i);
    }
    return pages;
  };

  // Handle menu open
  const handleMenuOpen = (event, member) => {
    event.stopPropagation();
    setMenuAnchor(event.currentTarget);
    setSelectedMember(member);
  };

  // Handle menu close
  const handleMenuClose = () => {
    setMenuAnchor(null);
    setSelectedMember(null);
  };

  // Handle remove viewer
  const handleRemoveViewer = async () => {
    if (!selectedMember || !workflow || selectedMember.access !== "Viewer") {
      handleMenuClose();
      return;
    }

    try {
      await removeViewerFromPipeline(workflow._id, selectedMember.id);
      setSnackbar({
        open: true,
        message: "Viewer removed successfully",
        severity: "success",
      });
      
      // Refresh members list by re-fetching
      const fetchMembers = async () => {
        setLoading(true);
        const membersList = [];


        // Fetch owner details
        if (workflow.owner_ids && workflow.owner_ids.length > 0) {
          const ownerPromises = workflow.owner_ids.map(async (ownerId) => {
            try {
              const userData = await fetchUserById(ownerId);
              return {
                id: userData.id || ownerId,
                name: userData.full_name || `User ${ownerId}`,
                email: userData.email || `user${ownerId}@example.com`,
                access: "Owner",
              };
            } catch (error) {
              console.error(`Error fetching owner ${ownerId}:`, error);
              return {
                id: ownerId,
                name: `Owner ${ownerId}`,
                email: `user${ownerId}@example.com`,
                access: "Owner",
              };
            }
          });
          const owners = await Promise.all(ownerPromises);
          membersList.push(...owners);
        }

        // Fetch viewer details (excluding the removed one)
        const remainingViewerIds = workflow.viewer_ids?.filter(id => String(id) !== String(selectedMember.id)) || [];
        if (remainingViewerIds.length > 0) {
          const viewerPromises = remainingViewerIds.map(async (viewerId) => {
            try {
              const userData = await fetchUserById(viewerId);
              return {
                id: userData.id || viewerId,
                name: userData.full_name || `User ${viewerId}`,
                email: userData.email || `user${viewerId}@example.com`,
                access: "Viewer",
              };
            } catch (error) {
              console.error(`Error fetching viewer ${viewerId}:`, error);
              return {
                id: viewerId,
                name: `Viewer ${viewerId}`,
                email: `user${viewerId}@example.com`,
                access: "Viewer",
              };
            }
          });
          const viewers = await Promise.all(viewerPromises);
          membersList.push(...viewers);
        }

        setMembers(membersList);
        setLoading(false);
      };

      await fetchMembers();
      
      // Update the workflow in the parent component to reflect the change
      if (onWorkflowUpdate && workflow) {
        const updatedWorkflow = {
          ...workflow,
          viewer_ids: workflow.viewer_ids?.filter(id => String(id) !== String(selectedMember.id)) || []
        };
        onWorkflowUpdate(updatedWorkflow);
      }
      
      handleMenuClose();
    } catch (error) {
      console.error("Error removing viewer:", error);
      setSnackbar({
        open: true,
        message: error.message || "Failed to remove viewer",
        severity: "error",
      });
      handleMenuClose();
    }
  };

  const handleCloseSnackbar = () => {
    setSnackbar({ ...snackbar, open: false });
  };
  return (
    <Box
      className="admin-members-section"
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
          flexDirection: { xs: 'column', sm: 'row' },
          gap: 2,
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
            Members
          </Typography>
          <Typography
            variant="body2"
            sx={{
              fontSize: '0.75rem',
              color: 'text.secondary',
              mt: 0.125,
            }}
          >
            {workflow ? `Members for ${formatPipelineName(workflow._id)}` : "Select a workflow to view members"}
          </Typography>
        </Box>
        <TextField
          placeholder="Search Members"
          size="small"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          sx={{
            width: { xs: '100%', sm: 160 },
            '& .MuiOutlinedInput-root': {
              borderRadius: 2,
              bgcolor: 'background.elevation1',
              pl: 4,
              '& fieldset': {
                borderColor: 'divider',
              },
            },
          }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon sx={{ fontSize: '1rem', color: 'text.secondary' }} />
              </InputAdornment>
            ),
          }}
        />
      </Box>
      <TableContainer
        sx={{
          boxShadow: 'none',
        }}
      >
        <Table size="small" sx={{ borderCollapse: 'separate', borderSpacing: '0 0.75rem' }}>
          <TableHead>
            <TableRow>
              {['Name', 'Access', 'Email', ''].map((header) => (
                <TableCell
                  key={header}
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
                  {header}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={4} sx={{ py: 4, textAlign: 'center' }}>
                  <CircularProgress size={24} />
                </TableCell>
              </TableRow>
            ) : data.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} sx={{ py: 4, textAlign: 'center', color: 'text.secondary' }}>
                  <Typography variant="body2">
                    {workflow ? "No members found" : "Select a workflow to view members"}
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              displayedData.map((member) => {
                const isUser = isCurrentUser(member);
                return (
              <TableRow
                key={member.id}
                sx={{
                  transition: 'background-color 0.2s ease',
                  ...(isUser && {
                    border: '2px solid',
                    borderColor: 'primary.main',
                    '& .MuiTableCell-root': {
                      bgcolor: 'action.selected',
                    },
                  }),
                  '&:hover .MuiTableCell-root': {
                    bgcolor: isUser ? 'action.selected' : 'action.hover',
                  },
                  '&:active .MuiTableCell-root': {
                    bgcolor: 'action.selected',
                  },
                  '& .MuiTableCell-root': {
                    borderBottom: 'none',
                    bgcolor: isUser ? 'action.selected' : 'background.elevation1',
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
                  <Box
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 1.5,
                    }}
                  >
                    <Avatar
                      src={`https://avatar.iran.liara.run/public/boy?username=${encodeURIComponent(member.name || member.id || `member${member.id}`)}&size=32`}
                      alt={member.name}
                      sx={{
                        width: 32,
                        height: 32,
                      }}
                    />
                    <Box>
                      <Typography
                        sx={{
                          fontWeight: 500,
                          color: 'text.primary',
                          fontSize: '0.875rem',
                        }}
                      >
                        {member.name}
                      </Typography>
                    </Box>
                  </Box>
                </TableCell>
                <TableCell
                  sx={{
                    py: 1.75,
                    fontSize: '0.875rem',
                  }}
                >
                  <Typography
                    sx={{
                      fontWeight: 500,
                      color: 'text.primary',
                      fontSize: '0.875rem',
                    }}
                  >
                    {member.access}
                  </Typography>
                </TableCell>
                <TableCell
                  sx={{
                    py: 1.75,
                    fontSize: '0.875rem',
                    color: 'text.secondary',
                  }}
                >
                  <Typography
                    sx={{
                      fontSize: '0.875rem',
                      color: 'text.secondary',
                    }}
                  >
                    {member.email}
                  </Typography>
                </TableCell>
                <TableCell
                  sx={{
                    py: 1.75,
                    fontSize: '0.875rem',
                  }}
                >
                  {isOwner && member.access === "Viewer" ? (
                    <IconButton 
                      size="small" 
                      sx={{ color: 'text.secondary' }}
                      onClick={(e) => handleMenuOpen(e, member)}
                    >
                      <MoreHorizIcon sx={{ fontSize: "1rem" }} />
                    </IconButton>
                  ) : (
                    <Box sx={{ width: 32, height: 32 }} /> // Spacer to maintain alignment
                  )}
                </TableCell>
              </TableRow>
              );
            })
            )}
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
          flexDirection: { xs: 'column', sm: 'row' },
          gap: 2,
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
            <IconButton
              size="small"
              onClick={handleFirstPage}
              disabled={currentPage === 1}
              sx={{
                color: currentPage === 1 ? 'text.disabled' : 'text.secondary',
                minWidth: 'auto',
                p: 0.5,
                fontSize: '0.75rem',
              }}
            >
              <KeyboardDoubleArrowLeftIcon sx={{ fontSize: "1rem" }} />
            </IconButton>
            <IconButton
              size="small"
              onClick={handlePrevPage}
              disabled={currentPage === 1}
              sx={{
                color: currentPage === 1 ? 'text.disabled' : 'text.secondary',
                minWidth: 'auto',
                p: 0.5,
                fontSize: '0.75rem',
              }}
            >
              <ChevronLeftIcon sx={{ fontSize: "1rem" }} />
            </IconButton>
            {getPageNumbers().map((page) => (
              <Button
                key={page}
                size="small"
                onClick={() => handlePageClick(page)}
                sx={{
                  bgcolor: currentPage === page ? 'primary.main' : 'transparent',
                  color: currentPage === page ? 'primary.contrastText' : 'text.secondary',
                  minWidth: 'auto',
                  p: 0.5,
                  fontSize: '0.75rem',
                  borderRadius: 1.5,
                  '&:hover': {
                    bgcolor: currentPage === page ? 'primary.dark' : 'action.hover',
                  },
                }}
              >
                {page}
              </Button>
            ))}
            <IconButton
              size="small"
              onClick={handleNextPage}
              disabled={currentPage === totalPages}
              sx={{
                color: currentPage === totalPages ? 'text.disabled' : 'text.secondary',
                minWidth: 'auto',
                p: 0.5,
                fontSize: '0.75rem',
              }}
            >
              <ChevronRightIcon sx={{ fontSize: "1rem" }} />
            </IconButton>
            <IconButton
              size="small"
              onClick={handleLastPage}
              disabled={currentPage === totalPages}
              sx={{
                color: currentPage === totalPages ? 'text.disabled' : 'text.secondary',
                minWidth: 'auto',
                p: 0.5,
                fontSize: '0.75rem',
              }}
            >
              <KeyboardDoubleArrowRightIcon sx={{ fontSize: "1rem" }} />
            </IconButton>
          </Box>
        )}
      </Box>

      {/* Menu for Remove Viewer */}
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
              minWidth: 180,
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
        {isOwner && selectedMember && selectedMember.access === "Viewer" && (
          <MenuItem 
            onClick={handleRemoveViewer}
            sx={{ color: 'error.main' }}
          >
            Remove Viewer
          </MenuItem>
        )}
      </Menu>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert 
          onClose={handleCloseSnackbar} 
          severity={snackbar.severity} 
          sx={{ borderRadius: 2 }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}

