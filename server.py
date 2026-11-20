import asyncio
import json
import os
import random
import websockets

# Strictly in-RAM state: nothing is ever logged or written to disk.
ROOMS: dict[str, dict] = {}
CONNECTED_CLIENTS: set = set()


def generate_code() -> str:
    while True:
        code = str(random.randint(1000, 9999))
        if code not in ROOMS:
            return code


def sanitize_username(raw_name, fallback: str) -> str:
    text = " ".join(str(raw_name or "").strip().split())
    cleaned = "".join(ch for ch in text if ch.isalnum() or ch in (" ", "-", "_")).strip()
    return cleaned[:20] or fallback


def sanitize_room_name(raw_name) -> str:
    text = " ".join(str(raw_name or "").strip().split())
    cleaned = "".join(ch for ch in text if ch.isalnum() or ch in (" ", "-", "_", ":")).strip()
    return cleaned[:28] or "UNNAMED-FREQ"


def get_public_rooms() -> list[dict]:
    items = []
    for code, info in ROOMS.items():
        if info.get("visibility") == "public":
            items.append({
                "room": code,
                "name": info["name"],
                "peers": len(info["clients"])
            })
    return items


async def broadcast(room_code: str, payload: dict, exclude=None):
    room = ROOMS.get(room_code)
    if not room:
        return
    message = json.dumps(payload)
    dead = []
    for ws in list(room["clients"]):
        if ws == exclude:
            continue
        try:
            await ws.send(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        room["clients"].discard(ws)


async def broadcast_public_list():
    if not CONNECTED_CLIENTS:
        return
    rooms_snapshot = get_public_rooms()
    message = json.dumps({
        "type": "public_rooms",
        "rooms": rooms_snapshot
    })
    dead = []
    for ws in list(CONNECTED_CLIENTS):
        try:
            await ws.send(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        CONNECTED_CLIENTS.discard(ws)


async def handler(websocket):
    current_room = None
    default_callsign = f"UNIT-{random.randint(10, 99)}"
    callsign = default_callsign
    CONNECTED_CLIENTS.add(websocket)

    try:
        await websocket.send(json.dumps({
            "type": "public_rooms",
            "rooms": get_public_rooms()
        }))

        async for raw in websocket:
            data = json.loads(raw)
            action = data.get("action")

            if "username" in data and str(data.get("username") or "").strip():
                callsign = sanitize_username(data.get("username"), callsign)

            if action == "set_username":
                callsign = sanitize_username(data.get("username"), default_callsign)
                await websocket.send(json.dumps({
                    "type": "username_set",
                    "callsign": callsign
                }))

            elif action == "list_public":
                await websocket.send(json.dumps({
                    "type": "public_rooms",
                    "rooms": get_public_rooms()
                }))

            elif action == "create":
                if str(data.get("username") or "").strip():
                    callsign = sanitize_username(data.get("username"), callsign)
                room_name = sanitize_room_name(data.get("name"))
                vis_raw = str(data.get("visibility", "public")).strip().lower()
                visibility = "private" if vis_raw == "private" else "public"
                code = generate_code()
                ROOMS[code] = {
                    "name": room_name,
                    "visibility": visibility,
                    "clients": {websocket}
                }
                current_room = code
                await websocket.send(json.dumps({
                    "type": "joined",
                    "room": code,
                    "name": room_name,
                    "visibility": visibility,
                    "callsign": callsign,
                    "peers": 1
                }))
                if visibility == "public":
                    await broadcast_public_list()

            elif action == "join":
                if str(data.get("username") or "").strip():
                    callsign = sanitize_username(data.get("username"), callsign)
                code = str(data.get("room", "")).strip()
                room = ROOMS.get(code)
                if not room:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "FREQUENCY NOT FOUND"
                    }))
                    continue
                room["clients"].add(websocket)
                current_room = code
                peer_count = len(room["clients"])
                await websocket.send(json.dumps({
                    "type": "joined",
                    "room": code,
                    "name": room["name"],
                    "visibility": room["visibility"],
                    "callsign": callsign,
                    "peers": peer_count
                }))
                await broadcast(code, {
                    "type": "system",
                    "text": f"{callsign} TUNED IN ({peer_count} ONLINE)"
                }, exclude=websocket)
                if room["visibility"] == "public":
                    await broadcast_public_list()

            elif action == "tx_state" and current_room:
                await broadcast(current_room, {
                    "type": "tx_state",
                    "callsign": callsign,
                    "active": bool(data.get("active"))
                }, exclude=websocket)

            elif action == "msg" and current_room:
                text = str(data.get("text", "")).strip()
                if text:
                    await broadcast(current_room, {
                        "type": "msg",
                        "callsign": callsign,
                        "text": text
                    })

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        CONNECTED_CLIENTS.discard(websocket)
        if current_room and current_room in ROOMS:
            room = ROOMS[current_room]
            was_public = room.get("visibility") == "public"
            room["clients"].discard(websocket)
            remaining = len(room["clients"])
            if remaining == 0:
                del ROOMS[current_room]
            else:
                await broadcast(current_room, {
                    "type": "system",
                    "text": f"{callsign} DROPPED ({remaining} ONLINE)"
                })
            if was_public:
                await broadcast_public_list()


async def main():
    port = int(os.environ.get("PORT", 8765))
    async with websockets.serve(handler, "0.0.0.0", port):
        print(f"Walkie Relay active on port {port} (RAM-only)")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())