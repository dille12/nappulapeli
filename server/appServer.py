import asyncio
import websockets
import json
import base64
import traceback
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
import time
import threading
class ClientHandler:
    def __init__(self, websocket):
        self.ws = websocket
        # Store pending packets keyed by a dedup signature so only the most
        # recent packet per key is retained.
        self.pending_packets = {}

    def open(self):
        return True

    async def send(self, packet: str):
        """Add packet to queue and try sending."""
        key = self._packet_key(packet)

        # Replace any existing packet with the same dedup key instead of
        # appending a duplicate. This keeps only the latest version while
        # maintaining the original position for that key.
        self.pending_packets[key] = packet
        await self._flush_queue()

    def _packet_key(self, packet: str):
        """Derive a stable key for deduplication (type + optional identifier)."""
        try:
            payload = json.loads(packet)
        except json.JSONDecodeError:
            # Non-JSON packets are treated as unique by their raw content.
            return ("raw", packet)

        packet_type = payload.get("type")
        # Common identifier field to further disambiguate similar packet types.
        identifier = payload.get("id") or payload.get("identifier")
        return (packet_type, identifier)

    async def _flush_queue(self):
        """Attempt to send all packets in order of their dedup keys."""
        while self.pending_packets:
            # Always send the first pending packet by insertion order. Dicts
            # preserve insertion order, and updates keep the existing position.
            key, packet = next(iter(self.pending_packets.items()))
            try:
                t = None
                try:
                    t = json.loads(packet).get("type")
                except json.JSONDecodeError:
                    # Still send raw packets even if they are not JSON.
                    pass
                #print("Sending", t)
                
                await self.ws.send(packet)
                #print("Done")
            except Exception:
                # Stop sending if connection fails
                break
            else:
                # Remove successfully sent packet
                self.pending_packets.pop(key, None)

    async def on_reconnect(self, new_ws):
        """Call when client reconnects to resend pending packets."""
        self.ws = new_ws
        await self._flush_queue()


def make_handler(app: "Game"):
    app.clients = {}
    app.clientPawns = {}

    async def handler(ws):
        client_ip, client_port = ws.remote_address
        print("Client IP:", client_ip, client_port)
        reconnection = False
        if client_ip in app.clients:
            print("Client reconnected!")
            reconnection = True
        else:
            print(f"Client connected")
        
        if not reconnection:
            app.clients[client_ip] = ClientHandler(ws)
        else:
            asyncio.run_coroutine_threadsafe(app.clients[client_ip].on_reconnect(ws), app.loop)
            

        

        try:

            if reconnection and client_ip in app.clientPawns:
                pawn = app.clientPawns[client_ip]
                pawn.fullSync()

                #asyncio.run_coroutine_threadsafe(pawn.completeToApp(), app.loop)

            else:
                await ws.send(json.dumps({"msg": "Hello from server"}))

            async for message in ws:
                data = json.loads(message)
                #print("Received:", data.get("type"))
                # Example: tell the app about the avatar
                if data.get("type") == "avatar":
                    name = data.get("name")
                    if client_ip not in app.clientPawns:
                        image_bytes = base64.b64decode(data.get("image"))
                        app.add_player(name, image_bytes, ws)  # <-- call your app method
                    else:
                        print("Pawn is already created! ")
                        pawn = app.clientPawns[client_ip]
                        pawn.fullSync()

                if data.get("type") == "levelUpChoice":
                    pawn_name = data.get("pawn")
                    item_name = data.get("item")

                    pawn = [pawn for pawn in app.getActualPawns() if pawn.name == pawn_name][0]
                    if pawn:
                        chosen_item = next((i for i in pawn.nextItems if i.name == item_name), None)
                        if chosen_item:
                            pawn.levelUp(chosen_item)

                if data.get("type") == "registerDrink":
                    print(data)
                    pawn_name = data.get("pawnName")
                    pawn = [pawn for pawn in app.getActualPawns() if pawn.name == pawn_name][0]

                    am = data.get("drinkValue")
                    pawn.team.currency += am
                    pawn.stats["amountDrank"] += am
                    
                    drinkType = data.get("drinkType")
                    if drinkType in pawn.drinks:
                        pawn.drinks[drinkType] += 1
                    else:
                        pawn.drinks[drinkType] = 1

                    

                    if pawn.drinkTimer > 0:
                        if app.ANTICHEAT:
                            app.bust(pawn, time.time() - pawn.lastDrinks[-1][0])

                    pawn.lastDrinks.append([time.time(), drinkType])
                    print(pawn.lastDrinks)
                    
                    pawn.drinkTimer = 60
                    
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

                    pawn = [pawn for pawn in app.getActualPawns() if pawn.name == pawn_name][0]

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
                    item_price = data.get("price")
                    
                    
                    pawn = [pawn for pawn in app.getActualPawns() if pawn.name == pawn_name][0]
                    if not pawn.canBuy(item_price):
                        p = {
                            "type": "purchaseResponse",
                            "success": False,
                            "itemName": item_name,
                            "message": "Not enough drinks!"
                            }
                        
                    else:
                        if item_type == "weapon":
                            pawn.purchaseWeapon(item_name, item_price)
                        else:
                            pawn.purchaseItem(item_name, item_price)
                        p = {
                            "type": "purchaseResponse",
                            "success": True,
                            "itemName": item_name,
                            "message": "Weapon purchased successfully!"
                            }
                        pawn.shopSuccessPackets.append(p)
                        pawn.updateEquipment()
                    
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
