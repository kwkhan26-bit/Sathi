import os
import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from google import genai
from google.genai import types
from prompts import SYSTEM_PROMPTS

load_dotenv()
app = FastAPI()
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL = "gemini-2.0-flash-exp"

@app.websocket("/ws/{mode}")
async def websocket_endpoint(websocket: WebSocket, mode: str = "default"):
    await websocket.accept()
    print(f"WebSocket connected, mode: {mode}")
    
    system_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["default"])
    
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=system_prompt,
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Leda")
            )
        ),
    )
    
    try:
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            print("Gemini session started")
            
            async def receive_from_client():
                try:
                    while True:
                        try:
                            data = await asyncio.wait_for(
                                websocket.receive_bytes(), 
                                timeout=30.0
                            )
                            await session.send(
                                input=types.LiveClientRealtimeInput(
                                    media_chunks=[types.Blob(data=data, mime_type="audio/pcm")]
                                )
                            )
                        except asyncio.TimeoutError:
                            continue
                except WebSocketDisconnect:
                    print("Client disconnected")
                except Exception as e:
                    print(f"Receive error: {e}")

            async def send_to_client():
                try:
                    while True:
                        async for response in session.receive():
                            if response.data:
                                await websocket.send_bytes(response.data)
                            elif response.text:
                                await websocket.send_text(json.dumps({"text": response.text}))
                except Exception as e:
                    print(f"Send error: {e}")

            await asyncio.gather(receive_from_client(), send_to_client())

    except Exception as e:
        print(f"Session error: {e}")
        try:
            await websocket.send_text(json.dumps({"error": str(e)}))
        except:
            pass
        await websocket.close()

app.mount("/", StaticFiles(directory="static", html=True), name="static")