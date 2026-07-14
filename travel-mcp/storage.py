import aiosqlite
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "trips.db"

_CREATE_TRIPS = """
CREATE TABLE IF NOT EXISTS trips (
    id          TEXT PRIMARY KEY,
    destination TEXT NOT NULL,
    origin      TEXT NOT NULL,
    start_date  TEXT NOT NULL,
    end_date    TEXT NOT NULL,
    travelers   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL,
    plan_text   TEXT NOT NULL
)
"""

_CREATE_ACTIVITIES = """
CREATE TABLE IF NOT EXISTS activities (
    id       TEXT PRIMARY KEY,
    trip_id  TEXT NOT NULL,
    day      INTEGER NOT NULL,
    name     TEXT NOT NULL,
    time     TEXT,
    notes    TEXT,
    FOREIGN KEY (trip_id) REFERENCES trips(id)
)
"""

_MIGRATE_TRIPS_ORIGIN = """
ALTER TABLE trips ADD COLUMN origin TEXT NOT NULL DEFAULT ''
"""

_MIGRATE_ACTIVITIES_NOTES = """
ALTER TABLE trips ADD COLUMN notes TEXT
"""


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(_CREATE_TRIPS)
        await db.execute(_CREATE_ACTIVITIES)
        # Add columns that may be missing from an older schema
        for sql in (_MIGRATE_TRIPS_ORIGIN, _MIGRATE_ACTIVITIES_NOTES):
            try:
                await db.execute(sql)
            except Exception:
                pass  # column already exists
        await db.commit()


async def get_all_trips() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, destination, origin, start_date, end_date, travelers, created_at "
            "FROM trips ORDER BY created_at DESC"
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def load_trip(trip_id: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM trips WHERE id = ?", (trip_id,)) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None


async def store_trip(
    trip_id: str,
    destination: str,
    origin: str,
    start_date: str,
    end_date: str,
    travelers: int,
    plan_text: str,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO trips (id, destination, origin, start_date, end_date, travelers, created_at, plan_text) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (trip_id, destination, origin, start_date, end_date, travelers, now, plan_text),
        )
        await db.commit()


async def get_activities(trip_id: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM activities WHERE trip_id = ? ORDER BY day, time",
            (trip_id,),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def add_activity_row(
    activity_id: str,
    trip_id: str,
    day: int,
    name: str,
    time: str | None,
    notes: str | None,
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO activities (id, trip_id, day, name, time, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (activity_id, trip_id, day, name, time, notes),
        )
        await db.commit()


async def update_activity_row(
    activity_id: str,
    name: str | None,
    time: str | None,
    notes: str | None,
) -> bool:
    fields, values = [], []
    if name is not None:
        fields.append("name = ?")
        values.append(name)
    if time is not None:
        fields.append("time = ?")
        values.append(time)
    if notes is not None:
        fields.append("notes = ?")
        values.append(notes)
    if not fields:
        return True  # nothing to update
    values.append(activity_id)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            f"UPDATE activities SET {', '.join(fields)} WHERE id = ?", values
        ) as cur:
            updated = cur.rowcount > 0
        await db.commit()
    return updated


async def remove_activity_row(activity_id: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "DELETE FROM activities WHERE id = ?", (activity_id,)
        ) as cur:
            deleted = cur.rowcount > 0
        await db.commit()
    return deleted
