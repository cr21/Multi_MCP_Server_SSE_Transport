import os
import time
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')  # You can set this in your .env file or hardcode it

def send_message(message: str):
    """Send a message to the Telegram bot."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = httpx.post(url, json=data)
        response.raise_for_status()
        print(f"Message sent: {message}")
    except Exception as e:
        print(f"Failed to send message: {str(e)}")

def main():
    """Main function to run the client."""
    while True:
        message = input("Enter a message to send to the bot (or 'exit' to quit): ")
        if message.lower() == 'exit':
            break
        send_message(message)
        time.sleep(1)  # Optional: wait a bit before sending the next message

if __name__ == "__main__":
    main()
