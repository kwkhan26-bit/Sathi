import os
import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from google import genai
from google.genai import types
from prompts import SYSTEM_PROMPTS

load_dotenv()

app = FastAPI()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL = "gemini-2.0-flash-live-001"

@app.websocket("/ws/{mode}")
async def websocket_endpoint(websocket: WebSocket, mode: str = "default"):
    await websocket.accept()
    
    system_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["default"])
    
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=system_prompt,
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Leda")
            )
        )
    )
    
    try:
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            async def receive_from_client():
                while True:
                    try:
                        data = await websocket.receive_bytes()
                        await session.send(
                            input=types.LiveClientRealtimeInput(
                                media_chunks=[types.Blob(data=data, mime_type="audio/pcm")]
                            )
                        )
                    except WebSocketDisconnect:
                        break

            async def send_to_client():
                while True:
                    async for response in session.receive():
                        if response.data:
                            await websocket.send_bytes(response.data)
                        elif response.text:
                            await websocket.send_text(json.dumps({"text": response.text}))

            await asyncio.gather(receive_from_client(), send_to_client())

    except Exception as e:
        await websocket.send_text(json.dumps({"error": str(e)}))
        await websocket.close()

app.mount("/", StaticFiles(directory="static", html=True), name="static")