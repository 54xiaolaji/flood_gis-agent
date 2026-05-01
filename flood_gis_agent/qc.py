# -*- coding: utf-8 -*-

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional

from .config import AgentConfig
from .data_scan import LayerMeta
from .utils import bbox_overlap_ratio, text_match_score


@dataclass
class QualityIssue:
    severity: str
    layer_name: str
    layer_path: str
    issue_type: str
    description: str
    suggestion: str

    def to_dict(self):
        return asdict(self)


class QualityChecker:
    def __init__(self, layers: List[LayerMeta], config: AgentConfig):
        self.layers = layers
        self.config = config
        self.issues: List[QualityIssue] = []

    def run(self) -> List[QualityIssue]:
        self._check_read_errors()
        self._check_expected_layers()
        self._check_layer_basic_quality()
        self._check_required_fields()
        self._check_bounds_overlap()
        return self.issues

    def _add(self, severity: str, layer: Optional[LayerMeta], issue_type: str, description: str, suggestion: str):
        self.issues.append(
            QualityIssue(
                severity=severity,
                layer_name=layer.file_name if layer else "",
                layer_path=layer.path if layer else "",
                issue_type=issue_type,
                description=description,
                suggestion=suggestion,
            )
        )

    def _check_read_errors(self):
        for layer in self.layers:
            if layer.read_error:
                self._add(
                    "ERROR",
                    layer,
                    "读取失败",
                    f"数据无法正常读取：{layer.read_error}",
                    "检查文件是否损坏、是否缺少同名 .dbf/.shx/.prj 文件，或是否安装 geopandas/rasterio。",
                )

    def _check_expected_layers(self):
        if not self.config.expected_layers:
            return

        for expected in self.config.expected_layers:
            matched = [x for x in self.layers if x.matched_key == expected.key]
            if not matched:
                self._add(
                    "WARN",
                    None,
                    "图层缺失",
                    f"未识别到预期图层：{expected.title}。匹配关键词：{expected.keywords}",
                    "检查文件命名或在 config.example.yaml 中补充该图层的关键词。",
                )

    def _check_layer_basic_quality(self):
        rules = self.config.qc_rules
        target_crs = self.config.target_crs

        for layer in self.layers:
            if layer.read_error:
                continue

            if rules.get("check_crs", True):
                if not layer.crs:
                    self._add(
                        "ERROR",
                        layer,
                        "坐标系缺失",
                        "该图层未识别到坐标系信息。",
                        "在 ArcGIS Pro 中先 Define Projection，或补充 .prj 文件后再运行。",
                    )
                elif target_crs and target_crs not in str(layer.crs):
                    self._add(
                        "WARN",
                        layer,
                        "坐标系不一致",
                        f"当前坐标系为 {layer.crs}，目标坐标系为 {target_crs}。",
                        "建议统一投影到项目目标坐标系后再制图和质检。",
                    )

            if rules.get("check_empty_layer", True):
                if layer.kind == "vector" and layer.feature_count == 0:
                    self._add(
                        "ERROR",
                        layer,
                        "空图层",
                        "矢量图层要素数量为 0。",
                        "检查导出范围、筛选条件或原始数据是否为空。",
                    )

            if layer.kind == "vector":
                self._check_vector_geometry(layer)

            if layer.kind == "raster" and rules.get("check_raster_nodata", True):
                max_ratio = float(rules.get("max_nodata_ratio", 0.85))
                if layer.nodata_ratio is not None and layer.nodata_ratio > max_ratio:
                    self._add(
                        "WARN",
                        layer,
                        "栅格空值比例偏高",
                        f"NoData/掩膜比例约为 {layer.nodata_ratio:.2%}，超过阈值 {max_ratio:.0%}。",
                        "检查栅格裁剪范围、NoData 设置和模型输出范围是否正确。",
                    )
                if layer.min_value is not None and layer.max_value is not None and layer.min_value == layer.max_value:
                    self._add(
                        "WARN",
                        layer,
                        "栅格值单一",
                        f"栅格最小值和最大值均为 {layer.min_value}。",
                        "检查该方案是否确实无淹没，或模型结果是否导出异常。",
                    )

            if layer.bounds is None:
                self._add(
                    "WARN",
                    layer,
                    "空间范围异常",
                    "未能读取图层空间范围。",
                    "检查几何或栅格空间参考信息是否完整。",
                )

    def _check_vector_geometry(self, layer: LayerMeta):
        if not self.config.qc_rules.get("check_geometry_valid", True):
            return
        if layer.read_error:
            return

        try:
            import geopandas as gpd
            gdf = gpd.read_file(layer.path)
            if len(gdf) == 0:
                return

            empty_count = int(gdf.geometry.is_empty.sum())
            null_count = int(gdf.geometry.isna().sum())
            invalid_count = int((~gdf.geometry.is_valid).sum())

            if empty_count > 0 or null_count > 0:
                self._add(
                    "ERROR",
                    layer,
                    "空几何",
                    f"存在空几何 {empty_count} 个，缺失几何 {null_count} 个。",
                    "在 GIS 软件中修复或删除空几何要素。",
                )

            if invalid_count > 0:
                self._add(
                    "WARN",
                    layer,
                    "几何无效",
                    f"存在无效几何 {invalid_count} 个。",
                    "可使用 Repair Geometry、Make Valid 或 buffer(0) 等方式修复。",
                )
        except Exception as exc:
            self._add(
                "WARN",
                layer,
                "几何检查失败",
                f"未能完成几何有效性检查：{exc}",
                "检查数据格式和 geopandas/shapely 环境。",
            )

    def _check_required_fields(self):
        if not self.config.qc_rules.get("check_required_fields", True):
            return

        expected_by_key = {x.key: x for x in self.config.expected_layers}

        for layer in self.layers:
            if layer.kind != "vector":
                continue
            if not layer.matched_key:
                continue
            expected = expected_by_key.get(layer.matched_key)
            if not expected:
                continue

            field_lower = {f.lower(): f for f in layer.fields}
            for req in expected.required_fields:
                if req.lower() not in field_lower:
                    self._add(
                        "WARN",
                        layer,
                        "字段缺失",
                        f"图层被识别为“{expected.title}”，但缺少字段：{req}。",
                        "检查字段命名，或在配置文件中修改 required_fields。",
                    )

    def _find_boundary_layer(self) -> Optional[LayerMeta]:
        keywords = self.config.map_options.get("boundary_keywords", [])
        best = None
        best_score = 0
        for layer in self.layers:
            if layer.kind != "vector" or layer.bounds is None:
                continue
            text = f"{layer.file_name} {' '.join(layer.fields)}"
            score = text_match_score(text, keywords)
            if score > best_score:
                best_score = score
                best = layer
        return best

    def _check_bounds_overlap(self):
        if not self.config.qc_rules.get("check_bounds_overlap", True):
            return

        boundary = self._find_boundary_layer()
        if boundary is None or boundary.bounds is None:
            return

        threshold = float(self.config.qc_rules.get("min_bbox_overlap_ratio", 0.10))

        for layer in self.layers:
            if layer.path == boundary.path or layer.bounds is None:
                continue
            ratio = bbox_overlap_ratio(boundary.bounds, layer.bounds)
            if ratio < threshold:
                self._add(
                    "WARN",
                    layer,
                    "空间范围疑似错位",
                    f"与边界图层“{boundary.file_name}”的外包矩形重叠率约为 {ratio:.2%}，低于阈值 {threshold:.0%}。",
                    "重点检查坐标系是否定义错误、是否误用经纬度/投影坐标、或是否选错项目范围。",
                )
