import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Typography,
  CircularProgress,
  Tooltip,
  Switch,
  useTheme,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';
import NavigateBeforeIcon from '@mui/icons-material/NavigateBefore';
import AutorenewIcon from '@mui/icons-material/Autorenew';
import { useGlobalWorkflow } from '../../context/GlobalWorkflowContext';

const NodeDataTable = ({ nodeId, tableName, isVisible, nodeRef, onMouseEnter, onMouseLeave}) => {
  const theme = useTheme();
  const { id: workflowId } = useGlobalWorkflow();
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(0);
  const [totalRows, setTotalRows] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [columns, setColumns] = useState([]);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [position, setPosition] = useState({ top: '100%', left: '0', right: 'auto', bottom: 'auto' });
  const [rowsPerPage, setRowsPerPage] = useState(5);
  const [countdown, setCountdown] = useState(10);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);
  
  const REFRESH_INTERVAL = 10000; // 10 seconds
  const intervalRef = useRef(null);
  const countdownIntervalRef = useRef(null);
  const tableRef = useRef(null);
  const apiServer = import.meta.env.VITE_API_SERVER;
  
  // Fetch data from container's /data endpoint via action proxy
  const fetchData = useCallback(async (startRow = 0) => {
    if (!isVisible || !workflowId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const limit = rowsPerPage;
      // Use the action proxy route to reach the container's /data endpoint
      const url = `${apiServer}/action/${workflowId}/data`;

      console.log(`Fetching data: table=${tableName || nodeId}, start=${startRow}, limit=${limit}`);
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          table_name: tableName || nodeId,
          start: startRow,
          limit: limit
        })
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('API Error:', response.status, errorText);
        throw new Error(`Failed to fetch data: Please ensure pipeline is saved and running`);
      }
      
      const result = await response.json();
      
      console.log(`Received ${result.data?.length || 0} rows, total: ${result.total}`);
      
      setData(result.data || []);
      setTotalRows(result.total || 0);
      setHasMore(result.has_more || false);
      setCountdown(10); // Reset countdown after fetch
      
      // Extract columns from first row
      if (result.data && result.data.length > 0) {
        setColumns(Object.keys(result.data[0]));
      }
    } catch (err) {
      console.error('Error in fetchData:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [isVisible, rowsPerPage, nodeId, tableName, workflowId, apiServer]);

  // Handle page navigation
  const handleNext = (e) => {
    e.stopPropagation();
    e.preventDefault();
    const nextPage = currentPage + 1;
    setCurrentPage(nextPage);
    setCountdown(10); // Reset countdown
    const startRow = nextPage * rowsPerPage;
    fetchData(startRow);
  };

  const handlePrevious = (e) => {
    e.stopPropagation();
    e.preventDefault();
    const prevPage = Math.max(0, currentPage - 1);
    setCurrentPage(prevPage);
    setCountdown(10); // Reset countdown
    const startRow = prevPage * rowsPerPage;
    fetchData(startRow);
  };

  const handleRefresh = (e) => {
    e.stopPropagation();
    e.preventDefault();
    setCountdown(10); // Reset countdown on manual refresh
    const startRow = currentPage * rowsPerPage;
    fetchData(startRow);
  };

  const handleRowsPerPageChange = (newValue) => {
    setDropdownOpen(false); // Close dropdown
    setCurrentPage(0); // Reset to first page
    setRowsPerPage(newValue); // This will trigger the useEffect to fetch data
    // Note: No manual fetch here - let useEffect handle it to avoid race conditions
    // Countdown will be reset by fetchData after successful fetch
  };

  const handleAutoRefreshToggle = (e) => {
    e.stopPropagation();
    const newValue = e.target.checked;
    setAutoRefresh(newValue);
    if (newValue) {
      setCountdown(10); // Reset countdown when turning on auto-refresh
    }
  };

  // Calculate optimal table position based on node location
  const calculatePosition = () => {
    if (!nodeRef?.current) return;

    const nodeRect = nodeRef.current.getBoundingClientRect();
    const tableWidth = 640; // 40rem approximate
    
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    
    // Calculate available space in each direction
    const spaceRight = viewportWidth - nodeRect.right;
    const spaceLeft = nodeRect.left;
    
    // Calculate which quadrant the node is in
    const isLeftHalf = nodeRect.left < viewportWidth / 2;
    const isTopHalf = nodeRect.top < viewportHeight / 2;
    
    let newPosition = {};
    
    // ALWAYS place table horizontally (left or right of node), never on top or bottom
    // Prefer right side if node is in left half, prefer left side if node is in right half
    if (isLeftHalf) {
      // Node is on left side of screen -> place table on RIGHT side of node
      newPosition.left = '100%';
      newPosition.right = 'auto';
    } else {
      // Node is on right side of screen -> place table on LEFT side of node
      newPosition.right = '100%';
      newPosition.left = 'auto';
    }
    
    // Vertical alignment: align top edges if node is in top half, bottom edges if in bottom half
    if (isTopHalf) {
      newPosition.top = '0';
      newPosition.bottom = 'auto';
    } else {
      newPosition.bottom = '0';
      newPosition.top = 'auto';
    }
    
    setPosition(newPosition);
  };

  // Calculate position when table becomes visible
  useEffect(() => {
    if (isVisible) {
      calculatePosition();
    }
  }, [isVisible]);

  // Setup auto-refresh
  useEffect(() => {
    if (!isVisible) {
      // Clear interval when not visible
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    // Clear any existing interval before setting up new one
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    // Initial fetch
    const startRow = currentPage * rowsPerPage;
    fetchData(startRow);

    // Setup auto-refresh only if enabled
    if (autoRefresh) {
      intervalRef.current = setInterval(() => {
        const startRow = currentPage * rowsPerPage;
        fetchData(startRow);
      }, REFRESH_INTERVAL);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [isVisible, currentPage, autoRefresh, rowsPerPage, fetchData]);

  // Setup countdown timer (only when auto-refresh is enabled)
  useEffect(() => {
    if (!isVisible || !autoRefresh) {
      if (countdownIntervalRef.current) {
        clearInterval(countdownIntervalRef.current);
        countdownIntervalRef.current = null;
      }
      return;
    }

    // Clear any existing countdown interval
    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current);
      countdownIntervalRef.current = null;
    }

    countdownIntervalRef.current = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          return 10; // Reset to 10 when it reaches 0
        }
        return prev - 1;
      });
    }, 1000);

    return () => {
      if (countdownIntervalRef.current) {
        clearInterval(countdownIntervalRef.current);
        countdownIntervalRef.current = null;
      }
    };
  }, [isVisible, autoRefresh]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setDropdownOpen(false);
      }
    };

    if (dropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [dropdownOpen]);

  if (!isVisible) return null;

  return (
    <div 
      onClick={(e) => {
        // Don't stop propagation if clicking on the select or its children
        if (!e.target.closest('.MuiSelect-root') && !e.target.closest('.MuiFormControl-root')) {
          e.stopPropagation();
        }
      }}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      style={{ position: 'absolute', ...position, zIndex: 99999 }}
    >
      <Paper
        ref={tableRef}
        elevation={8}
        sx={{
          p: '1rem',
          minWidth: '40rem',
          maxWidth: '60rem',
          zIndex: 99999,
          bgcolor: 'background.paper',
          borderRadius: '0.5rem',
          boxShadow: theme.shadows[8],
          border: '1px solid',
          borderColor: 'divider',
        }}
      >
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: '1rem' }}>
        <Box>
          <Typography variant="h6" sx={{ fontSize: '1rem', fontWeight: 600 }}>
            Node Data: {nodeId}
          </Typography>
          {autoRefresh && (
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
              Updating in {countdown} seconds
            </Typography>
          )}
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Tooltip title={autoRefresh ? "Auto-refresh ON" : "Auto-refresh OFF"}>
            <Box 
              sx={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}
              onClick={(e) => e.stopPropagation()}
            >
              <AutorenewIcon sx={{ fontSize: '1rem', color: autoRefresh ? 'primary.main' : 'text.disabled' }} />
              <Switch
                checked={autoRefresh}
                onChange={handleAutoRefreshToggle}
                onClick={(e) => e.stopPropagation()}
                size="small"
              />
            </Box>
          </Tooltip>
          <Tooltip title="Refresh Data">
            <IconButton 
              onClick={handleRefresh} 
              disabled={loading} 
              size="small"
            >
              <RefreshIcon sx={{ fontSize: '1.25rem' }} />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Table */}
      <TableContainer sx={{ 
        maxHeight: '20rem', 
        mb: '1rem', 
        overflowX: 'scroll',
        overflowY: 'auto',
      }}>
        {loading && data.length === 0 ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: '2rem' }}>
            <CircularProgress size="2rem" />
          </Box>
        ) : error ? (
          <Box sx={{ p: '2rem', textAlign: 'center' }}>
            <Typography color="error" sx={{ fontSize: '0.875rem' }}>{error}</Typography>
          </Box>
        ) : data.length === 0 ? (
          <Box sx={{ p: '2rem', textAlign: 'center' }}>
            <Typography color="text.secondary" sx={{ fontSize: '0.875rem' }}>No data available</Typography>
          </Box>
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                {columns.map((col) => (
                  <TableCell key={col} sx={{ fontWeight: 600, fontSize: '0.75rem', bgcolor: 'background.elevation1' }}>
                    {col}
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {data.map((row, idx) => (
                <TableRow key={idx} hover>
                  {columns.map((col) => (
                    <TableCell key={col} sx={{ fontSize: '0.75rem' }}>
                      {typeof row[col] === 'object' && row[col] !== null
                        ? JSON.stringify(row[col])
                        : String(row[col] ?? '')}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </TableContainer>

      {/* Pagination Controls */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Typography variant="caption" sx={{ fontSize: '0.75rem' }}>
            {rowsPerPage >= totalRows
              ? `Showing all ${totalRows} rows`
              : `Showing rows ${currentPage * rowsPerPage + 1} - ${Math.min((currentPage + 1) * rowsPerPage, totalRows)} of ${totalRows}`
            }
          </Typography>
          <div
            ref={dropdownRef}
            style={{ position: 'relative', display: 'inline-block' }}
            onClick={(e) => e.stopPropagation()}
            onMouseDown={(e) => e.stopPropagation()}
          >
            <div
              onClick={() => setDropdownOpen(!dropdownOpen)}
              style={{
                fontSize: '0.75rem',
                height: '1.75rem',
                minWidth: '5.5rem',
                borderRadius: '0.25rem',
                border: `1px solid ${theme.palette.divider}`,
                padding: '0 0.5rem',
                backgroundColor: theme.palette.background.paper,
                cursor: 'pointer',
                fontFamily: 'inherit',
                color: theme.palette.text.primary,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                userSelect: 'none',
              }}
            >
              <span>{rowsPerPage}</span>
              <span style={{ marginLeft: '0.25rem', fontSize: '0.6rem' }}>▲</span>
            </div>
            {dropdownOpen && (
              <div
                style={{
                  position: 'absolute',
                  bottom: '100%',
                  left: 0,
                  marginBottom: '0.25rem',
                  minWidth: '5.5rem',
                  backgroundColor: theme.palette.background.paper,
                  border: `1px solid ${theme.palette.divider}`,
                  borderRadius: '0.25rem',
                  boxShadow: theme.shadows[4],
                  zIndex: 100000,
                  maxHeight: '12rem',
                  overflowY: 'auto',
                }}
              >
                {[5, 10, 20, 100].map((option) => (
                  <div
                    key={option}
                    onClick={() => handleRowsPerPageChange(option)}
                    style={{
                      fontSize: '0.75rem',
                      padding: '0.5rem',
                      cursor: 'pointer',
                      backgroundColor: rowsPerPage === option ? theme.palette.action.selected : theme.palette.background.paper,
                      color: theme.palette.text.primary,
                      userSelect: 'none',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = theme.palette.action.hover;
                    }}
                    onMouseLeave={(e) => {
                      if (rowsPerPage !== option) {
                        e.currentTarget.style.backgroundColor = theme.palette.background.paper;
                      } else {
                        e.currentTarget.style.backgroundColor = theme.palette.action.selected;
                      }
                    }}
                  >
                    {option}
                  </div>
                ))}
              </div>
            )}
          </div>
        </Box>
        <Box sx={{ display: 'flex', gap: '0.5rem' }}>
          <Tooltip title={`Previous ${rowsPerPage >= totalRows ? '' : rowsPerPage} rows`}>
            <span>
              <IconButton
                onClick={handlePrevious}
                disabled={currentPage === 0 || loading || rowsPerPage >= totalRows}
                size="small"
                sx={{
                  border: '0.0625rem solid',
                  borderColor: 'divider',
                  borderRadius: '0.375rem',
                }}
              >
                <NavigateBeforeIcon sx={{ fontSize: '1.25rem' }} />
              </IconButton>
            </span>
          </Tooltip>
          <Tooltip title={`Next ${rowsPerPage >= totalRows ? '' : rowsPerPage} rows`}>
            <span>
              <IconButton
                onClick={handleNext}
                disabled={!hasMore || loading || rowsPerPage >= totalRows}
                size="small"
                sx={{
                  border: '0.0625rem solid',
                  borderColor: 'divider',
                  borderRadius: '0.375rem',
                }}
              >
                <NavigateNextIcon sx={{ fontSize: '1.25rem' }} />
              </IconButton>
            </span>
          </Tooltip>
        </Box>
      </Box>
    </Paper>
    </div>
  );
};

export default NodeDataTable;


