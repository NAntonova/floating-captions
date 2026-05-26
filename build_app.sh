#!/bin/bash

# Exit immediately if any command fails
set -e

echo "=== Building Captions.app ==="

# Define directories
APP_DIR="Captions.app"
CONTENTS_DIR="$APP_DIR/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"

# 1. Recreate the App Bundle directory structure
echo "Creating directory structure..."
rm -rf "$APP_DIR"
mkdir -p "$MACOS_DIR"
mkdir -p "$RESOURCES_DIR"

# 2. Generate the Info.plist
echo "Generating Info.plist..."
cat << 'EOF' > "$CONTENTS_DIR/Info.plist"
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
EOF

# 3. Generate the launcher script
echo "Generating launcher script..."
cat << 'EOF' > "$MACOS_DIR/launcher"
#!/bin/bash

# FaceTime Transcribe App Launcher

# Define working directories dynamically relative to the script location
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
LOG_FILE="/tmp/soniox_app_server.log"
CHROME_PROFILE="$PROJECT_DIR/chrome-profile"

# Ensure we are in the project directory
cd "$PROJECT_DIR" || exit 1

# Export the Soniox API key
export SONIOX_API_KEY="YOUR_SONIOX_API_KEY"

# Cleanup any previous server instances listening on port 8000
echo "Cleaning up port 8000..." >> "$LOG_FILE"
lsof -ti :8000 | xargs kill -9 2>/dev/null

# Start the Python FastAPI server in the background
echo "Starting Python backend server..." >> "$LOG_FILE"
./.venv/bin/python server.py >> "$LOG_FILE" 2>&1 &

# Wait for the server to spin up and bind to the port
echo "Waiting for server to start..." >> "$LOG_FILE"
sleep 2

# Launch Google Chrome in App Mode (chromeless popup window)
# We use an isolated user profile so it runs independently
echo "Launching Google Chrome in App Mode..." >> "$LOG_FILE"
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
    --app="http://localhost:8000" \
    --user-data-dir="$CHROME_PROFILE" &

# Exit immediately. The server will automatically shut down after 60 seconds
# if no connection is established, or 15 seconds after the WebSocket closes.
echo "Launcher script completed. Exiting..." >> "$LOG_FILE"
exit 0
EOF

# Make launcher executable
chmod +x "$MACOS_DIR/launcher"

# 4. Copy the application icon
if [ -f "assets/icon.icns" ]; then
    echo "Copying application icon..."
    cp "assets/icon.icns" "$RESOURCES_DIR/icon.icns"
else
    echo "Warning: assets/icon.icns not found, App Bundle will not have custom icon."
fi

echo "=== Build Complete: Captions.app has been created! ==="
