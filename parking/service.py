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


    def check_in(
        self,
        plate_str: str,
        time_in: datetime,
        spot_id: Optional[str] = None,
        last_image_path: Optional[str] = None,
    ) -> dict:
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

        self.db.add_vehicle(
            plate=plate,
            time_in=time_in,
            spot_id=spot_id,
            last_image_path=last_image_path,
        )
        self.db.write_check_in_history(
            plate=plate,
            time_in=time_in,
            spot_id=spot_id,
            last_image_path=last_image_path,
        )



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

    def get_active_vehicles(self) -> list[dict]:
        return self.db.get_active_vehicles()

    def update_active_plate(self, old_plate: str, new_plate: str) -> dict:
        old_plate = (old_plate or '').strip().upper()
        new_plate = (new_plate or '').strip().upper()
        if not old_plate or not new_plate:
            return {"status": "error", "message": "Invalid plate"}

        updated = self.db.update_active_plate(old_plate=old_plate, new_plate=new_plate)
        if updated is None:
            # either old not found or new already exists
            return {"status": "error", "message": "Cannot update plate (maybe already exists or not found)", "plate": old_plate}

        # Update history plate only for IN rows (the current active record)
        # NOTE: requirement says only biển số changes, keep other fields.
        # Simplest: update all IN history rows for old_plate.
        with self.db._connect() as con:
            con.execute(
                "UPDATE history SET plate = ? WHERE plate = ? AND status = 'IN'",
                (new_plate, old_plate),
            )

        return {"status": "ok", "event": "ACTIVE_UPDATE_PLATE", "old_plate": old_plate, "new_plate": new_plate}

    def delete_active_vehicle(self, plate: str) -> dict:
        plate = (plate or '').strip().upper()
        if not plate:
            return {"status": "error", "message": "Invalid plate"}

        active = self.db.delete_active_vehicle(plate)
        if active is None:
            return {"status": "error", "message": "Plate not found inside", "plate": plate}

        # Remove corresponding history IN row so history bảng không còn xe này
        self.db.delete_history_in_by_plate_and_spot(plate=plate, spot_id=active.get('spot_id'))

        return {"status": "ok", "event": "ACTIVE_DELETE", "plate": plate, "spot_id": active.get('spot_id')}

    def update_history_plate(self, event_id: int, new_plate: str) -> dict:
        try:
            event_id = int(event_id)
        except Exception:
            return {"status": "error", "message": "Invalid event_id"}

        new_plate = (new_plate or '').strip().upper()
        if not new_plate:
            return {"status": "error", "message": "Invalid plate"}

        updated = self.db.update_history_plate(event_id=event_id, new_plate=new_plate)
        if updated is None:
            return {"status": "error", "message": "History event not found"}

        # If this history event is currently IN, ensure active_vehicles record plate matches.
        # Update active by deleting old active plate if needed.
        if updated.get('status') == 'IN':
            # Find active by the NEW plate; if not exists, the old active plate is not updated by DB layer.
            # So we search active record by spot_id from history and update by old plate.
            active_by_new = self.db.get_active_vehicle((new_plate or '').strip().upper())
            if active_by_new is None:
                # Update by spot_id: get any active record that has same spot_id.
                # There is at most one active per spot for typical flow.
                spot_id = updated.get('spot_id')
                if spot_id:
                    # scan active_vehicles to find the one at spot_id
                    actives = self.db.get_active_vehicles() or []
                    for a in actives:
                        if (a.get('spot_id') == spot_id):
                            old_active_plate = (a.get('plate') or '').strip().upper()
                            if old_active_plate and old_active_plate != new_plate:
                                self.db.update_active_plate(old_plate=old_active_plate, new_plate=new_plate)
                            break

        return {"status": "ok", "event": "HISTORY_UPDATE_PLATE", "event_id": event_id, "new_plate": new_plate }


    def delete_history_event(self, event_id: int) -> dict:
        try:
            event_id = int(event_id)
        except Exception:
            return {"status": "error", "message": "Invalid event_id"}

        row = self.db.delete_history_event(event_id)
        if row is None:
            return {"status": "error", "message": "History event not found"}

        # If deleting an IN record (xe đang đổ), remove active vehicle too (spot chuyển xanh)
        if row.get('status') == 'IN':
            plate = (row.get('plate') or '').strip().upper()
            if plate:
                self.db.delete_active_vehicle(plate)

        return {"status": "ok", "event": "HISTORY_DELETE", "event_id": event_id, "deleted": row}



