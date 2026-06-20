import os
from pathlib import Path
from dotenv import load_dotenv
import logging
from typing import Optional, List
import slack_sdk
load_dotenv()

logger = logging.getLogger(__name__)


def _get_slack_client():
    """Get Slack client with token from environment."""
    slack_token = os.environ.get('SLACK_TOKEN', '')
    if not slack_token:
        return None
    try:
        return slack_sdk.WebClient(token=slack_token)
    except ImportError:
        logger.warning("slack_sdk not installed. Run: pip install slack_sdk")
        return None


def text_channel(channel_id: str, message: str) -> dict:
    """Send a text message to a Slack channel."""
    client = _get_slack_client()
    if not client:
        return {"ok": False, "error": "Slack client not configured"}
    try:
        response = client.chat_postMessage(
            channel=channel_id,
            text=message
        )
        return response
    except Exception as e:
        logger.error(f"Failed to send message to channel {channel_id}: {e}")
        return {"ok": False, "error": str(e)}


def dm_user(user_id: str, message: str) -> dict:
    """Send a direct message to a Slack user."""
    client = _get_slack_client()
    if not client:
        return {"ok": False, "error": "Slack client not configured"}

    try:
        response = client.chat_postMessage(
            channel=user_id,
            text=message
        )
        return response
    except Exception as e:
        logger.error(f"Failed to send DM to user {user_id}: {e}")
        return {"ok": False, "error": str(e)}


def send_file_to_channel(
    channel_id: str,
    file_path: str,
    message: Optional[str] = None,
    title: Optional[str] = None,
    filename: Optional[str] = None
) -> dict:
    """
    Send a file (PDF, image, etc.) to a Slack channel.

    Args:
        channel_id: The Slack channel ID
        file_path: Path to the file on the server
        message: Optional message to accompany the file
        title: Optional title for the file
        filename: Optional filename to display (defaults to actual filename)

    Returns:
        Slack API response dict
    """
    client = _get_slack_client()
    if not client:
        return {"ok": False, "error": "Slack client not configured"}

    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return {"ok": False, "error": f"File not found: {file_path}"}

    try:
        response = client.files_upload_v2(
            channel=channel_id,
            file=file_path,
            title=title or os.path.basename(file_path),
            filename=filename or os.path.basename(file_path),
            initial_comment=message
        )
        return response
    except Exception as e:
        logger.error(f"Failed to upload file to channel {channel_id}: {e}")
        return {"ok": False, "error": str(e)}


def send_message_with_files(
    channel_id: str,
    message: str,
    file_paths: Optional[List[str]] = None,
    blocks: Optional[List[dict]] = None
) -> dict:
    """
    Send a message with optional file attachments and rich formatting.

    Args:
        channel_id: The Slack channel ID
        message: The message text
        file_paths: Optional list of file paths to attach
        blocks: Optional Slack blocks for rich formatting

    Returns:
        Slack API response dict
    """
    client = _get_slack_client()
    if not client:
       return {"ok": False, "error": "Slack client not configured"}

    try:
        # First send the message
        msg_response = client.chat_postMessage(
            channel=channel_id,
            text=message,
            blocks=blocks
        )

        if not msg_response.get("ok"):
            return msg_response

        # Then upload files if provided
        if file_paths:
            thread_ts = msg_response.get("ts")  # Reply in thread
            for file_path in file_paths:
                if os.path.exists(file_path):
                    client.files_upload_v2(
                        channel=channel_id,
                        file=file_path,
                        thread_ts=thread_ts,
                        filename=os.path.basename(file_path)
                    )
                else:
                    logger.warning(f"File not found, skipping: {file_path}")

        return msg_response
    except Exception as e:
        logger.error(f"Failed to send message with files: {e}")
        return {"ok": False, "error": str(e)}


