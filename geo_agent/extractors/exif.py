from __future__ import annotations

import io

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

from geo_agent.models.schemas import ExifData


def _dms_to_decimal(dms, ref: str) -> float:
    degrees = float(dms[0])
    minutes = float(dms[1])
    seconds = float(dms[2])
    decimal = degrees + minutes / 60.0 + seconds / 3600.0
    if ref in ("S", "W"):
        decimal = -decimal
    return decimal


def extract_exif(image_bytes: bytes) -> ExifData:
    try:
        img = Image.open(io.BytesIO(image_bytes))
    except Exception:
        return ExifData()

    exif_raw = img.getexif()
    if not exif_raw:
        return ExifData()

    exif_dict: dict = {}
    for tag_id, value in exif_raw.items():
        tag_name = TAGS.get(tag_id, tag_id)
        exif_dict[tag_name] = value

    camera_make = exif_dict.get("Make")
    camera_model = exif_dict.get("Model")
    datetime_original = exif_dict.get("DateTimeOriginal") or exif_dict.get("DateTime")
    orientation = exif_dict.get("Orientation")

    if isinstance(camera_make, bytes):
        camera_make = camera_make.decode("utf-8", errors="replace").strip("\x00 ")
    if isinstance(camera_model, bytes):
        camera_model = camera_model.decode("utf-8", errors="replace").strip("\x00 ")
    if isinstance(datetime_original, bytes):
        datetime_original = datetime_original.decode("utf-8", errors="replace").strip("\x00 ")

    gps_info = exif_raw.get_ifd(0x8825)
    if not gps_info:
        return ExifData(
            camera_make=camera_make,
            camera_model=camera_model,
            datetime_original=datetime_original,
            orientation=orientation,
        )

    gps_data: dict = {}
    for key, val in gps_info.items():
        tag_name = GPSTAGS.get(key, key)
        gps_data[tag_name] = val

    lat = None
    lng = None
    try:
        if "GPSLatitude" in gps_data and "GPSLatitudeRef" in gps_data:
            lat = _dms_to_decimal(gps_data["GPSLatitude"], gps_data["GPSLatitudeRef"])
        if "GPSLongitude" in gps_data and "GPSLongitudeRef" in gps_data:
            lng = _dms_to_decimal(gps_data["GPSLongitude"], gps_data["GPSLongitudeRef"])
    except (TypeError, ValueError, IndexError):
        lat = None
        lng = None

    has_gps = lat is not None and lng is not None

    return ExifData(
        has_gps=has_gps,
        latitude=lat,
        longitude=lng,
        camera_make=camera_make,
        camera_model=camera_model,
        datetime_original=datetime_original,
        orientation=orientation,
    )
