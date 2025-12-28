import asyncio
import websockets
import json
import base64
from pathlib import Path
import random, os

SERVER_URI = "ws://localhost:8765"
AVATAR_NAME = "TestPawn"

IMAGE_PATH = Path("backUpImages") / random.choice(os.listdir("backUpImages"))

async def main():
    image_bytes = IMAGE_PATH.read_bytes()
    image_b64 = base64.b64encode(image_bytes).decode("ascii")

    packet = json.dumps({
        "type": "avatar",
        "name": AVATAR_NAME,
        "image": image_b64
    })

    async with websockets.connect(SERVER_URI) as ws:
        for i in range(10):
            await ws.send(packet)
            print(f"Sent avatar packet {i+1}/10")
            await asyncio.sleep(0.05)  # small spacing to preserve ordering

        # optional: read a few responses without blocking forever
        try:
            for _ in range(10):
                msg = await asyncio.wait_for(ws.recv(), timeout=0.2)
                print("Received:", msg)
        except asyncio.TimeoutError:
            pass

if __name__ == "__main__":
    asyncio.run(main())
