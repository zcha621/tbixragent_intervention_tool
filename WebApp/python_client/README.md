# Unity Render Streaming Python Client

A high-performance Python client for receiving real-time video streams from Unity Render Streaming servers via WebRTC. Features H.264 hardware acceleration, interactive controls, and screenshot capture for AI/ML integration.

## 🚀 Features

- **Real-time Video Streaming**: Receive HD video streams (1280x720 @ 30fps) from Unity
- **H.264 Hardware Acceleration**: Optimized codec support for smooth playback
- **Interactive Controls**: Press `Q` to quit, `S` to save screenshots
- **Screenshot Capture**: Save frames as JPG/PNG for Visual LLM analysis
- **WebRTC & WebSocket**: Full WebRTC peer connection with WebSocket signaling
- **Cross-platform**: Works on Windows, macOS, and Linux
- **Developer-friendly**: Clean API for programmatic use

## 📋 Requirements

- **Python 3.8+** (recommended 3.9+)
- **Unity Render Streaming Server** running on target device
- **OpenCV** for video display and processing

## 🛠️ Installation

1. **Clone or download** this repository
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Dependencies
```
aiortc>=1.6.0          # WebRTC implementation
websockets>=11.0.0     # WebSocket client  
opencv-python>=4.8.0   # Video display and processing
numpy>=1.21.0          # Numerical operations
Pillow>=9.0.0          # Image processing for screenshots
```

## 🎮 Quick Start

### Basic Usage
```bash
python unity_client.py
```

### Connect to Custom Server
```bash
python unity_client.py --server ws://192.168.1.100:8080
```

### With Screenshot Support
```bash
python unity_client.py --screenshots
```

### Full Command Line Options
```bash
python unity_client.py [OPTIONS]

Options:
  --server URL          WebSocket server URL (default: ws://localhost:8080)
  --connection-id ID    Specific connection ID to use
  --screenshots         Enable screenshot saving (S key to capture)
  --screenshot-dir DIR  Directory to save screenshots (default: screenshots/)
  --screenshot-format   Image format: jpg, png, or both (default: jpg)
  --verbose             Enable detailed logging
  --help               Show this help message
```

## ⌨️ Interactive Controls

While the video stream is running:

- **`Q` key or `Ctrl+C`**: Quit and stop streaming
- **`S` key**: Save screenshot (when --screenshots enabled)
- **`ESC` key**: Close video window
- **Mouse clicks**: Can be captured for Unity interaction (if implemented)

## 📸 Screenshot Features

When enabled with `--screenshots`, you can:

1. **Capture frames in real-time** by pressing `S`
2. **Save in multiple formats**: JPG (fast), PNG (lossless), or both
3. **Organized storage**: Files saved with timestamps in `screenshots/` directory
4. **AI/ML ready**: Perfect for feeding frames to Visual LLMs like GPT-4V, Claude, etc.

### Screenshot Example
```bash
# Enable screenshots with PNG format
python unity_client.py --screenshots --screenshot-format png

# Custom screenshot directory
python unity_client.py --screenshots --screenshot-dir "./captures"
```

Screenshots are saved as:
```
screenshots/
├── unity_frame_2025-10-05_14-30-45.jpg
├── unity_frame_2025-10-05_14-31-02.jpg
└── unity_frame_2025-10-05_14-31-15.png
```

## 🔧 Programmatic Usage

```python
import asyncio
from unity_client import UnityStreamingClient

async def main():
    # Create client with screenshot support
    client = UnityStreamingClient(
        server_url="ws://localhost:8080",
        enable_screenshots=True,
        screenshot_format="jpg"
    )
    
    # Custom frame handler
    def on_frame_received(frame, frame_count):
        print(f"Frame {frame_count}: {frame.shape}")
        # Process frame for AI/ML here
        return frame
    
    # Custom screenshot handler  
    def on_screenshot_saved(filepath):
        print(f"Screenshot saved: {filepath}")
        # Send to Visual LLM API here
    
    client.set_frame_handler(on_frame_received)
    client.set_screenshot_handler(on_screenshot_saved)
    
    # Run the client
    await client.run()

if __name__ == "__main__":
    asyncio.run(main())
```

