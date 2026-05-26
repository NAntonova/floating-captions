import os
import asyncio
import subprocess
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from soniox import AsyncSonioxClient
from soniox.types import RealtimeSTTConfig

app = FastAPI()

# Global tracker for float window subprocess
float_process = None
active_streams = 0
dashboard_connections = 0

async def monitor_connections():
    global dashboard_connections, active_streams, float_process
    # Wait 15 seconds for the initial connection on startup
    await asyncio.sleep(15)
    while True:
        if dashboard_connections == 0 and active_streams == 0:
            print("No active dashboard tabs or recording streams. Shutting down server...")
            if float_process is not None:
                try:
                    float_process.terminate()
                    float_process.wait(timeout=1)
                except Exception:
                    pass
                float_process = None
            # Terminate FastAPI / Uvicorn server
            os.kill(os.getpid(), 15)
            await asyncio.sleep(2)
            os._exit(0)
        await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(monitor_connections())

@app.websocket("/dashboard_ws")
async def dashboard_ws_endpoint(websocket: WebSocket):
    global dashboard_connections
    await websocket.accept()
    dashboard_connections += 1
    print(f"Dashboard tab connected. Active tabs: {dashboard_connections}")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"Error in dashboard WS: {e}")
    finally:
        dashboard_connections -= 1
        print(f"Dashboard tab disconnected. Active tabs: {dashboard_connections}")

@app.on_event("shutdown")
async def shutdown_event():
    global float_process, caption_websockets
    # Force close all active caption overlays to allow clean uvicorn shutdown
    for ws in list(caption_websockets):
        try:
            await ws.close(code=1001)
        except Exception:
            pass
    if float_process is not None:
        try:
            float_process.terminate()
            float_process.wait(timeout=1)
        except Exception:
            pass
        float_process = None

@app.post("/launch_float")
@app.get("/launch_float")
async def launch_float():
    global float_process
    # Kill any existing floating window process
    if float_process is not None:
        try:
            float_process.terminate()
            float_process.wait(timeout=1)
        except Exception:
            pass
        float_process = None
    
    # Spawn float_window.py in background using virtual environment python
    try:
        python_exe = os.path.join(".venv", "bin", "python")
        if not os.path.exists(python_exe):
            python_exe = "python" # fallback
            
        float_process = subprocess.Popen(
            [python_exe, "float_window.py"]
        )
        return {"status": "success", "pid": float_process.pid}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/close_float")
@app.get("/close_float")
async def close_float():
    global float_process
    if float_process is not None:
        try:
            float_process.terminate()
            float_process.wait(timeout=1)
        except Exception:
            pass
        float_process = None
        return {"status": "success"}
    return {"status": "ignored"}

# Global state for caption overlays
current_final_transcript = ""
caption_websockets = []

@app.websocket("/captions_ws")
async def captions_ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    caption_websockets.append(websocket)
    print(f"Captions window connected. Total connections: {len(caption_websockets)}")
    try:
        # Immediately send current state on connection
        await websocket.send_json({
            "type": "init",
            "final": current_final_transcript
        })
        while True:
            # Keep connection open by listening for any keepalive/pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        print("Captions window disconnected.")
    except Exception as e:
        print(f"Error in captions websocket: {e}")
    finally:
        if websocket in caption_websockets:
            caption_websockets.remove(websocket)

@app.post("/clear")
@app.get("/clear")
async def clear_transcript():
    global current_final_transcript
    current_final_transcript = ""
    # Broadcast clear event to all listening overlay windows
    for ws in list(caption_websockets):
        try:
            await ws.send_json({"type": "clear"})
        except Exception:
            pass
    return {"status": "success"}

# Ensure static folder exists
os.makedirs("static", exist_ok=True)

@app.get("/")
async def get():
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    return HTMLResponse(content="<h1>index.html not found</h1>", status_code=404)

@app.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    global active_streams
    await websocket.accept()
    active_streams += 1
    print(f"Client connected to local WebSocket. Active streams: {active_streams}")

    api_key = os.environ.get("SONIOX_API_KEY")
    if not api_key:
        print("Error: SONIOX_API_KEY not found in environment.")
        await websocket.send_json({"error": "SONIOX_API_KEY environment variable is not set."})
        await websocket.close()
        return

    # Initialize the Soniox Async Client
    client = AsyncSonioxClient(api_key=api_key)

    # Configure Soniox Realtime STT
    config = RealtimeSTTConfig(
        model="stt-rt-v4",
        audio_format="mulaw",
        sample_rate=16000,
        num_channels=1,
        enable_endpoint_detection=True
    )

    try:
        print("Connecting to Soniox Real-time WebSocket API...")
        async with client.realtime.stt.connect(config=config) as session:
            print("Connected to Soniox. Starting stream loops...")

            async def receive_from_client():
                """Receives audio from browser and forwards to Soniox."""
                try:
                    while True:
                        # Receive audio chunk as bytes from the browser
                        data = await websocket.receive_bytes()
                        # Forward to Soniox realtime session
                        await session.send_byte_chunk(data)
                except WebSocketDisconnect:
                    print("Client disconnected. Finalizing Soniox session...")
                    await session.finalize()
                except Exception as e:
                    print(f"Error in client receive loop: {e}")
                    await session.finalize()

            async def send_to_client():
                """Receives transcription events from Soniox and forwards to browser."""
                global current_final_transcript
                try:
                    async for event in session.receive_events():
                        tokens_list = []
                        new_finals = ""
                        current_nonfinals = ""
                        for token in event.tokens:
                            # Skip end-of-stream tags like <fin> or <end>
                            if token.text.strip() in ("<fin>", "<end>"):
                                continue
                            tokens_list.append({
                                "text": token.text,
                                "is_final": token.is_final,
                                "start_ms": token.start_ms,
                                "end_ms": token.end_ms
                            })
                            if token.is_final:
                                new_finals += token.text
                            else:
                                current_nonfinals += token.text
                        
                        # Send events back to dashboard
                        if tokens_list:
                            await websocket.send_json({"tokens": tokens_list})
                            
                            # Update server-side transcript
                            if new_finals:
                                current_final_transcript += new_finals
                                
                            # Broadcast update to all connected captions overlay windows
                            for ws in list(caption_websockets):
                                try:
                                    await ws.send_json({
                                        "type": "update",
                                        "final": current_final_transcript,
                                        "nonfinal": current_nonfinals
                                    })
                                except Exception:
                                    pass
                except Exception as e:
                    print(f"Error in Soniox event loop: {e}")

            # Run both loops concurrently
            await asyncio.gather(receive_from_client(), send_to_client())

    except Exception as e:
        print(f"Soniox connection error: {e}")
        try:
            await websocket.send_json({"error": f"Soniox error: {str(e)}"})
        except:
            pass
    finally:
        active_streams -= 1
        print(f"Closing client WebSocket connection. Active streams: {active_streams}")
        try:
            await websocket.close()
        except:
            pass

# Mount static folder for CSS and JS assets
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, log_level="info")
