# -*- coding: utf-8 -*-

from pathlib import Path
from typing import Iterable, Optional, Tuple


VECTOR_EXTS = {".shp", ".geojson", ".gpkg"}
RASTER_EXTS = {".tif", ".tiff", ".asc"}


def safe_name(name: str) -> str:
    bad = '<>:"/\\|?*'
    for ch in bad:
        name = name.replace(ch, "_")
    return name.strip() or "unnamed"


def iter_gis_files(input_dir: Path, recursive: bool = True, max_files: Optional[int] = None):
    pattern = "**/*" if recursive else "*"
    count = 0
    for path in input_dir.glob(pattern):
        if not path.is_file():
            continue
        if path.suffix.lower() not in VECTOR_EXTS | RASTER_EXTS:
            continue
        yield path
        count += 1
        if max_files is not None and count >= max_files:
            break


def text_match_score(text: str, keywords: Iterable[str]) -> int:
    text_lower = text.lower()
    score = 0
    for kw in keywords:
        if not kw:
            continue
        if str(kw).lower() in text_lower:
            score += 1
    return score


def bbox_area(bounds: Tuple[float, float, float, float]) -> float:
    minx, miny, maxx, maxy = bounds
    return max(0.0, maxx - minx) * max(0.0, maxy - miny)


def bbox_overlap_ratio(a, b) -> float:
    """
    计算两个外包矩形的交集面积 / 较小矩形面积。
    用于粗略判断图层空间范围是否明显错位。
    """
    if not a or not b:
        return 0.0

    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b

    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)

    inter = bbox_area((ix1, iy1, ix2, iy2))
    small = min(bbox_area(a), bbox_area(b))
    if small <= 0:
        return 0.0
    return inter / small
