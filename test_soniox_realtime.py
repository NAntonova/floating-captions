import os
import sys
import time
import threading
from soniox import SonioxClient
from soniox.types import RealtimeSTTConfig

def send_audio_chunks(session, filename, chunk_size=8000, delay=0.25):
    """Reads the WAV file and sends it in chunks to simulate real-time streaming."""
    try:
        print(f"Starting audio stream thread for {filename}...")
        with open(filename, "rb") as f:
            # Read header and data
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                session.send_byte_chunk(chunk)
                time.sleep(delay)
        print("Audio file completely sent. Finalizing session...")
        session.finalize()
    except Exception as e:
        print(f"Error in audio streaming thread: {e}", file=sys.stderr)

def main():
    api_key = os.environ.get("SONIOX_API_KEY")
    if not api_key:
        print("Error: SONIOX_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    audio_file = "test.wav"
    if not os.path.exists(audio_file):
        print(f"Error: {audio_file} not found. Please run generate_audio.py first.", file=sys.stderr)
        sys.exit(1)

    print("Initializing SonioxClient...")
    client = SonioxClient()

    # Configure real-time transcription
    # We specify "wav" format since we are streaming a WAV file.
    config = RealtimeSTTConfig(
        model="stt-rt-v4",
        audio_format="wav"
    )

    print("Connecting to Soniox Real-time STT WebSocket...")
    try:
        with client.realtime.stt.connect(config=config) as session:
            # Start streaming the audio file in a background thread
            stream_thread = threading.Thread(
                target=send_audio_chunks,
                args=(session, audio_file),
                daemon=True
            )
            stream_thread.start()

            print("Listening for transcription events...")
            print("-" * 50)
            
            # Print the transcription results as they arrive
            for event in session.receive_events():
                for token in event.tokens:
                    # Non-final tokens represent interim results (gray/provisional)
                    # Final tokens represent confirmed results
                    color = "\033[90m" if not token.is_final else "\033[92m"
                    reset = "\033[0m"
                    print(f"{color}{token.text}{reset}", end=" ", flush=True)
            
            print("\n" + "-" * 50)
            print("Session completed successfully.")

    except Exception as e:
        print(f"\nError in real-time transcription: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
