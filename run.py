# run.py
import asyncio
import signal
import sys
from src.core.mcp_bot import main as bot_main
import uvicorn
from src.rest_server import app as rest_app
from src.services.initialization import initialize_services


class RestServer:
    def __init__(self):
        self.server = None
        self.should_exit = False

    async def start_server(self):
        config = uvicorn.Config(
            rest_app, host="0.0.0.0", port=8000, log_level="info", access_log=False
        )
        self.server = uvicorn.Server(config)

        # Override the should_exit check
        original_should_exit = self.server.should_exit

        def should_exit():
            return self.should_exit or original_should_exit

        self.server.should_exit = should_exit

        await self.server.serve()

    async def shutdown(self):
        if self.server:
            self.should_exit = True
            self.server.should_exit = True
            if hasattr(self.server, "shutdown"):
                await self.server.shutdown()


async def main():
    """Main function with proper shutdown handling"""
    rest_server = RestServer()
    bot_task = None
    rest_task = None

    try:
        # Initialize services once at startup
        print("🔧 Initializing conversation services...")
        await initialize_services()
        print("✅ Conversation services initialized")

        # Create tasks for both services
        bot_task = asyncio.create_task(bot_main())
        rest_task = asyncio.create_task(rest_server.start_server())

        print("🚀 Starting bot and REST server...")

        # Wait for both tasks to complete normally (this should run indefinitely)
        # Only exit if both services stop or on KeyboardInterrupt
        await asyncio.gather(bot_task, rest_task)

    except KeyboardInterrupt:
        print("\n🛑 Shutdown signal received...")
    except Exception as e:
        print(f"❌ Error in main services: {e}")
        # Log the exception details for debugging
        import traceback

        traceback.print_exc()
    finally:
        print("🔄 Shutting down services...")

        # Shutdown REST server
        if rest_server:
            await rest_server.shutdown()

        # Cancel tasks if they're still running
        tasks_to_cancel = []
        if bot_task and not bot_task.done():
            tasks_to_cancel.append(bot_task)
        if rest_task and not rest_task.done():
            tasks_to_cancel.append(rest_task)

        if tasks_to_cancel:
            for task in tasks_to_cancel:
                task.cancel()

            # Wait for cancellation with timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks_to_cancel, return_exceptions=True),
                    timeout=5.0,
                )
            except asyncio.TimeoutError:
                print("⚠️  Some tasks didn't shut down within timeout")

        print("✅ All services stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✅ Shutdown Complete!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
