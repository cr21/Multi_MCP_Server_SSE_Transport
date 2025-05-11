from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel
from typing import List, Dict, Any
import os
import json
import google.auth
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import re

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

# === Helper Functions ===
def format_f1_data(data: str) -> List[List[str]]:
    """Format F1 standings data into a clean spreadsheet format."""
    # Add headers
    formatted_data = [["Position", "Driver", "Nationality", "Team", "Points"]]
    
    try:
        # If data is in JSON format with markdown field
        if isinstance(data, str) and data.startswith("{"):
            json_data = json.loads(data)
            if "markdown" in json_data:
                data = json_data["markdown"]
        
        # Process each line
        for line in data.split('\n'):
            if not line.strip():
                continue
            
            # Split by | and clean up
            parts = [p.strip() for p in line.split('|') if p.strip()]
            if len(parts) >= 4:  # Minimum required parts
                position = re.sub(r'\D', '', parts[0])  # Extract only numbers
                
                # Clean up driver name (remove codes like VER, HAM)
                driver_part = parts[1]
                driver_name = ' '.join(word for word in driver_part.split() 
                                     if not (word.isupper() and len(word) == 3))
                
                nationality = parts[2]
                team = parts[3]
                points = parts[4] if len(parts) > 4 else "0"
                
                # Clean up points (remove non-numeric characters)
                points = re.sub(r'[^\d.]', '', points)
                
                formatted_data.append([position, driver_name.strip(), 
                                     nationality.strip(), team.strip(), points.strip()])
    except Exception as e:
        print(f"Error formatting F1 data: {e}")
        # Return empty data with headers if formatting fails
        return [["Position", "Driver", "Nationality", "Team", "Points"]]
    
    return formatted_data

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
    """Append data to a Google Sheet. If the data looks like F1 standings, it will be automatically formatted.
    Usage: append_to_sheet|input={"spreadsheet_id": "...", "range": "...", "values": [[...]]}"""
    try:
        service = build("sheets", "v4", credentials=credentials)
        
        # Check if this might be F1 data that needs formatting
        if len(input.values) == 1 and isinstance(input.values[0], list) and len(input.values[0]) == 1:
            # This might be raw F1 data
            raw_data = input.values[0][0]
            if isinstance(raw_data, str) and ('|' in raw_data or raw_data.startswith('{')):
                formatted_values = format_f1_data(raw_data)
            else:
                formatted_values = input.values
        else:
            formatted_values = input.values

        body = {"values": formatted_values}
        
        # Format the sheet
        service.spreadsheets().values().append(
            spreadsheetId=input.spreadsheet_id,
            range=input.range,
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body=body
        ).execute()
        
        # Auto-format the sheet
        requests = [
            {
                "autoResizeDimensions": {
                    "dimensions": {
                        "sheetId": 0,
                        "dimension": "COLUMNS",
                        "startIndex": 0,
                        "endIndex": len(formatted_values[0])
                    }
                }
            },
            {
                "repeatCell": {
                    "range": {
                        "sheetId": 0,
                        "startRowIndex": 0,
                        "endRowIndex": 1
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9},
                            "textFormat": {"bold": True}
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat)"
                }
            }
        ]
        
        service.spreadsheets().batchUpdate(
            spreadsheetId=input.spreadsheet_id,
            body={"requests": requests}
        ).execute()
        
        return "Data appended and formatted successfully."
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