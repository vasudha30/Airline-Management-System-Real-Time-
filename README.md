# Airline Management System (Real-time) - Demo

This repository contains a working demo of a real-time Airline Management System (AMS):
- Backend: FastAPI + async SQLAlchemy (Postgres via asyncpg) + Redis for short holds + WebSocket broadcasts
- Frontend: React (Vite) staff dashboard that subscribes to WebSocket events
- Docker compose with services: backend, frontend, postgres, redis

Features:
- Seat holds using Redis (TTL)
- Booking finalize using Postgres transaction with `SELECT ... FOR UPDATE` to avoid double-booking
- Payment simulation endpoint with idempotency using `idempotency_key`
- WebSocket broadcasting of seat events via Redis Pub/Sub
- React staff dashboard showing live seat changes and passenger manifests

Run (local dev):
1. Install Docker & Docker Compose
2. From project root: `docker-compose up --build`
3. Backend: http://localhost:8000
4. Frontend: http://localhost:3000

Notes:
- This is a demo. For production: secure secrets, add migrations, better error handling, TLS, and monitoring.
