# -*- coding: utf-8 -*-

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .config import AgentConfig
from .utils import RASTER_EXTS, VECTOR_EXTS, iter_gis_files, text_match_score


@dataclass
class LayerMeta:
    path: str
    file_name: str
    suffix: str
    kind: str
    matched_key: Optional[str] = None
    matched_title: Optional[str] = None
    crs: Optional[str] = None
    bounds: Optional[Tuple[float, float, float, float]] = None
    feature_count: Optional[int] = None
    fields: List[str] = field(default_factory=list)
    geometry_type: Optional[str] = None
    raster_width: Optional[int] = None
    raster_height: Optional[int] = None
    raster_count: Optional[int] = None
    nodata: Optional[Any] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    nodata_ratio: Optional[float] = None
    read_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.bounds is not None:
            d["bounds"] = ",".join([str(round(v, 6)) for v in self.bounds])
        return d


class DataScanner:
    def __init__(self, input_dir: Path, config: AgentConfig, max_files: Optional[int] = None):
        self.input_dir = input_dir
        self.config = config
        self.max_files = max_files

    def scan(self) -> List[LayerMeta]:
        layers: List[LayerMeta] = []
        for path in iter_gis_files(
            self.input_dir,
            recursive=self.config.scan_recursive,
            max_files=self.max_files,
        ):
            suffix = path.suffix.lower()
            if suffix in VECTOR_EXTS:
                meta = self._scan_vector(path)
            elif suffix in RASTER_EXTS:
                meta = self._scan_raster(path)
            else:
                continue

            self._match_expected_layer(meta)
            layers.append(meta)
        return layers

    def _scan_vector(self, path: Path) -> LayerMeta:
        meta = LayerMeta(
            path=str(path),
            file_name=path.name,
            suffix=path.suffix.lower(),
            kind="vector",
        )
        try:
            import geopandas as gpd
        except ImportError as exc:
            meta.read_error = "缺少 geopandas，请先安装 geopandas。"
            return meta

        try:
            gdf = gpd.read_file(path)
            meta.feature_count = int(len(gdf))
            meta.fields = [str(c) for c in gdf.columns if c != gdf.geometry.name]
            meta.crs = str(gdf.crs) if gdf.crs is not None else None
            meta.geometry_type = str(gdf.geom_type.dropna().mode().iloc[0]) if len(gdf) > 0 and not gdf.geom_type.dropna().empty else None
            if len(gdf) > 0:
                bounds = gdf.total_bounds
                meta.bounds = tuple(float(x) for x in bounds)
        except Exception as exc:
            meta.read_error = str(exc)
        return meta

    def _scan_raster(self, path: Path) -> LayerMeta:
        meta = LayerMeta(
            path=str(path),
            file_name=path.name,
            suffix=path.suffix.lower(),
            kind="raster",
        )
        try:
            import numpy as np
            import rasterio
        except ImportError:
            meta.read_error = "缺少 rasterio 或 numpy，请先安装 rasterio。"
            return meta

        try:
            with rasterio.open(path) as src:
                meta.crs = str(src.crs) if src.crs is not None else None
                meta.bounds = tuple(float(x) for x in src.bounds)
                meta.raster_width = int(src.width)
                meta.raster_height = int(src.height)
                meta.raster_count = int(src.count)
                meta.nodata = src.nodata

                arr = src.read(1, masked=True)
                total = arr.size
                masked = int(arr.mask.sum()) if hasattr(arr, "mask") and arr.mask is not False else 0
                meta.nodata_ratio = float(masked / total) if total else None

                valid = arr.compressed() if hasattr(arr, "compressed") else arr.reshape(-1)
                if valid.size > 0:
                    meta.min_value = float(np.nanmin(valid))
                    meta.max_value = float(np.nanmax(valid))
        except Exception as exc:
            meta.read_error = str(exc)
        return meta

    def _match_expected_layer(self, meta: LayerMeta) -> None:
        best_score = 0
        best = None
        text = f"{meta.file_name} {' '.join(meta.fields)}"
        for layer in self.config.expected_layers:
            score = text_match_score(text, layer.keywords)
            if score > best_score:
                best_score = score
                best = layer

        if best is not None and best_score > 0:
            meta.matched_key = best.key
            meta.matched_title = best.title
