import json
import subprocess

def run_tool(tool_name, payload):
    command = [
        "python", "mcp_server_gworkspace.py", "dev"
    ]
    input_message = {
        "type": "tool_call",
        "tool": tool_name,
        "input": payload
    }
    proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    try:
        stdout, stderr = proc.communicate(json.dumps(input_message), timeout=60)
        print("Response:")
        print(stdout)
        if stderr:
            print("Error:")
            print(stderr)
    except subprocess.TimeoutExpired:
        proc.kill()
        print("❌ MCP server call timed out")

if __name__ == "__main__":
    print("Starting test...")
    # Step 1: Create Google Sheet
    sheet_payload = {
        "title": "Test Sheet From MCP"
    }
    run_tool("create_sheet", {"input": sheet_payload})

    # Let's assume we retrieved this ID manually or parsed it from response
    spreadsheet_id = input("Paste the Google Sheet ID returned above: ")
    target_email = input("Enter the email to share with: ")

    # Step 2: Share with email
    share_payload = {
        "file_id": spreadsheet_id,
        "email": target_email
    }
    run_tool("share_file_via_email", {"input": share_payload})

    # Step 3: Send link by Gmail
    email_payload = {
        "to": target_email,
        "subject": "Your Sheet is Ready!",
        "body": f"Here is the link to your sheet: https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
    }
    run_tool("send_email", {"input": email_payload})
