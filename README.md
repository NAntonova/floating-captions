# Floating Captions

Real-time speech-to-text overlay on macOS powered by Soniox.

## Prerequisites

- macOS
- Python 3.11+
- Google Chrome
- Soniox API Key

## Setup & Run

1. Clone the repository and navigate to the project directory.
2. Set up the Python environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Configure your Soniox API Key in `Captions.app/Contents/MacOS/launcher`:
   ```bash
   export SONIOX_API_KEY="your_soniox_api_key_here"
   ```
4. Start the application:
   ```bash
   ./Captions.app/Contents/MacOS/launcher
   ```
   *(Or double-click `Captions.app` in Finder)*

## Rebuilding the App Bundle

If you ever need to recreate or reset the `Captions.app` bundle:
```bash
./build_app.sh
```
