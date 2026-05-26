import os
import sys
from soniox import SonioxClient

def main():
    # Verify API key is in the environment
    api_key = os.environ.get("SONIOX_API_KEY")
    if not api_key:
        print("Error: SONIOX_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    print("Initializing SonioxClient...")
    client = SonioxClient()

    audio_file = "test.wav"
    if not os.path.exists(audio_file):
        print(f"Error: {audio_file} not found. Please run generate_audio.py first.", file=sys.stderr)
        sys.exit(1)

    print(f"Transcribing {audio_file} (this may take a few seconds)...")
    try:
        # Transcribe and wait for tokens
        # The model defaults to 'stt-async-v4'
        result = client.stt.transcribe_and_wait_with_tokens(
            file=audio_file,
            filename=audio_file
        )
        
        print("\nTranscription Result:")
        print(f"ID: {result.id}")
        print(f"Text: '{result.text}'")
        print("\nTokens detail:")
        for i, token in enumerate(result.tokens[:10]):
            print(f"  [{i}] '{token.text}' (start: {token.start_ms}ms, end: {token.end_ms}ms, confidence: {token.confidence})")
        if len(result.tokens) > 10:
            print(f"  ... and {len(result.tokens) - 10} more tokens.")
            
        print("\nSuccess! Connection to Soniox verified.")

    except Exception as e:
        print(f"\nError transcribing file: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
