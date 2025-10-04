"""
Unity Render Streaming Client Example with AI Integration
Demonstrates how to use the Unity client with screenshot functionality for Visual LLM analysis
"""

import asyncio
import base64
from pathlib import Path
import sys
import os

# Add the parent directory to path so we can import the client
sys.path.append(str(Path(__file__).parent.parent))

from unity_client import UnityStreamingClient

class AIIntegratedClient:
    """Example client that integrates with AI services for frame analysis"""
    
    def __init__(self):
        self.frame_analysis_enabled = True
        self.analysis_interval = 30  # Analyze every 30 frames (1 second at 30fps)
        
    async def run_with_ai_analysis(self):
        """Run the Unity client with AI integration"""
        # Create client with screenshot support
        client = UnityStreamingClient(
            server_url="ws://localhost/",
            enable_screenshots=True,
            screenshot_dir="ai_analysis_frames",
            screenshot_format="jpg"
        )
        
        # Set up custom handlers
        client.set_frame_handler(self.analyze_frame)
        client.set_screenshot_handler(self.handle_screenshot)
        
        print("🎮 Starting Unity client with AI analysis...")
        print("🔍 Frame analysis will occur every 30 frames")
        print("📸 Press 'S' to manually capture screenshots for AI analysis")
        print("⌨️  Press 'Q' or Ctrl+C to quit")
        
        await client.run()
        
    def analyze_frame(self, frame, frame_count):
        """
        Custom frame handler for real-time analysis
        
        Args:
            frame: OpenCV BGR frame (numpy array)
            frame_count: Current frame number
            
        Returns:
            frame: Processed frame (can be modified)
        """
        # Perform analysis every 30 frames
        if frame_count % self.analysis_interval == 0 and self.frame_analysis_enabled:
            # Here you could send the frame to an AI service
            print(f"🔍 Analyzing frame {frame_count} for AI insights...")
            
            # Example: Save frame for batch AI processing
            analysis_dir = Path("ai_analysis_frames")
            analysis_dir.mkdir(exist_ok=True)
            
            frame_path = analysis_dir / f"analysis_frame_{frame_count}.jpg"
            cv2.imwrite(str(frame_path), frame)
            
            # Simulate AI analysis (replace with actual AI service call)
            self.simulate_ai_analysis(str(frame_path), frame_count)
            
        return frame  # Return potentially modified frame
        
    def handle_screenshot(self, filepath):
        """
        Custom screenshot handler for AI processing
        
        Args:
            filepath: Path to the saved screenshot
        """
        print(f"📸 Screenshot saved for AI analysis: {filepath}")
        
        # Process screenshot with AI service
        asyncio.create_task(self.process_screenshot_with_ai(filepath))
        
    async def process_screenshot_with_ai(self, filepath):
        """
        Process screenshot with AI service (async)
        
        Args:
            filepath: Path to the screenshot file
        """
        try:
            print(f"🤖 Processing screenshot with AI: {filepath}")
            
            # Example: Convert to base64 for API calls
            base64_image = self.image_to_base64(filepath)
            
            # Here you would call your AI service
            # Example with OpenAI GPT-4V (commented out):
            """
            import openai
            
            response = await openai.ChatCompletion.acreate(
                model="gpt-4-vision-preview",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analyze this Unity game screenshot. What do you see?"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }]
            )
            
            analysis = response.choices[0].message.content
            print(f"🎯 AI Analysis: {analysis}")
            """
            
            # Simulate AI analysis
            await asyncio.sleep(0.1)  # Simulate API call delay
            print(f"🎯 AI Analysis (simulated): Unity scene with interactive elements detected")
            
        except Exception as e:
            print(f"❌ Error processing screenshot with AI: {e}")
            
    def image_to_base64(self, image_path):
        """Convert image to base64 string for AI APIs"""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            print(f"Error converting image to base64: {e}")
            return None
            
    def simulate_ai_analysis(self, frame_path, frame_count):
        """Simulate AI analysis of a frame"""
        # This would be replaced with actual AI service calls
        analyses = [
            "Unity 3D scene with player character detected",
            "User interface elements visible in corner",
            "Environmental objects and lighting detected", 
            "Interactive game elements present",
            "Menu system or HUD components visible"
        ]
        
        analysis = analyses[frame_count % len(analyses)]
        print(f"🎯 AI Analysis (simulated): {analysis}")

async def main():
    """Main entry point for the AI-integrated example"""
    ai_client = AIIntegratedClient()
    
    try:
        await ai_client.run_with_ai_analysis()
    except KeyboardInterrupt:
        print("\n🛑 AI analysis stopped by user")
    except Exception as e:
        print(f"❌ Error in AI client: {e}")

if __name__ == "__main__":
    # Import cv2 here to avoid import issues
    import cv2
    
    print("🚀 Unity Render Streaming AI Integration Example")
    print("=" * 50)
    
    asyncio.run(main())