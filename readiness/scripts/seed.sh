#!/usr/bin/env bash
# Database Seed Script
set -e

echo "Seeding Readiness Assistant database..."
docker compose exec backend python -c "
import asyncio
from app.security import init_db
asyncio.run(init_db())
print('Database successfully seeded with demo users and assets.')
"
