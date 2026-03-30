from __future__ import annotations

from datetime import datetime, timezone
import logging

import aiosqlite

from app.database.db import Database
from app.database.models import Event, ReminderEvent, RepeatType, User


logger = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class UserRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        row = await self._db.fetchone(
            "SELECT id, telegram_id, created_at FROM users WHERE telegram_id = ?",
            (telegram_id,),
        )
        if row is None:
            return None
        return User.from_row(row)

    async def get_or_create(self, telegram_id: int) -> User:
        existing = await self.get_by_telegram_id(telegram_id)
        if existing is not None:
            return existing

        created_at = _utc_now_iso()
        try:
            cursor = await self._db.execute(
                "INSERT INTO users (telegram_id, created_at) VALUES (?, ?)",
                (telegram_id, created_at),
            )
            user_id = cursor.lastrowid
        except aiosqlite.IntegrityError:
            existing_again = await self.get_by_telegram_id(telegram_id)
            if existing_again is None:
                raise
            return existing_again

        row = await self._db.fetchone(
            "SELECT id, telegram_id, created_at FROM users WHERE id = ?",
            (user_id,),
        )
        if row is None:
            raise RuntimeError("Не удалось прочитать созданного пользователя")
        return User.from_row(row)


class EventRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def create(
        self,
        user_id: int,
        title: str,
        event_date_iso: str,
        repeat_type: RepeatType,
        remind_before_days: int,
        reminders_per_day: int,
    ) -> int:
        now = _utc_now_iso()
        cursor = await self._db.execute(
            """
            INSERT INTO events (
                user_id,
                title,
                event_date,
                repeat_type,
                remind_before_days,
                reminders_per_day,
                is_active,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                user_id,
                title,
                event_date_iso,
                repeat_type.value,
                remind_before_days,
                reminders_per_day,
                now,
                now,
            ),
        )
        return int(cursor.lastrowid)

    async def list_by_telegram_id(self, telegram_id: int) -> list[Event]:
        rows = await self._db.fetchall(
            """
            SELECT e.id, e.user_id, e.title, e.event_date, e.repeat_type,
                   e.remind_before_days, e.reminders_per_day,
                   e.is_active, e.created_at, e.updated_at
            FROM events e
            JOIN users u ON u.id = e.user_id
            WHERE u.telegram_id = ? AND e.is_active = 1
            ORDER BY e.event_date ASC, e.id DESC
            """,
            (telegram_id,),
        )
        return [Event.from_row(row) for row in rows]

    async def get_by_id_for_telegram_user(self, event_id: int, telegram_id: int) -> Event | None:
        row = await self._db.fetchone(
            """
            SELECT e.id, e.user_id, e.title, e.event_date, e.repeat_type,
                   e.remind_before_days, e.reminders_per_day,
                   e.is_active, e.created_at, e.updated_at
            FROM events e
            JOIN users u ON u.id = e.user_id
            WHERE e.id = ? AND u.telegram_id = ? AND e.is_active = 1
            """,
            (event_id, telegram_id),
        )
        if row is None:
            return None
        return Event.from_row(row)

    async def update_field(self, event_id: int, user_id: int, field: str, value: str | int) -> bool:
        allowed_fields = {"title", "event_date", "repeat_type", "remind_before_days", "reminders_per_day"}
        if field not in allowed_fields:
            raise ValueError(f"Недопустимое поле для обновления: {field}")

        query = f"UPDATE events SET {field} = ?, updated_at = ? WHERE id = ? AND user_id = ? AND is_active = 1"
        cursor = await self._db.execute(query, (value, _utc_now_iso(), event_id, user_id))
        return cursor.rowcount > 0

    async def soft_delete(self, event_id: int, user_id: int) -> bool:
        cursor = await self._db.execute(
            """
            UPDATE events
            SET is_active = 0, updated_at = ?
            WHERE id = ? AND user_id = ? AND is_active = 1
            """,
            (_utc_now_iso(), event_id, user_id),
        )
        return cursor.rowcount > 0

    async def list_active_for_reminders(self) -> list[ReminderEvent]:
        rows = await self._db.fetchall(
            """
            SELECT e.id, e.user_id, e.title, e.event_date, e.repeat_type,
                   e.remind_before_days, e.reminders_per_day,
                   e.is_active, e.created_at, e.updated_at,
                   u.telegram_id
            FROM events e
            JOIN users u ON u.id = e.user_id
            WHERE e.is_active = 1
            """
        )
        return [ReminderEvent.from_row(row) for row in rows]


class NotificationLogRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def exists(self, event_id: int, user_id: int, scheduled_for_iso: str) -> bool:
        row = await self._db.fetchone(
            """
            SELECT id
            FROM notifications_log
            WHERE event_id = ? AND user_id = ? AND scheduled_for = ?
            LIMIT 1
            """,
            (event_id, user_id, scheduled_for_iso),
        )
        return row is not None

    async def add(self, event_id: int, user_id: int, scheduled_for_iso: str) -> bool:
        sent_at = _utc_now_iso()
        try:
            await self._db.execute(
                """
                INSERT INTO notifications_log (event_id, user_id, scheduled_for, sent_at)
                VALUES (?, ?, ?, ?)
                """,
                (event_id, user_id, scheduled_for_iso, sent_at),
            )
            return True
        except aiosqlite.IntegrityError:
            logger.info(
                "Дубликат лог-записи пропущен: event_id=%s user_id=%s scheduled_for=%s",
                event_id,
                user_id,
                scheduled_for_iso,
            )
            return False
