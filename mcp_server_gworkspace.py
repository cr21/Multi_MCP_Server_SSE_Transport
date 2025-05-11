from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel
from typing import List
import os
import json
import google.auth
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# === Setup Google Service Account ===
SERVICE_ACCOUNT_FILE = "gworkspace_service_account.json"
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets"
]

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)

# === Initialize MCP Server ===
mcp = FastMCP("gworkspace-tools")

# === Tool Input Schemas ===
class EmailInput(BaseModel):
    to: str
    subject: str
    body: str

class CreateSheetInput(BaseModel):
    title: str

class AppendSheetInput(BaseModel):
    spreadsheet_id: str
    range: str
    values: List[List[str]]

class ShareFileInput(BaseModel):
    file_id: str
    email: str

# === Tools ===
@mcp.tool()
def send_email(input: EmailInput) -> str:
    """Send an email using Gmail. Usage: send_email|input={"to": "...", "subject": "...", "body": "..."}"""
    try:
        service = build("gmail", "v1", credentials=credentials)
        message = {
            "raw": base64.urlsafe_b64encode(
                f"To: {input.to}\r\nSubject: {input.subject}\r\n\r\n{input.body}".encode("utf-8")
            ).decode("utf-8")
        }
        result = service.users().messages().send(userId="me", body=message).execute()
        return f"Email sent with ID: {result['id']}"
    except HttpError as error:
        return f"Failed to send email: {error}"

@mcp.tool()
def create_sheet(input: CreateSheetInput) -> str:
    """Create a new Google Sheet. Usage: create_sheet|input={"title": "My Sheet"}"""
    try:
        service = build("sheets", "v4", credentials=credentials)
        spreadsheet = {
            "properties": {
                "title": input.title
            }
        }
        sheet = service.spreadsheets().create(body=spreadsheet, fields="spreadsheetId").execute()
        return f"Spreadsheet created: {sheet['spreadsheetId']}"
    except HttpError as error:
        return f"Failed to create sheet: {error}"

@mcp.tool()
def append_to_sheet(input: AppendSheetInput) -> str:
    """Append data to a Google Sheet. Usage: append_to_sheet|input={"spreadsheet_id": "...", "range": "...", "values": [[...]]}"""
    try:
        service = build("sheets", "v4", credentials=credentials)
        body = {"values": input.values}
        service.spreadsheets().values().append(
            spreadsheetId=input.spreadsheet_id,
            range=input.range,
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body=body
        ).execute()
        return "Data appended successfully."
    except HttpError as error:
        return f"Failed to append to sheet: {error}"

@mcp.tool()
def share_file_via_email(input: ShareFileInput) -> str:
    """Share a file with a user via email. Usage: share_file_via_email|input={"file_id": "...", "email": "..."}"""
    try:
        service = build("drive", "v3", credentials=credentials)
        permission = {
            "type": "user",
            "role": "writer",
            "emailAddress": input.email
        }
        service.permissions().create(
            fileId=input.file_id,
            body=permission,
            sendNotificationEmail=True
        ).execute()
        return f"File shared with {input.email}"
    except HttpError as error:
        return f"Failed to share file: {error}"

# === Server Startup ===
if __name__ == "__main__":
    import sys
    import base64

    print("MCP GWorkspace server starting...")
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        mcp.run()
    else:
        mcp.run(transport="stdio")