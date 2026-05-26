import wave
import math
import struct

def generate_test_wav(filename="test.wav", duration=5.0, sample_rate=16000, frequency=440.0):
    # Create a 16kHz Mono 16-bit PCM WAV file
    num_samples = int(duration * sample_rate)
    
    with wave.open(filename, "w") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)   # 16-bit (2 bytes)
        wav_file.setframerate(sample_rate)
        
        amplitude = 32767 * 0.5  # 50% max volume for 16-bit signed int
        
        for i in range(num_samples):
            t = float(i) / sample_rate
            value = int(amplitude * math.sin(2.0 * math.pi * frequency * t))
            data = struct.pack("<h", value)
            wav_file.writeframesraw(data)

    print(f"Generated {filename}: {duration}s, {sample_rate}Hz, Mono, 16-bit PCM")

if __name__ == "__main__":
    generate_test_wav()
