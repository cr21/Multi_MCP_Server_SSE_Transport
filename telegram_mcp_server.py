from mcp.server.fastmcp import FastMCP, Context
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import urllib.parse
import sys
import traceback
import asyncio
from datetime import datetime, timedelta
import time
import re
import os
import threading
from dotenv import load_dotenv

# Load environment variables at the start
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Initialize FastMCP server
mcp = FastMCP("telegram-mcp-server")

class TelegramBot:
    def __init__(self):
        print("Initializing TelegramBot...")
        self.app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Add handlers
        print("Setting up message handlers...")
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.app.add_handler(CommandHandler("getchatid", self.get_chat_id_command))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        print(f"Received /start command from user {update.effective_user.id}")
        await update.message.reply_text(
            "👋 Hello! I'm your AI assistant. How can I help you today?"
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        message_text = update.message.text
        
        print(f"\n{'='*50}")
        print(f"Received new message:")
        print(f"From User ID: {user_id}")
        print(f"Chat ID: {chat_id}")
        print(f"Message: {message_text}")
        print(f"{'='*50}\n")
        
        try:
            # Send typing indicator
            await update.message.chat.send_action(action="typing")
            
            # Echo the message back (for testing)
            await update.message.reply_text(f"Processing your request wait for some time:")
            
        except Exception as e:
            print(f"Error handling message: {str(e)}")
            error_msg = f"Sorry, an error occurred: {str(e)}"
            await update.message.reply_text(error_msg)

    async def get_chat_id_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /getchatid command"""
        chat_id = update.message.chat.id
        print(f"Chat ID requested: {chat_id}")
        await update.message.reply_text(f"Your Chat ID is: {chat_id}")

    def run(self):
        """Run the bot"""
        print("Starting Telegram bot...")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)
        print("Telegram bot is running!")

def run_mcp_server():
    """Run the MCP server"""
    print("Starting MCP server...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(mcp.run(transport="sse"))

def run_telegram_bot():
    """Run the Telegram bot"""
    print("Starting Telegram bot...")
    bot = TelegramBot()
    bot.run()

if __name__ == "__main__":
    print("Starting Telegram MCP Server...")
    print(f"Bot Token: {TELEGRAM_BOT_TOKEN[:10]}...")

    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        print("Running in dev mode")
        asyncio.run(mcp.run())
    else:
        print("Running in production mode")
        
        # Start MCP server in a separate thread
        mcp_thread = threading.Thread(target=run_mcp_server)
        mcp_thread.daemon = True  # Thread will be terminated when main program exits
        mcp_thread.start()
        
        # Start Telegram bot in the main thread
        try:
            run_telegram_bot()
        except KeyboardInterrupt:
            print("\nShutting down...")
        except Exception as e:
            print(f"Error occurred: {str(e)}")
            traceback.print_exc()