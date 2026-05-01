# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ExpectedLayer:
    key: str
    title: str
    keywords: List[str]
    kind: str = "vector"
    required_fields: List[str] = field(default_factory=list)
    cmap: str = "viridis"


@dataclass
class AgentConfig:
    project_name: str
    target_crs: Optional[str]
    scan_recursive: bool
    qc_rules: Dict[str, Any]
    map_options: Dict[str, Any]
    expected_layers: List[ExpectedLayer]


def _default_config() -> AgentConfig:
    return AgentConfig(
        project_name="洪水风险图制图质检一体化 Agent",
        target_crs=None,
        scan_recursive=True,
        qc_rules={
            "check_crs": True,
            "check_geometry_valid": True,
            "check_empty_layer": True,
            "check_required_fields": True,
            "check_raster_nodata": True,
            "check_bounds_overlap": True,
            "max_nodata_ratio": 0.85,
            "min_bbox_overlap_ratio": 0.10,
        },
        map_options={
            "dpi": 200,
            "figsize": [11.69, 8.27],
            "boundary_keywords": ["行政区", "边界", "范围", "boundary"],
            "label_field_candidates": ["名称", "name", "NAME"],
            "output_format": "png",
        },
        expected_layers=[],
    )


def load_config(path: Path) -> AgentConfig:
    """
    加载 YAML 配置。
    如果配置文件不存在，则使用默认配置。
    """
    if not path.exists():
        print(f"提示：配置文件不存在，使用默认配置：{path}")
        return _default_config()

    try:
        import yaml
    except ImportError as exc:
        raise ImportError("缺少 PyYAML，请先安装：pip install pyyaml") from exc

    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    project = raw.get("project", {})
    qc_rules = raw.get("qc_rules", {})
    map_options = raw.get("map", {})

    layers = []
    for item in raw.get("expected_layers", []):
        layers.append(
            ExpectedLayer(
                key=item.get("key", ""),
                title=item.get("title", item.get("key", "")),
                keywords=item.get("keywords", []),
                kind=item.get("kind", "vector"),
                required_fields=item.get("required_fields", []),
                cmap=item.get("cmap", "viridis"),
            )
        )

    default = _default_config()
    merged_qc = {**default.qc_rules, **qc_rules}
    merged_map = {**default.map_options, **map_options}

    return AgentConfig(
        project_name=project.get("name", default.project_name),
        target_crs=project.get("target_crs", default.target_crs),
        scan_recursive=bool(project.get("scan_recursive", default.scan_recursive)),
        qc_rules=merged_qc,
        map_options=merged_map,
        expected_layers=layers,
    )
