from __future__ import annotations

import aiosqlite


class Database:
    def __init__(self, path: str) -> None:
        self._path = path
        self._conn: aiosqlite.Connection | None = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("База данных не подключена")
        return self._conn

    async def connect(self) -> None:
        self._conn = await aiosqlite.connect(self._path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA foreign_keys = ON;")
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def init_schema(self) -> None:
        await self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                event_date TEXT NOT NULL,
                repeat_type TEXT NOT NULL CHECK (repeat_type IN ('daily', 'monthly', 'yearly')),
                remind_before_days INTEGER NOT NULL CHECK (remind_before_days >= 0),
                reminders_per_day INTEGER NOT NULL CHECK (reminders_per_day BETWEEN 1 AND 3),
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS notifications_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                scheduled_for TEXT NOT NULL,
                sent_at TEXT NOT NULL,
                FOREIGN KEY(event_id) REFERENCES events(id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_notifications_unique
                ON notifications_log(event_id, user_id, scheduled_for);

            CREATE INDEX IF NOT EXISTS idx_events_user_id ON events(user_id);
            CREATE INDEX IF NOT EXISTS idx_events_active ON events(is_active);
            """
        )
        await self.conn.commit()

    async def fetchone(self, query: str, params: tuple | dict = ()) -> aiosqlite.Row | None:
        async with self.conn.execute(query, params) as cursor:
            return await cursor.fetchone()

    async def fetchall(self, query: str, params: tuple | dict = ()) -> list[aiosqlite.Row]:
        async with self.conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()
        return rows

    async def execute(self, query: str, params: tuple | dict = ()) -> aiosqlite.Cursor:
        cursor = await self.conn.execute(query, params)
        await self.conn.commit()
        return cursor
