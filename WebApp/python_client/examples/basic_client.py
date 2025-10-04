"""
Basic Unity Render Streaming Python client example
"""

import asyncio
import logging
import sys
import os

# Add parent directory to path to import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.client import UnityRenderStreamingClient


async def main():
    """Basic client example"""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting basic Unity Render Streaming client example")
    
    # Create client
    client = UnityRenderStreamingClient(
        server_url="localhost",
        display_video=True,
        save_frames=False,
        save_audio=False
    )
    
    try:
        # Run the client
        await client.run()
        
    except KeyboardInterrupt:
        logger.info("Received interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Error running client: {e}")
    finally:
        logger.info("Client stopped")


if __name__ == "__main__":
    asyncio.run(main())