## 🏗️ Architecture

```
unity_client.py          # Main application entry point
├── src/
│   ├── __init__.py      # Package initialization
│   ├── signaling.py     # WebSocket signaling with Unity
│   ├── webrtc_peer.py   # WebRTC peer connection management
│   ├── media_handlers.py # Video/audio stream processing
│   └── client.py        # Core client logic
└── examples/
    ├── basic_client.py      # Simple streaming example
    ├── headless_client.py   # No-display streaming
    └── custom_handlers.py   # Advanced frame processing
```

### Component Overview

- **`signaling.py`**: Handles WebSocket communication with Unity server
- **`webrtc_peer.py`**: Manages WebRTC peer connections and ICE negotiation  
- **`media_handlers.py`**: Processes video frames, handles display and screenshots
- **`client.py`**: Orchestrates all components and provides the main API

## 🔗 Unity Render Streaming Setup

Ensure your Unity project has:

1. **Unity Render Streaming package** installed
2. **WebRTC signaling server** running (usually on port 8080)
3. **Compatible video codec**: H.264 recommended
4. **Network accessibility**: Firewall allows WebSocket connections

### Unity Side Configuration
```csharp
// In your Unity script
var renderStreaming = FindObjectOfType<RenderStreaming>();
renderStreaming.runOnStart = true;  // Auto-start streaming
```

## 🚨 Troubleshooting

### Connection Issues
- ✅ **Check Unity server**: Ensure Render Streaming is active
- ✅ **Verify URL**: Default is `ws://localhost:8080`
- ✅ **Firewall**: Allow port 8080 (or your custom port)
- ✅ **Network**: Test connectivity with `ping` or `telnet`

### Video Issues  
- ✅ **Codec support**: H.264 should work on most systems
- ✅ **OpenCV installation**: Try `cv2.__version__` in Python
- ✅ **Graphics drivers**: Update for hardware acceleration
- ✅ **System resources**: Close other video applications

### Screenshot Issues
- ✅ **Directory permissions**: Ensure write access to screenshot folder
- ✅ **Disk space**: Check available storage
- ✅ **Pillow installation**: Required for PNG format

### Performance Tips
- 🔥 **Use H.264**: Better performance than VP8/VP9
- 🔥 **Close unused apps**: Free up CPU/GPU resources
- 🔥 **Wired connection**: Ethernet preferred over WiFi
- 🔥 **Updated drivers**: Latest graphics and network drivers

## 💡 AI/ML Integration Examples

### Send Screenshots to GPT-4V
```python
import base64
import openai

def analyze_unity_screenshot(screenshot_path):
    with open(screenshot_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    
    response = openai.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[{
            "role": "user", 
            "content": [
                {"type": "text", "text": "Analyze this Unity game screenshot:"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]
        }]
    )
    return response.choices[0].message.content
```

### Real-time Frame Analysis
```python
async def process_frames_with_ai(client):
    frame_buffer = []
    
    def frame_handler(frame, count):
        frame_buffer.append(frame)
        
        # Process every 30th frame (1 per second at 30fps)
        if count % 30 == 0:
            # Save frame and analyze
            screenshot_path = f"temp_frame_{count}.jpg"
            cv2.imwrite(screenshot_path, frame)
            
            # Send to AI service
            analysis = analyze_unity_screenshot(screenshot_path)
            print(f"AI Analysis: {analysis}")
        
        return frame
    
    client.set_frame_handler(frame_handler)
    await client.run()
```

## 📊 Performance Metrics

Typical performance on modern hardware:
- **Latency**: 50-150ms end-to-end
- **Frame Rate**: 30fps (1280x720)
- **CPU Usage**: 10-20% (H.264 hardware decoding)
- **Memory**: ~100MB RAM usage
- **Network**: ~2-8 Mbps depending on quality

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is provided as-is for educational and development purposes.

---

**Built with ❤️ for Unity developers and AI/ML enthusiasts**