def send_slack_notification(notification_data: dict, file_paths: Optional[List[str]] = None) -> bool:
    """
    Send notification to Slack channel if configured.
    Supports file attachments (PDFs, images, etc.)

    Args:
        notification_data: Dict with notification details (type, title, desc, pipeline_id, etc.)
        file_paths: Optional list of file paths to attach

    Returns:
        True if sent successfully, False otherwise.
    """
    slack_token = os.environ.get('SLACK_TOKEN', '')
    slack_channel = os.environ.get('SLACK_CHANNEL', '')

    if not slack_token or not slack_channel:
        logger.debug("Slack not configured (SLACK_TOKEN or SLACK_CHANNEL missing)")
        return False

    client = _get_slack_client()
    if not client:
        return False

    try:
        # Format the notification message
        notification_type = notification_data.get('type', 'info').upper()
        title = notification_data.get('title', 'Notification')
        desc = notification_data.get('desc', notification_data.get('description', ''))
        pipeline_id = notification_data.get('pipeline_id', 'N/A')

        # Create formatted Slack message with blocks for better formatting
        message = f"*[{notification_type}]* {title}\n"
        message += f"Pipeline: `{pipeline_id}`\n"
        if desc:
            message += f"Description: {desc}\n"

        # Add alert-specific info if present
        if notification_data.get('alert'):
            alert = notification_data['alert']
            if alert.get('actions'):
                message += f"Actions available: {', '.join(alert['actions'])}\n"
            if alert.get('status'):
                message += f"Status: {alert['status']}\n"

        # Add RCA-specific info if present
        if notification_data.get('rca_event'):
            message += "\n*RCA Event Details:*\n"
            if notification_data.get('trace_ids'):
                message += f"Trace IDs: {', '.join(notification_data['trace_ids'])}\n"
            if notification_data.get('metadata'):
                message += f"Metadata: {notification_data['metadata']}\n"

        # Send message (with files if provided)
        if file_paths:
            response = send_message_with_files(slack_channel, message, file_paths)
        else:
            response = client.chat_postMessage(
                channel=slack_channel,
                text=message
            )

        return response.get('ok', False)
    except Exception as e:
        logger.error(f"Failed to send Slack notification: {e}")
        return False


def send_critical_log_notification(log_data: dict) -> bool:
    """
    Send critical log to Slack channel.
    Only sends logs with level 'critical', 'error'.

    Args:
        log_data: Dict with log details (level, message, pipeline_id, etc.)

    Returns:
        True if sent successfully, False otherwise.
    """
    level = log_data.get('level', '').lower()

    slack_channel = os.environ.get('SLACK_CHANNEL', '')
    if not slack_channel:
        return False

    client = _get_slack_client()
    if not client:
        return False

    try:
        pipeline_id = log_data.get('pipeline_id', 'N/A')
        message = log_data.get('message', 'No message')
        source = log_data.get('source', 'unknown')
        timestamp = log_data.get('timestamp', 'N/A')

        # Create alert-style message for critical logs
        slack_message = (
            f"🚨 *{level.upper()} LOG ALERT* 🚨\n"
            f"*Pipeline:* `{pipeline_id}`\n"
            f"*Source:* {source}\n"
            f"*Message:* {message}\n"
            f"*Timestamp:* {timestamp}\n"
        )

        if log_data.get('details'):
            slack_message += f"*Details:* ```{log_data['details']}```\n"

        response = client.chat_postMessage(
            channel=slack_channel,
            text=slack_message
        )
        return response.get('ok', False)
    except Exception as e:
        logger.error(f"Failed to send critical log notification: {e}")
        return False


def send_rca_update_notification(rca_data: dict, operation_type: str = "update") -> bool:
    """
    Send RCA event update to Slack channel with optional PDF attachment.

    Args:
        rca_data: Dict with RCA event details
        operation_type: 'insert' for new RCA, 'update' for updates

    Returns:
        True if sent successfully, False otherwise.
    """
    slack_channel = os.environ.get('SLACK_CHANNEL', '')
    if not slack_channel:
        return False

    client = _get_slack_client()
    if not client:
        return False

    try:
        pipeline_id = rca_data.get('pipeline_id', 'N/A')
        title = rca_data.get('title', 'RCA Event')
        description = rca_data.get('description', '')
        triggered_at = rca_data.get('triggered_at', 'N/A')
        trace_ids = rca_data.get('trace_ids', [])
        metadata = rca_data.get('metadata', {})
        status = metadata.get('status', 'in_progress') if isinstance(metadata, dict) else 'unknown'

        # Determine emoji and header based on operation type
        if operation_type == "insert":
            emoji = "🔍"
            header = "NEW RCA ANALYSIS STARTED"
        else:
            emoji = "📊"
            header = "RCA ANALYSIS UPDATED"

        # Create formatted message
        slack_message = (
            f"{emoji} *{header}* {emoji}\n"
            f"*Title:* {title}\n"
            f"*Pipeline:* `{pipeline_id}`\n"
            f"*Status:* {status}\n"
        )

        if description:
            slack_message += f"*Description:* {description}\n"

        if trace_ids:
            slack_message += f"*Trace IDs:* {', '.join(str(t) for t in trace_ids)}\n"

        slack_message += f"*Triggered At:* {triggered_at}\n"

        # Check for PDF path in metadata
        pdf_path = None
        if isinstance(metadata, dict):
            pdf_path = metadata.get('pdf_path') or metadata.get('report_path')

        # Send with PDF if available
        if pdf_path and os.path.exists(pdf_path):
            response = send_message_with_files(
                slack_channel, 
                slack_message, 
                [pdf_path]
            )
        else:
            response = client.chat_postMessage(
                channel=slack_channel,
                text=slack_message
            )

        return response.get('ok', False)
    except Exception as e:
        logger.error(f"Failed to send RCA update notification: {e}")
        return False