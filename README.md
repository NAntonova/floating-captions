# Floating Captions

A macOS application for real-time speech-to-text transcription powered by Soniox. It uses a FastAPI backend, Google Chrome in App Mode for the dashboard, and a native Cocoa float window (`WKWebView` via PyObjC) to overlay captions on top of any active application.

## Prerequisites

- **macOS** (Required for the Cocoa/PyObjC floating window APIs)
- **Python 3.11+**
- **Google Chrome**
- **Soniox API Key**

## Local Setup

1. **Clone the Repository** and navigate to the project directory:
   ```bash
   cd floating-captions
   ```

2. **Create and Activate a Virtual Environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Soniox API Key**:
   Set your Soniox API key in the environment or update the export line inside the app launcher (`Captions.app/Contents/MacOS/launcher`):
   ```bash
   export SONIOX_API_KEY="your_soniox_api_key_here"
   ```

## Running the Application

You can launch the app by double-clicking **`Captions.app`** in macOS Finder, or run the launcher script directly from your terminal:
```bash
./Captions.app/Contents/MacOS/launcher
```

Ensure the launcher script has executable permissions:
```bash
chmod +x Captions.app/Contents/MacOS/launcher
```

## macOS App Bundle Wrapper

The repository includes a pre-configured macOS Application Bundle (`Captions.app`) to make launching the app convenient. 

If you ever need to recreate or rename this app wrapper from scratch, follow these steps:

1. **Create the Folder Structure**:
   ```bash
   mkdir -p "Captions.app/Contents/MacOS"
   mkdir -p "Captions.app/Contents/Resources"
   ```

2. **Configure launcher**:
   Copy the `launcher` bash script into `Captions.app/Contents/MacOS/launcher` and make it executable:
   ```bash
   chmod +x Captions.app/Contents/MacOS/launcher
   ```

3. **Configure Info.plist**:
   Create `Captions.app/Contents/Info.plist` with the following contents:
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
   <plist version="1.0">
   <dict>
       <key>CFBundleExecutable</key>
       <string>launcher</string>
       <key>CFBundleIdentifier</key>
       <string>com.natalia.captions</string>
       <key>CFBundleName</key>
       <string>Captions</string>
       <key>CFBundlePackageType</key>
       <string>APPL</string>
       <key>CFBundleShortVersionString</key>
       <string>1.0</string>
       <key>LSMinimumSystemVersion</key>
       <string>10.13</string>
       <key>LSUIElement</key>
       <false/>
       <key>CFBundleIconFile</key>
       <string>icon.icns</string>
   </dict>
   </plist>
   ```

4. **Add App Icon**:
   Place your icon file in Apple Icon Image format (`.icns`) at `Captions.app/Contents/Resources/icon.icns`.

## How It Works

- **App Launcher**: Cleans up port `8000`, starts the Python FastAPI server (`server.py`) in the background, and opens Google Chrome in isolated App Mode pointing to `http://localhost:8000`.
- **Audio Streaming**: When you click "Start Listening", the web interface captures microphone audio and streams it to the FastAPI server over a WebSocket connection.
- **Speech-to-Text**: The server streams the audio payload to the Soniox API and receives real-time transcriptions.
- **Cocoa Floating Window**: The server spins up `float_window.py` to draw a native Cocoa window that floats above all apps, displaying the final and non-final transcriptions with a modern warm beige styling.
- **Auto-Shutdown**: The background server monitors active browser connections and closes itself automatically when the app is closed.
