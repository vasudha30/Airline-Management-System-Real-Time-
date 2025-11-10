import asyncio, os, json
from sqlalchemy import select, update, insert, text
from sqlalchemy.ext.asyncio import AsyncSession
from . import models
from .database import AsyncSessionLocal, engine
from datetime import datetime, timedelta
import redis.asyncio as redis

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)

# helper: publish to redis channel
async def publish_event(event: dict):
    await redis_client.publish("seat_events", json.dumps(event))

# get seat map for a flight
async def list_seats(flight_id: int):
    async with AsyncSessionLocal() as session:
        q = select(models.Seat).where(models.Seat.flight_id==flight_id)
        res = await session.execute(q)
        return res.scalars().all()

# hold seat using Redis key (short-term)
async def try_hold_seat(flight_id: int, seat_code: str, user_id: str, ttl=300):
    key = f"hold:{flight_id}:{seat_code}"
    ok = await redis_client.set(key, user_id, nx=True, ex=ttl)
    if not ok:
        return False
    await publish_event({"type":"seat_held", "flight_id": flight_id, "seat": seat_code, "holder": user_id})
    return True

# finalize booking using database transaction with SELECT FOR UPDATE
async def confirm_booking(flight_id: int, seat_code: str, user_id: str):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # find the seat row FOR UPDATE to lock it
            q = select(models.Seat).where(models.Seat.flight_id==flight_id, models.Seat.seat_code==seat_code).with_for_update()
            res = await session.execute(q)
            seat = res.scalars().first()
            if not seat:
                raise Exception("seat not found")
            # check if seat already booked
            q2 = select(models.Booking).where(models.Booking.seat_id==seat.id, models.Booking.status=="confirmed")
            res2 = await session.execute(q2)
            existing = res2.scalars().first()
            if existing:
                raise Exception("seat already booked")
            # create booking record
            booking = models.Booking(user_id=int(user_id) if str(user_id).isdigit() else None,
                                     flight_id=flight_id, seat_id=seat.id, status="confirmed",
                                     created_at=datetime.utcnow())
            session.add(booking)
            await session.flush()  # get booking.id
            # remove hold key
            await redis_client.delete(f"hold:{flight_id}:{seat_code}")
            await publish_event({"type":"seat_confirmed", "flight_id": flight_id, "seat": seat_code, "booking_id": booking.id})
            return booking.id

# payment idempotency handler
async def process_payment(booking_id: int, amount_cents: int, idempotency_key: str):
    async with AsyncSessionLocal() as session:
        # check idempotency
        q = select(models.Payment).where(models.Payment.idempotency_key==idempotency_key)
        res = await session.execute(q)
        existing = res.scalars().first()
        if existing:
            return existing
        payment = models.Payment(booking_id=booking_id, amount_cents=amount_cents, status="succeeded", idempotency_key=idempotency_key)
        session.add(payment)
        await session.commit()
        return payment

# helper to create initial demo data
async def create_demo_data():
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # create a demo flight
            f = models.Flight(flight_number="F100", origin="DEL", destination="AKL",
                              depart_at=datetime.utcnow() + timedelta(days=1),
                              arrive_at=datetime.utcnow() + timedelta(days=1, hours=12))
            session.add(f)
            await session.flush()
            # create seats 1A..5D
            seats = []
            for r in range(1,6):
                for c in ["A","B","C","D"]:
                    seats.append(models.Seat(flight_id=f.id, seat_code=f"{r}{c}", seat_class="economy"))
            session.add_all(seats)
