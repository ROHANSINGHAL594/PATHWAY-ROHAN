import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Chip,
  TextField,
  Alert,
  CircularProgress,
  Divider,
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import WarningIcon from '@mui/icons-material/Warning';

/**
 * ApprovalDialog - Component for handling remediation action approvals
 * 
 * Props:
 * - open: boolean - Whether dialog is open
 * - onClose: function - Callback when dialog closes
 * - notification: object - Notification data with approval request details
 * - pipelineId: string - Current pipeline ID
 * - onApprove: function(requestId, actionId, approvedBy) - Callback when approved
 * - onReject: function(requestId, actionId, rejectedBy, reason) - Callback when rejected
 */
const ApprovalDialog = ({ open, onClose, notification, pipelineId, onApprove, onReject }) => {
  const [rejectionReason, setRejectionReason] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  if (!notification) return null;

  const {
    request_id,
    error_message,
    matched_error,
    confidence,
    actions = [],
    description,
    approval_type,
    actions_requiring_individual_approval = [],
  } = notification.data || {};

  const handleApprove = async (actionId = null) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_SERVER}/agentic/${pipelineId}/runbook/remediate/approve`,
        {
          method: 'POST',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            request_id,
            action_id: actionId,
            approved: true,
            approved_by: 'frontend_user',
          }),
        }
      );

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to approve: ${errorText || response.status}`);
      }

      const result = await response.json();
      console.log('Approval successful:', result);

      if (onApprove) {
        onApprove(request_id, actionId, 'frontend_user');
      }

      onClose();
    } catch (err) {
      console.error('Error approving request:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleReject = async () => {
    if (!rejectionReason.trim()) {
      setError('Please provide a reason for rejection');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_SERVER}/agentic/${pipelineId}/runbook/remediate/approve`,
        {
          method: 'POST',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            request_id,
            approved: false,
            approved_by: 'frontend_user',
            rejection_reason: rejectionReason,
          }),
        }
      );

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to reject: ${errorText || response.status}`);
      }

      const result = await response.json();
      console.log('Rejection successful:', result);

      if (onReject) {
        onReject(request_id, null, 'frontend_user', rejectionReason);
      }

      onClose();
    } catch (err) {
      console.error('Error rejecting request:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getConfidenceColor = () => {
    switch (confidence) {
      case 'high':
        return 'success';
      case 'medium':
        return 'warning';
      case 'low':
        return 'error';
      default:
        return 'default';
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 2,
        },
      }}
    >
      <DialogTitle sx={{ pb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <WarningIcon color="warning" />
          <Typography variant="h6">Approval Required</Typography>
        </Box>
      </DialogTitle>

      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {/* Error Information */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            Error Message
          </Typography>
          <Typography variant="body1" sx={{ mb: 2 }}>
            {error_message}
          </Typography>

          {matched_error && (
            <>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Matched Error
              </Typography>
              <Typography variant="body1" sx={{ mb: 2 }}>
                {matched_error}
              </Typography>
            </>
          )}

          {description && (
            <>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Description
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                {description}
              </Typography>
            </>
          )}

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <Typography variant="subtitle2" color="text.secondary">
              Confidence:
            </Typography>
            <Chip
              label={confidence?.toUpperCase() || 'UNKNOWN'}
              color={getConfidenceColor()}
              size="small"
            />
          </Box>
        </Box>

        <Divider sx={{ mb: 2 }} />

        {/* Actions to be executed */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            Actions to Execute ({actions.length})
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1 }}>
            {actions.map((actionId, index) => (
              <Chip
                key={index}
                label={actionId}
                variant="outlined"
                size="small"
                color={
                  actions_requiring_individual_approval.includes(actionId)
                    ? 'warning'
                    : 'default'
                }
              />
            ))}
          </Box>
        </Box>

        {/* Approval Type Info */}
        {approval_type && (
          <Alert severity="info" sx={{ mb: 2 }}>
            <Typography variant="body2">
              {approval_type === 'per-action'
                ? 'This request requires individual approval for some actions.'
                : 'This request requires approval for all actions due to confidence level.'}
            </Typography>
          </Alert>
        )}

        {/* Rejection Reason */}
        <Box sx={{ mb: 2 }}>
          <TextField
            fullWidth
            multiline
            rows={3}
            label="Rejection Reason (optional for approval, required for rejection)"
            value={rejectionReason}
            onChange={(e) => setRejectionReason(e.target.value)}
            placeholder="Provide a reason if rejecting this request..."
            variant="outlined"
          />
        </Box>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} disabled={loading}>
          Cancel
        </Button>
        <Button
          onClick={handleReject}
          disabled={loading}
          variant="outlined"
          color="error"
          startIcon={loading ? <CircularProgress size={16} /> : <CancelIcon />}
        >
          Reject
        </Button>
        <Button
          onClick={() => handleApprove(null)}
          disabled={loading}
          variant="contained"
          color="success"
          startIcon={loading ? <CircularProgress size={16} /> : <CheckCircleIcon />}
        >
          Approve All
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ApprovalDialog;
