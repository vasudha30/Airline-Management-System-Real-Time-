from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SeatOut(BaseModel):
    id: int
    flight_id: int
    seat_code: str
    seat_class: Optional[str]

    class Config:
        orm_mode = True

class HoldResponse(BaseModel):
    result: str
    expires_in: int

class BookingConfirmResponse(BaseModel):
    result: str
    booking_id: str

class PaymentIn(BaseModel):
    booking_id: int
    amount_cents: int
    idempotency_key: str
