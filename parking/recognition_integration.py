from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import Main


def recognize_plate_from_image(image_path: str) -> str:
    return Main.detect_plate_str_from_image(image_path)

