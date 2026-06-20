"""
Connector functions for WhatsApp
Simple functions to send messages via WhatsApp (Twilio)
"""
import os
from twilio.rest import Client
from dotenv import load_dotenv
from fastapi import APIRouter
from pydantic import BaseModel
import logging

load_dotenv()
logging.getLogger("twilio").setLevel(logging.WARNING)
router = APIRouter()

# Twilio WhatsApp credentials (free tier)
WHATSAPP_SID = os.getenv("WHATSAPP_SID")
WHATSAPP_AUTH = os.getenv("WHATSAPP_AUTH")
WHATSAPP_FROM = os.getenv("WHATSAPP_FROM", "whatsapp:+14155238886")

# Initialize Twilio client on module load
_twilio_client = None
if WHATSAPP_SID and WHATSAPP_AUTH:
    try:
        _twilio_client = Client(WHATSAPP_SID, WHATSAPP_AUTH)
        print("✅ Twilio WhatsApp connected", flush=True)
    except Exception:
        pass


def send_whatsapp_message(number: str, message: str) -> dict:
    """
    Send WhatsApp message using Twilio (free tier compatible)
    
    Args:
        number: Phone number (e.g., "1234567890" or "+911234567890")
        message: Message text
        
    Returns:
        dict: Response with success status and details
    """
    if not WHATSAPP_SID or not WHATSAPP_AUTH:
        return {
            "success": False,
            "error": "WhatsApp credentials not configured. Set WHATSAPP_SID and WHATSAPP_AUTH in .env"
        }
    
    if not number or not message:
        return {
            "success": False,
            "error": "Number and message are required"
        }
    
    try:
        # Use pre-initialized client or create new one
        client = _twilio_client if _twilio_client else Client(WHATSAPP_SID, WHATSAPP_AUTH)
        
        # Format phone number - add whatsapp: prefix and handle country code
        phone_number = number.strip()
        if not phone_number.startswith("whatsapp:"):
            if not phone_number.startswith("+"):
                # Add +91 as default country code if not provided
                phone_number = f"whatsapp:+91{phone_number}"
            else:
                phone_number = f"whatsapp:{phone_number}"
        
        # Send message
        twilio_message = client.messages.create(
            to=phone_number,
            from_=WHATSAPP_FROM,
            body=message
        )
        
        # Fetch updated status after a brief delay (Twilio updates asynchronously)
        # Initial status is often "queued" even if it will send successfully
        import time
        time.sleep(0.8)  # Small delay to let Twilio update status
        
        try:
            # Fetch the latest status
            updated_message = client.messages(twilio_message.sid).fetch()
            current_status = updated_message.status
        except:
            # Fallback to initial status if fetch fails
            current_status = twilio_message.status
        
        # Prepare response
        status_info = {
            "success": True,
            "message": "WhatsApp message accepted by Twilio",
            "message_sid": twilio_message.sid,
            "status": current_status,
            "to": phone_number,
            "check_status_url": f"/connectors/whatsapp/status/{twilio_message.sid}"
        }
        
        # Add helpful notes based on status
        if current_status == "queued":
            status_info["message"] = "Message queued - this is initial status"
            status_info["note"] = (
                "Status shows 'queued' - this is normal initially. Twilio updates status "
                "asynchronously to 'sent' → 'delivered'. If recipient has joined WhatsApp "
                "Sandbox, message will be sent. Check current status: GET /connectors/whatsapp/status/{message_sid}"
            )
            status_info["tip"] = "Use check_status_url to get the latest status after a few seconds"
        elif current_status == "sent":
            status_info["message"] = "✅ WhatsApp message sent successfully!"
            status_info["note"] = "Message has been sent to WhatsApp and should arrive shortly."
        elif current_status == "delivered":
            status_info["message"] = "✅ WhatsApp message delivered!"
            status_info["note"] = "Message has been delivered to the recipient's phone."
        elif current_status == "failed":
            status_info["success"] = False
            status_info["message"] = "❌ Message failed to send"
            try:
                error_msg = updated_message.error_message if 'updated_message' in locals() else twilio_message.error_message
                status_info["note"] = f"Check Twilio Console for details. Error: {error_msg or 'Unknown error'}"
            except:
                status_info["note"] = "Check Twilio Console for error details."
        else:
            status_info["message"] = f"Message status: {current_status}"
            status_info["note"] = f"Current status: {current_status}. Use check_status_url for updates."
        
        return status_info
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to send WhatsApp message: {str(e)}"
        }


def check_whatsapp_status(message_sid: str) -> dict:
    """
    Check the delivery status of a WhatsApp message
    
    Args:
        message_sid: Twilio message SID (from send_whatsapp_message response)
        
    Returns:
        dict: Current status of the message
    """
    if not WHATSAPP_SID or not WHATSAPP_AUTH:
        return {
            "success": False,
            "error": "WhatsApp credentials not configured"
        }
    
    if not message_sid:
        return {
            "success": False,
            "error": "Message SID is required"
        }
    
    try:
        # Use pre-initialized client or create new one
        client = _twilio_client if _twilio_client else Client(WHATSAPP_SID, WHATSAPP_AUTH)
        message = client.messages(message_sid).fetch()
        
        return {
            "success": True,
            "message_sid": message.sid,
            "status": message.status,
            "date_created": str(message.date_created),
            "date_sent": str(message.date_sent) if message.date_sent else None,
            "date_updated": str(message.date_updated),
            "error_code": message.error_code,
            "error_message": message.error_message,
            "to": message.to,
            "from": message.from_
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to check message status: {str(e)}"
        }




class WhatsAppRequest(BaseModel):
    number: str
    message: str

@router.post("/send")
def whatsapp_send_route(request: WhatsAppRequest):
    """
    Send WhatsApp message via Twilio (free tier compatible)
    
    Example:
        POST /connectors/whatsapp/send
        {
            "number": "1234567890",
            "message": "Hello from API!"
        }
    """
    return send_whatsapp_message(request.number, request.message)

@router.get("/status/{message_sid}")
def whatsapp_status_route(message_sid: str):
    """
    Check the delivery status of a WhatsApp message
    
    Example:
        GET /connectors/whatsapp/status/SM80be931f8172ae9b0dbb99d50b5c91db
    """
    return check_whatsapp_status(message_sid)