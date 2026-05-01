# -*- coding: utf-8 -*-

from pathlib import Path
from typing import Dict, List, Optional

from .config import AgentConfig, ExpectedLayer
from .data_scan import LayerMeta
from .utils import safe_name, text_match_score


class MapMaker:
    def __init__(self, layers: List[LayerMeta], config: AgentConfig, output_dir: Path):
        self.layers = [x for x in layers if not x.read_error]
        self.config = config
        self.output_dir = output_dir
        self.map_dir = output_dir / "maps"
        self.map_dir.mkdir(parents=True, exist_ok=True)

    def make_all(self) -> List[Path]:
        outputs: List[Path] = []

        expected_by_key = {x.key: x for x in self.config.expected_layers}

        for layer in self.layers:
            if not layer.matched_key:
                continue
            expected = expected_by_key.get(layer.matched_key)
            if expected is None:
                continue

            try:
                out = self._make_single_map(layer, expected)
                if out:
                    outputs.append(out)
            except Exception as exc:
                print(f"出图失败：{layer.file_name}，原因：{exc}")

        return outputs

    def _find_boundary_path(self) -> Optional[str]:
        keywords = self.config.map_options.get("boundary_keywords", [])
        best = None
        best_score = 0
        for layer in self.layers:
            if layer.kind != "vector":
                continue
            text = f"{layer.file_name} {' '.join(layer.fields)}"
            score = text_match_score(text, keywords)
            if score > best_score:
                best = layer
                best_score = score
        return best.path if best is not None else None

    def _make_single_map(self, layer: LayerMeta, expected: ExpectedLayer) -> Optional[Path]:
        import matplotlib.pyplot as plt

        output_format = self.config.map_options.get("output_format", "png")
        dpi = int(self.config.map_options.get("dpi", 200))
        figsize = self.config.map_options.get("figsize", [11.69, 8.27])

        fig, ax = plt.subplots(figsize=figsize)
        ax.set_title(f"{expected.title} - {Path(layer.file_name).stem}", fontsize=16, pad=14)

        boundary_path = self._find_boundary_path()

        if layer.kind == "raster":
            self._plot_raster(ax, layer, expected)
        elif layer.kind == "vector":
            self._plot_vector(ax, layer, expected)
        else:
            return None

        if boundary_path and boundary_path != layer.path:
            self._plot_boundary(ax, boundary_path)

        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.ticklabel_format(style="plain", useOffset=False)
        ax.grid(True, linewidth=0.3, alpha=0.5)

        out_name = safe_name(f"{expected.title}_{Path(layer.file_name).stem}.{output_format}")
        out_path = self.map_dir / out_name

        plt.tight_layout()
        fig.savefig(out_path, dpi=dpi)
        plt.close(fig)
        return out_path

    def _plot_raster(self, ax, layer: LayerMeta, expected: ExpectedLayer):
        import rasterio
        from rasterio.plot import show

        with rasterio.open(layer.path) as src:
            image = src.read(1, masked=True)
            show(image, transform=src.transform, ax=ax, cmap=expected.cmap)
            # 单独加 colorbar，避免 rasterio.show 的自动行为不可控
            im = ax.images[-1] if ax.images else None
            if im is not None:
                import matplotlib.pyplot as plt
                plt.colorbar(im, ax=ax, fraction=0.035, pad=0.02)

    def _plot_vector(self, ax, layer: LayerMeta, expected: ExpectedLayer):
        import geopandas as gpd

        gdf = gpd.read_file(layer.path)
        if len(gdf) == 0:
            return

        geom_types = set(gdf.geom_type.dropna().unique().tolist())

        if any("Point" in x for x in geom_types):
            gdf.plot(ax=ax, markersize=25, alpha=0.9)
            self._try_label(ax, gdf)
        elif any("Line" in x for x in geom_types):
            gdf.plot(ax=ax, linewidth=1.5, alpha=0.9)
        else:
            gdf.plot(ax=ax, cmap=expected.cmap, alpha=0.65, edgecolor="black", linewidth=0.3)

    def _plot_boundary(self, ax, boundary_path: str):
        try:
            import geopandas as gpd
            boundary = gpd.read_file(boundary_path)
            if len(boundary) > 0:
                boundary.boundary.plot(ax=ax, linewidth=1.0)
        except Exception as exc:
            print(f"边界叠加失败：{boundary_path}，原因：{exc}")

    def _try_label(self, ax, gdf):
        candidates = self.config.map_options.get("label_field_candidates", [])
        label_field = None
        fields_lower = {str(c).lower(): c for c in gdf.columns}
        for cand in candidates:
            if str(cand).lower() in fields_lower:
                label_field = fields_lower[str(cand).lower()]
                break

        if label_field is None:
            return

        try:
            for _, row in gdf.iterrows():
                geom = row.geometry
                if geom is None or geom.is_empty:
                    continue
                ax.annotate(
                    text=str(row[label_field])[:20],
                    xy=(geom.centroid.x, geom.centroid.y),
                    fontsize=7,
                    ha="center",
                    va="center",
                )
        except Exception:
            pass
