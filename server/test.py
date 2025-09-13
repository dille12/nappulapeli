import asyncio
import websockets
import json
import base64
import traceback
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game

import threading
class ClientHandler:
    def __init__(self, websocket):
        self.ws = websocket
        self.pending_packets = []

    def open(self):
        return self.ws.open

    async def send(self, packet: str):
        """Add packet to queue and try sending."""
        self.pending_packets.append(packet)
        await self._flush_queue()

    async def _flush_queue(self):
        """Attempt to send all packets in order."""
        while self.pending_packets:
            packet = self.pending_packets[0]
            try:
                t = json.loads(packet).get("type")
                print("Sending", t)
                
                await self.ws.send(packet)
                print("Done")
            except Exception:
                # Stop sending if connection fails
                break
            else:
                # Remove successfully sent packet
                self.pending_packets.pop(0)

    async def on_reconnect(self, new_ws):
        """Call when client reconnects to resend pending packets."""
        self.ws = new_ws
        await self._flush_queue()


def make_handler(app: "Game"):
    app.clients = {}
    app.clientPawns = {}

    async def handler(ws, path):
        client_ip, client_port = ws.remote_address
        print("Client IP:", client_ip, "Port:", client_port)
        reconnection = False
        if client_ip in app.clients:
            print("Client reconnected!")
            reconnection = True
        
        if not reconnection:
            app.clients[client_ip] = ClientHandler(ws)
        else:
            asyncio.run_coroutine_threadsafe(app.clients[client_ip].on_reconnect(ws), app.loop)
            

        print(f"Client connected")

        try:

            if reconnection and client_ip in app.clientPawns:
                pawn = app.clientPawns[client_ip]

                pawn.fullSync()

                #asyncio.run_coroutine_threadsafe(pawn.completeToApp(), app.loop)

            else:
                await ws.send(json.dumps({"msg": "Hello from server"}))

            async for message in ws:
                data = json.loads(message)
                print("Received:", data.get("type"))
                # Example: tell the app about the avatar
                if data.get("type") == "avatar":
                    name = data.get("name")
                    image_bytes = base64.b64decode(data.get("image"))
                    app.add_player(name, image_bytes, ws)  # <-- call your app method

                if data.get("type") == "levelUpChoice":
                    pawn_name = data.get("pawn")
                    item_name = data.get("item")

                    pawn = [pawn for pawn in app.pawnHelpList if pawn.name == pawn_name][0]
                    if pawn:
                        chosen_item = next((i for i in pawn.nextItems if i.name == item_name), None)
                        if chosen_item:
                            pawn.levelUp(chosen_item)

                if data.get("type") == "registerDrink":
                    print(data)
                    pawn_name = data.get("pawnName")
                    pawn = [pawn for pawn in app.pawnHelpList if pawn.name == pawn_name][0]
                    pawn.team.currency += data.get("drinkValue")
                    am = data.get("drinkValue")
                    """Send drink registration response to client"""
                    packet = {
                        "type": "drinkRegistrationResponse",
                        "success": True,
                        "drinkType": data.get("drinkType"),
                        "drinkValue": data.get("drinkValue"),
                        "message": f"{am} drinks earned!"
                    }
                    await ws.send(json.dumps(packet))
                    pawn.team.updateCurrency()


                if data.get("type") == "musicRequest":
                    trackLink = data.get("youtubeLink")
                    print("Music request:", trackLink)
                    threading.Thread(target=app.addToPlaylist, args=(trackLink,), daemon=True).start()


                if data.get("type") == "rerollRequest":
                    
                    pawn_name = data.get("pawnName")

                    pawn = [pawn for pawn in app.pawnHelpList if pawn.name == pawn_name][0]

                    if not pawn.canReroll():
                        p = {
                            "type": "rerollResponse",
                            "success": False,
                            "rerollType": "weapon",
                            "message": "Not enough drinks for reroll!"
                            }
                    else:
                        p = {
                            "type": "rerollResponse",
                            "success": True,
                            "rerollType": "weapon",
                            "message": "Weapon rerolled!"
                            }
                        
                        pawn.rerollWeapon()

                    await ws.send(json.dumps(p))

                    pawn.team.updateCurrency()

                if data.get("type") == "purchaseRequest":
                    item_type = data.get("itemType")
                    item_name = data.get("itemName")
                    pawn_name = data.get("pawnName")
                    

                    pawn = [pawn for pawn in app.pawnHelpList if pawn.name == pawn_name][0]
                    if not pawn.canBuy():
                        p = {
                            "type": "purchaseResponse",
                            "success": False,
                            "itemName": item_name,
                            "message": "Not enough drinks!"
                            }
                        
                    else:
                        pawn.purchaseWeapon(item_name)
                        p = {
                            "type": "purchaseResponse",
                            "success": True,
                            "itemName": item_name,
                            "message": "Weapon purchased successfully!"
                            }
                    
                    await ws.send(json.dumps(p))

                    pawn.team.updateCurrency()

                # Echo back
                for ip in app.clients:
                    c = app.clients[ip]
                    if c and c.open():
                        await c.send(json.dumps({"echo": "echo"}))

        except websockets.exceptions.ConnectionClosed:
            print("Client disconnected")
        finally:
            print("Client removed")
            #app.clients[client_ip] = None

    return handler

