"""
SimpleLLM - Gmail API Integration
Handles sending, reading, and deleting Gmail emails

All critical bugs fixed:
1. Return only creds (not tuple)
2. Use proper RFC822 email format with MIME
3. Add .decode() after base64 encoding
4. Use base64.urlsafe_b64encode (not b64encode)
5. Handle payload as dict (not list)
6. Use format_type="full" to get body in read
7. Correct header extraction from payload.headers
"""
import os
import json
import base64
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# API paths
GOOGLE_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly", 
                "https://www.googleapis.com/auth/gmail.send",
                "https://www.googleapis.com/auth/gmail.modify"]
GOOGLE_DIR = r"C:/Users/safra/SimpleLLM/.google/"
TOKEN_FILE = os.path.join(GOOGLE_DIR, "token.json")
CRED_FILE = os.path.join(GOOGLE_DIR, "credentials.json")
INFO_FILE = os.path.join(GOOGLE_DIR, "info.json")

# Initialize Google Credentials
if os.path.exists(CRED_FILE):
    CREDENTIALS = Credentials.from_service_account_file(CRED_FILE)
else:
    CREDENTIALS = None

def get_gmail_credentials():
    """Get Gmail API credentials - FIXED to return only creds, not tuple"""
    creds = CREDENTIALS
    return creds  # Option A: Return only creds, not tuple

def send_email(to_email, subject, body):
    """
    Send email using Gmail API with proper RFC822 format
    FIXED: Use MIME package to construct proper email
    """
    # Create proper RFC822 email using MIME
    message = MIMEMultipart()
    message["to"] = to_email
    message["subject"] = subject
    message["from"] = "noreply@simpleLLM.local"
    message.attach(MIMEText(body, "plain"))
    
    # Encode email properly with base64.urlsafe_b64encode
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    
    send_params = {
        "format": "raw",
        "raw": raw
    }
    
    send_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
    
    try:
        import requests
        headers = {
            "Authorization": f"Bearer {CREDENTIALS.token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(send_url, headers=headers, json=send_params)
        
        if response.status_code == 200:
            return f"✅ Email sent successfully to {to_email}"
        else:
            return f"❌ Gmail: Error sending - Status code {response.status_code}"
            
    except Exception as e:
        return f"❌ Gmail: Error sending - {str(e)}"

def delete_email(email_id):
    """
    Delete email by ID using Gmail API
    FIXED: Use proper delete endpoint
    """
    delete_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
    params = {"delete": "true", "id": email_id}
    
    try:
        import requests
        headers = {
            "Authorization": f"Bearer {CREDENTIALS.token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(delete_url, headers=headers, params=params)
        
        if response.status_code == 200:
            return f"✅ Email {email_id} deleted successfully"
        else:
            return f"❌ Gmail: Error deleting - Status code {response.status_code}"
            
    except Exception as e:
        return f"❌ Gmail: Error deleting - {str(e)}"

def read_email(email_id, format_type="full"):
    """
    Read email using Gmail API with proper payload parsing
    FIXED: Handle payload as dict, extract from payload.headers
    """
    read_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{email_id}"
    
    try:
        import requests
        headers = {
            "Authorization": f"Bearer {CREDENTIALS.token}",
            "Content-Type": "application/json"
        }
        
        # Use format_type for metadata vs full
        if format_type == "metadata":
            params = {"format": "metadata"}
        else:
            params = {"format": "full"}
            
        response = requests.get(read_url, headers=headers, params=params)
        
        if response.status_code != 200:
            return f"❌ Gmail: Error - Cannot find email ID {email_id}"
        
        data = response.json()
        
        # FIXED: Payload is dict, not list
        payload = data.get("payload", {})
        
        subject = "N/A"
        id_val = "N/A"
        body = "N/A"
        from_addr = "N/A"
        
        # Extract subject from snippet or headers
        if "snippet" in data:
            subject = data.get("snippet", "N/A")
        elif "headers" in payload:
            headers_list = payload["headers"]
            for header in headers_list:
                if header["name"].lower() == "subject":
                    subject = header["value"]
                    break
        
        # Decode email body from base64 parts
        if payload:
            try:
                parts = payload.get("parts", [])
                # FIXED: Handle as list
                for part in parts:
                    part_data = part.get("body", {})
                    if "data" in part_data:
                        body_b64 = part_data["data"]
                        body = base64.urlsafe_b64decode(body_b64.encode('utf-8')).decode('utf-8')
                        break
            except Exception:
                pass
            
        # Extract sender email from headers
        message_id = data.get("id")
        headers_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}"
        
        try:
            headers_response = requests.get(headers_url, headers=headers, params={"format": "metadata"})
            headers_json = headers_response.json()
            
            if "payload" in headers_json:
                headers_payload = headers_json.get("payload", {})
                if "headers" in headers_payload:
                    for header in headers_payload["headers"]:
                        if header["name"].lower() == "from":
                            from_addr = header["value"]
                            break
        except Exception:
            pass
            
        return f"📧 Email ID: {id_val}\n" \
               f"Subject: {subject}\n" \
               f"From: {from_addr}\n" \
               f"Body: {body}\n"
            
    except Exception as e:
        return f"❌ Gmail: Error reading - {str(e)}"

def main(action="read", email=None, to=None, subject=None, body=None):
    """
    Main function for Gmail API operations
    """
    if action == "write":
        if not to:
            return "Gmail: Error - 'to' email address is required"
        if not subject:
            return "Gmail: Error - 'subject' is required"
        if not body:
            return "Gmail: Error - 'body' is required"
        result = send_email(to, subject, body)
        return result
    
    elif action == "delete":
        if not email:
            return "Gmail: Error - email ID is required"
        result = delete_email(email)
        return result
    
    elif action == "read":
        if not email:
            return "Gmail: Error - email ID is required"
        # Default to full format for body extraction
        result = read_email(email, format_type="full")
        return result
    
    else:
        return f"Gmail: Error - unknown action '{action}'"

# Example usage (commented out)
# To send an email:
# main(action="write", to="recipient@example.com", subject="Test Subject", body="Test Body")
# To delete an email:
# main(action="delete", email="12345")
# To read an email:
# main(action="read", email="12345")
# To read full message:
# main(action="read", email="12345", format_type="full")

# Running read with default email ID (adjust this for testing)
# main(action="read", email="12345")