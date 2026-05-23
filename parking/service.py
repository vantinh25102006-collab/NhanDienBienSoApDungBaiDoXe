from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from parking.db import ParkingDB


DEFAULT_RATE_VND_PER_HOUR = 10000


@dataclass(frozen=True)
class FeeRule:
    vnd_per_hour: int = DEFAULT_RATE_VND_PER_HOUR

    def compute_fee_vnd(self, duration_seconds: int) -> int:
        # Rule: x VND / hour, làm tròn lên theo giờ; tối thiểu = 1 giờ
        hours = (duration_seconds + 3599) // 3600
        if hours < 1:
            hours = 1
        return int(hours * self.vnd_per_hour)


class ParkingService:
    def __init__(self, db_path: str, fee_rule: FeeRule | None = None):
        self.db = ParkingDB(db_path=db_path)
        self.fee_rule = fee_rule or FeeRule()

    def check_in(self, plate_str: str, time_in: datetime, spot_id: Optional[str] = None) -> dict:
        plate = (plate_str or "").strip().upper()
        if not plate:
            return {"status": "error", "message": "Invalid plate"}

        active = self.db.get_active_vehicle(plate)
        if active is not None:
            return {"status": "error", "message": "Plate already inside", "plate": plate}

        if spot_id is None:
            spot_id = self.db.get_free_spot()

        if spot_id is None:
            return {"status": "error", "message": "No free spot"}

        self.db.add_vehicle(plate=plate, time_in=time_in, spot_id=spot_id)
        self.db.write_check_in_history(plate=plate, time_in=time_in, spot_id=spot_id)

        return {
            "status": "ok",
            "event": "IN",
            "plate": plate,
            "time_in": time_in.isoformat(timespec="seconds"),
            "spot_id": spot_id,
        }

    def check_out(self, plate_str: str, time_out: datetime) -> dict:
        plate = (plate_str or "").strip().upper()
        if not plate:
            return {"status": "error", "message": "Invalid plate"}

        active = self.db.get_active_vehicle(plate)
        if active is None:
            return {"status": "error", "message": "Plate not found inside", "plate": plate}

        time_in = datetime.fromisoformat(active["time_in"])
        duration_seconds = int((time_out - time_in).total_seconds())
        if duration_seconds < 0:
            duration_seconds = 0

        fee_vnd = self.fee_rule.compute_fee_vnd(duration_seconds)
        spot_id = active.get("spot_id")

        # remove active
        self.db.remove_vehicle(plate)

        self.db.write_check_out_history(
            plate=plate,
            time_in=time_in,
            time_out=time_out,
            duration_seconds=duration_seconds,
            fee_vnd=fee_vnd,
            spot_id=spot_id,
        )

        return {
            "status": "ok",
            "event": "OUT",
            "plate": plate,
            "time_in": time_in.isoformat(timespec="seconds"),
            "time_out": time_out.isoformat(timespec="seconds"),
            "duration_seconds": duration_seconds,
            "fee_vnd": fee_vnd,
            "spot_id": spot_id,
        }

    def get_history(self, limit: int = 200) -> list[dict]:
        return self.db.get_history(limit=limit)

    def get_spots(self) -> list[dict]:
        return self.db.get_spots()

