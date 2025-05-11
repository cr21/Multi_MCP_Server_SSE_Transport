import asyncio
import yaml
from core.loop import AgentLoop
from core.session import MultiMCP
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os
from dotenv import load_dotenv

def log(stage: str, msg: str):
    """Simple timestamped console logger."""
    import datetime
    now = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] [{stage}] {msg}")

class TelegramAgent:
    def __init__(self):
        # Load MCP server configs
        with open("config/profiles.yaml", "r") as f:
            profile = yaml.safe_load(f)
            self.mcp_servers = profile.get("mcp_servers", [])
        
        # Initialize MultiMCP
        self.multi_mcp = MultiMCP(server_configs=self.mcp_servers)
        
        # Load Telegram token
        load_dotenv()
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")
            
        # Initialize Telegram application
        self.app = Application.builder().token(self.token).build()
        
    async def initialize(self):
        """Initialize MCP connections"""
        await self.multi_mcp.initialize()
        
        # Add Telegram handlers
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        print("🤖 Telegram Agent Ready!")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        await update.message.reply_text(
            "👋 Hello! I'm your AI assistant powered by multiple expert systems.\n"
            "I can help you with:\n"
            "- Web searches and current information\n"
            "- Reading and analyzing documents\n"
            "- Performing calculations\n"
            "- Answering questions using my knowledge\n\n"
            "Just ask me anything!"
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages"""
        try:
            # Send typing indicator
            await update.message.chat.send_action(action="typing")
            
            # Get user input
            user_input = update.message.text
            
            log("telegram", f"Received message: {user_input}")
            
            # Create agent loop
            agent = AgentLoop(
                user_input=user_input,
                dispatcher=self.multi_mcp
            )
            
            # Run agent and get response
            final_response = await agent.run()
            clean_response = final_response.replace("FINAL_ANSWER:", "").strip()
            
            # Send response in chunks if needed
            if len(clean_response) > 4096:
                for i in range(0, len(clean_response), 4096):
                    chunk = clean_response[i:i + 4096]
                    await update.message.reply_text(chunk)
            else:
                await update.message.reply_text(clean_response)
                
        except Exception as e:
            log("error", f"Failed to process message: {e}")
            await update.message.reply_text(
                f"Sorry, I encountered an error while processing your request: {str(e)}"
            )

    async def run(self):
        """Run the Telegram bot"""
        try:
            # Initialize MCP connections first
            await self.initialize()
            
            # Start the application
            await self.app.initialize()
            await self.app.start()
            
            # Start polling in non-blocking mode
            await self.app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
            
            # Keep the application running
            print("Bot is running. Press Ctrl+C to stop.")
            while True:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            print("\nShutting down...")
        except Exception as e:
            print(f"Error: {e}")
            raise
        finally:
            try:
                # Stop polling first
                if self.app.updater.running:
                    await self.app.updater.stop()
                
                # Then stop the application
                if self.app.running:
                    await self.app.stop()
                    
            except Exception as e:
                print(f"Error during shutdown: {e}")

def main():
    """Main entry point"""
    agent = TelegramAgent()
    
    try:
        # Create and run a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(agent.run())
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    except Exception as e:
        log("fatal", f"Agent failed: {e}")
        raise
    finally:
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()

if __name__ == "__main__":
    main()
