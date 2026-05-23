from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable


@dataclass(frozen=True)
class HistoryRow:
    event_id: int
    plate: str
    time_in: str | None
    time_out: str | None
    duration_seconds: int | None
    fee_vnd: int | None
    status: str
    spot_id: str | None


class ParkingDB:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()


    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def _init_db(self) -> None:
        with self._connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS spots (
                    spot_id TEXT PRIMARY KEY,
                    is_active INTEGER NOT NULL DEFAULT 1
                );
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS active_vehicles (
                    plate TEXT PRIMARY KEY,
                    time_in TEXT NOT NULL,
                    spot_id TEXT,
                    last_image_path TEXT,
                    FOREIGN KEY (spot_id) REFERENCES spots(spot_id)
                );
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS history (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plate TEXT NOT NULL,
                    time_in TEXT,
                    time_out TEXT,
                    duration_seconds INTEGER,
                    fee_vnd INTEGER,
                    status TEXT NOT NULL,
                    spot_id TEXT,
                    last_image_path TEXT
                );
                """
            )
            # Create default spots if empty
            cur = con.execute("SELECT COUNT(*) as cnt FROM spots")
            cnt = int(cur.fetchone()["cnt"])
            if cnt == 0:
                for i in range(1, 21):
                    con.execute("INSERT INTO spots(spot_id, is_active) VALUES(?, 1)", (f"S{i:02d}",))

    def get_spots(self) -> list[dict[str, Any]]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT spot_id, is_active FROM spots ORDER BY spot_id"
            ).fetchall()
            return [dict(r) for r in rows]

    def get_free_spot(self) -> str | None:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT s.spot_id
                FROM spots s
                WHERE s.is_active = 1
                  AND s.spot_id NOT IN (SELECT spot_id FROM active_vehicles WHERE spot_id IS NOT NULL)
                ORDER BY s.spot_id
                LIMIT 1
                """
            ).fetchall()
            return rows[0]["spot_id"] if rows else None

    def add_vehicle(self, plate: str, time_in: datetime, spot_id: str | None, last_image_path: str | None = None) -> None:
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO active_vehicles(plate, time_in, spot_id, last_image_path)
                VALUES(?,?,?,?)
                """,
                (plate, time_in.isoformat(timespec="seconds"), spot_id, last_image_path),
            )

    def get_active_vehicle(self, plate: str) -> dict[str, Any] | None:
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM active_vehicles WHERE plate = ?", (plate,)
            ).fetchone()
            return dict(row) if row else None

    def get_active_vehicles(self) -> list[dict[str, Any]]:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT plate, time_in, spot_id, last_image_path
                FROM active_vehicles
                ORDER BY time_in DESC
                """
            ).fetchall()
            return [dict(r) for r in rows]


    def remove_vehicle(self, plate: str) -> dict[str, Any] | None:
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM active_vehicles WHERE plate = ?", (plate,)
            ).fetchone()
            if not row:
                return None
            con.execute("DELETE FROM active_vehicles WHERE plate = ?", (plate,))
            return dict(row)

    def write_check_in_history(self, plate: str, time_in: datetime, spot_id: str | None, last_image_path: str | None = None) -> None:
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO history(plate, time_in, time_out, duration_seconds, fee_vnd, status, spot_id, last_image_path)
                VALUES(?, ?, NULL, NULL, NULL, 'IN', ?, ?)
                """,
                (plate, time_in.isoformat(timespec="seconds"), spot_id, last_image_path),
            )

    def write_check_out_history(
        self,
        plate: str,
        time_in: datetime,
        time_out: datetime,
        duration_seconds: int,
        fee_vnd: int,
        spot_id: str | None,
        last_image_path: str | None = None,
    ) -> None:
        with self._connect() as con:
            # Update latest IN record without time_out
            con.execute(
                """
                UPDATE history
                SET time_out = ?, duration_seconds = ?, fee_vnd = ?, status = 'OUT', last_image_path = ?
                WHERE plate = ? AND status = 'IN' AND time_in = ?
                """,
                (
                    time_out.isoformat(timespec="seconds"),
                    duration_seconds,
                    fee_vnd,
                    last_image_path,
                    plate,
                    time_in.isoformat(timespec="seconds"),
                ),
            )
            # If nothing updated (edge case), insert a row
            # (SQLite's total_changes is connection-wide; we instead re-check existence.)
            updated = con.execute(
                """
                SELECT 1
                FROM history
                WHERE plate = ? AND status = 'OUT' AND time_out = ?
                LIMIT 1
                """,
                (plate, time_out.isoformat(timespec="seconds")),
            ).fetchone()
            if updated is None:
                con.execute(
                    """
                    INSERT INTO history(plate, time_in, time_out, duration_seconds, fee_vnd, status, spot_id, last_image_path)
                    VALUES(?, ?, ?, ?, ?, 'OUT', ?, ?)
                    """,
                    (
                        plate,
                        time_in.isoformat(timespec="seconds"),
                        time_out.isoformat(timespec="seconds"),
                        duration_seconds,
                        fee_vnd,
                        spot_id,
                        last_image_path,
                    ),
                )


    def get_history(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT event_id, plate, time_in, time_out, duration_seconds, fee_vnd, status, spot_id
                FROM history
                ORDER BY event_id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

