description = "Sends, reads, and deletes Gmail emails using the Gmail API with OAuth2 authentication."

args = {
    "action": {
        "type": "string",
        "values": ["send", "read", "delete"]
    },
    "email": {
        "type": "string",
        "description": "Gmail message ID for reading or deleting emails"
    },
    "subject": {
        "type": "string",
        "description": "Subject line for outgoing email"
    },
    "body": {
        "type": "string",
        "description": "Body content for outgoing email"
    },
    "to": {
        "type": "string",
        "description": "Recipient email address"
    }
}

required = ["action"]

"""
SimpleLLM Gmail Integration
Production-style Gmail API wrapper with:
- OAuth2 authentication
- Token refresh
- Email sending
- Email reading
- Email deletion
- MIME encoding
- Gmail API compliance
"""

import os
import base64
import requests

from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


# ==========================================
# CONFIG
# ==========================================

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify"
]

GOOGLE_DIR = r"C:/Users/safra/SimpleLLM/.google"

TOKEN_FILE = os.path.join(GOOGLE_DIR, "token.json")
CREDENTIALS_FILE = os.path.join(GOOGLE_DIR, "credentials.json")


# ==========================================
# AUTH
# ==========================================

def get_gmail_credentials():
    """
    Load, refresh, or create OAuth credentials
    """

    creds = None

    # Load existing token
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(
                TOKEN_FILE,
                SCOPES
            )
        except Exception:
            creds = None

    # Refresh expired token
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())

            with open(TOKEN_FILE, "w") as token:
                token.write(creds.to_json())

        except Exception:
            creds = None

    # First login
    if not creds or not creds.valid:

        if not os.path.exists(CREDENTIALS_FILE):
            raise FileNotFoundError(
                f"Missing credentials file: {CREDENTIALS_FILE}"
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_FILE,
            SCOPES
        )

        creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return creds


# ==========================================
# SEND EMAIL
# ==========================================

def send_email(to_email, subject, body):
    """
    Send Gmail email
    """

    try:

        creds = get_gmail_credentials()

        # Build MIME email
        message = MIMEText(body)

        message["To"] = to_email
        message["Subject"] = subject
        message["From"] = "me"

        # Encode message
        raw_message = base64.urlsafe_b64encode(
            message.as_bytes()
        ).decode("utf-8")

        payload = {
            "raw": raw_message
        }

        headers = {
            "Authorization": f"Bearer {creds.token}",
            "Content-Type": "application/json"
        }

        url = (
            "https://gmail.googleapis.com/"
            "gmail/v1/users/me/messages/send"
        )

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=15
        )

        if response.status_code in [200, 202]:

            data = response.json()

            return (
                f"✅ Email sent successfully\n"
                f"Message ID: {data.get('id', 'unknown')}"
            )

        return (
            f"❌ Failed to send email\n"
            f"Status: {response.status_code}\n"
            f"{response.text}"
        )

    except Exception as e:
        return f"❌ Gmail send error: {str(e)}"


# ==========================================
# READ EMAIL
# ==========================================

def extract_plain_text(payload):
    """
    Recursively extract plain text body
    """

    if not payload:
        return None

    mime_type = payload.get("mimeType", "")

    # Direct text/plain
    if mime_type == "text/plain":

        body_data = (
            payload.get("body", {})
            .get("data")
        )

        if body_data:
            try:
                return base64.urlsafe_b64decode(
                    body_data
                ).decode("utf-8")

            except Exception:
                return "[Unable to decode body]"

    # Multipart recursive search
    for part in payload.get("parts", []):

        result = extract_plain_text(part)

        if result:
            return result

    return None


def read_email(email_id):
    """
    Read Gmail message
    """

    try:

        creds = get_gmail_credentials()

        headers = {
            "Authorization": f"Bearer {creds.token}"
        }

        url = (
            f"https://gmail.googleapis.com/"
            f"gmail/v1/users/me/messages/{email_id}"
        )

        response = requests.get(
            url,
            headers=headers,
            params={"format": "full"},
            timeout=15
        )

        if response.status_code != 200:

            return (
                f"❌ Failed to read email\n"
                f"Status: {response.status_code}\n"
                f"{response.text}"
            )

        data = response.json()

        payload = data.get("payload", {})

        headers_list = payload.get("headers", [])

        subject = "N/A"
        sender = "N/A"
        date = "N/A"

        for header in headers_list:

            name = header.get("name", "").lower()

            if name == "subject":
                subject = header.get("value", "N/A")

            elif name == "from":
                sender = header.get("value", "N/A")

            elif name == "date":
                date = header.get("value", "N/A")

        body = extract_plain_text(payload)

        if not body:
            body = "[No readable text body found]"

        return (
            f"📧 Email ID: {data.get('id', 'N/A')}\n\n"
            f"From: {sender}\n"
            f"Date: {date}\n"
            f"Subject: {subject}\n\n"
            f"Body:\n{body}"
        )

    except Exception as e:
        return f"❌ Gmail read error: {str(e)}"


# ==========================================
# DELETE EMAIL
# ==========================================

def delete_email(email_id):
    """
    Delete Gmail message
    """

    try:

        creds = get_gmail_credentials()

        headers = {
            "Authorization": f"Bearer {creds.token}"
        }

        url = (
            f"https://gmail.googleapis.com/"
            f"gmail/v1/users/me/messages/{email_id}"
        )

        response = requests.delete(
            url,
            headers=headers,
            timeout=15
        )

        if response.status_code in [200, 204]:

            return (
                f"✅ Email deleted successfully\n"
                f"Message ID: {email_id}"
            )

        return (
            f"❌ Failed to delete email\n"
            f"Status: {response.status_code}\n"
            f"{response.text}"
        )

    except Exception as e:
        return f"❌ Gmail delete error: {str(e)}"


# ==========================================
# MAIN ROUTER
# ==========================================

def main(action, email=None, subject=None, body=None, to=None):
    """
    Gmail tool router
    """

    try:

        action = action.lower().strip()

        if action == "send":

            if not to:
                return "❌ Missing recipient email address"

            if not subject:
                return "❌ Missing email subject"

            if not body:
                return "❌ Missing email body"

            return send_email(
                to_email=to,
                subject=subject,
                body=body
            )

        elif action == "read":

            if not email:
                return "❌ Missing Gmail message ID"

            return read_email(email)

        elif action == "delete":

            if not email:
                return "❌ Missing Gmail message ID"

            return delete_email(email)

        else:

            return (
                f"❌ Unknown action: {action}\n"
                f"Valid actions: send, read, delete"
            )

    except Exception as e:
        return f"❌ Gmail tool error: {str(e)}"


# ==========================================
# EXAMPLES
# ==========================================

# SEND EMAIL
# main(
#     action="send",
#     to="example@gmail.com",
#     subject="Hello",
#     body="This is a test email"
# )

# READ EMAIL
# main(
#     action="read",
#     email="MESSAGE_ID"
# )

# DELETE EMAIL
# main(
#     action="delete",
#     email="MESSAGE_ID"
# )