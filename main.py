import os, asyncio, json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse
from . import models
from .database import engine, AsyncSessionLocal
from .crud import try_hold_seat, confirm_booking, process_payment, publish_event, create_demo_data, redis_client
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .models import Base
from pydantic import BaseModel
from .schemas import PaymentIn
import uvicorn

app = FastAPI(title="Airline AMS Demo")

# Simple websocket manager
class WSManager:
    def __init__(self):
        self.connections = set()
    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.add(ws)
    def disconnect(self, ws: WebSocket):
        self.connections.discard(ws)
    async def broadcast(self, message: dict):
        dead = []
        for ws in list(self.connections):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for d in dead:
            self.disconnect(d)

ws_manager = WSManager()

# Startup: create tables and demo data, start redis subscriber bridge
@app.on_event("startup")
async def startup():
    # create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # demo data
    await create_demo_data()
    # start pubsub listener
    asyncio.create_task(_redis_listener())

async def _redis_listener():
    pub = redis_client.pubsub()
    await pub.subscribe("seat_events")
    async for msg in pub.listen():
        if msg is None:
            continue
        if msg.get("type") != "message":
            continue
        try:
            data = json.loads(msg["data"])
        except:
            continue
        # forward to connected websockets
        await ws_manager.broadcast(data)

@app.get("/health")
async def health():
    return {"status":"ok"}

@app.get("/flights/{flight_id}/seats")
async def get_seats(flight_id: int):
    async with AsyncSessionLocal() as session:
        q = select(models.Seat).where(models.Seat.flight_id==flight_id)
        res = await session.execute(q)
        seats = res.scalars().all()
        return [{"id":s.id,"seat_code":s.seat_code,"seat_class":s.seat_class} for s in seats]

@app.post("/flights/{flight_id}/seats/{seat_code}/hold")
async def hold_seat(flight_id: int, seat_code: str, request: Request):
    data = await request.json()
    user_id = data.get("user_id")
    ok = await try_hold_seat(flight_id, seat_code, user_id)
    if not ok:
        raise HTTPException(status_code=409, detail="seat already held/booked")
    return {"result":"held","expires_in":300}

@app.post("/flights/{flight_id}/seats/{seat_code}/confirm")
async def confirm_seat(flight_id: int, seat_code: str, request: Request):
    data = await request.json()
    user_id = data.get("user_id")
    try:
        booking_id = await confirm_booking(flight_id, seat_code, user_id)
    except Exception as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"result":"booked","booking_id": booking_id}

# Payment simulation endpoint (idempotent)
@app.post("/payments/simulate")
async def payment_simulate(payment: PaymentIn):
    # Process the payment with idempotency
    p = await process_payment(payment.booking_id, payment.amount_cents, payment.idempotency_key)
    # simulate webhook to booking service (we simply publish event)
    await publish_event({"type":"payment_succeeded","booking_id": payment.booking_id, "payment_id": p.id})
    return {"status":"ok", "payment_id": p.id}

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            # simple echo for now
            await ws.send_text(f"ACK:{data}")
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)

if __name__ == '__main__':
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
