# 洪水风险图制图质检一体化 Agent

这个项目把两个功能合在一起：

1. **洪水风险图智能质检 Agent**  
   自动扫描洪水风险图相关数据，检查坐标系、字段、几何、空值、栅格 NoData、图层缺失、图层范围一致性等问题，并生成质检报告。

2. **GIS 制图批处理 Agent**  
   根据配置文件自动识别“淹没水深、最大流速、到达时间、淹没历时、淹没范围、转移路线、安置点、行政边界”等图层，并批量输出专题图。

---

## 一、适用数据

支持常见开源 GIS 数据格式：

- 矢量：`.shp`、`.geojson`、`.gpkg`
- 栅格：`.tif`、`.tiff`、`.asc`

如果你的数据是 ArcGIS FileGDB，也建议先在 ArcGIS Pro 中导出为 Shapefile、GeoPackage 或 GeoTIFF 后再运行。

---

## 二、环境安装

建议使用 conda 环境，Windows 下更稳定：

```bash
conda create -n flood_agent python=3.10 -y
conda activate flood_agent
conda install -c conda-forge geopandas rasterio pyproj shapely fiona matplotlib pyyaml pandas openpyxl tqdm -y
```

或者使用 pip：

```bash
pip install -r requirements.txt
```

---

## 三、快速运行

### 1. 修改配置文件

打开 `config.example.yaml`，重点修改：

```yaml
project:
  target_crs: "EPSG:4547"
```

如果你的项目坐标系不是 EPSG:4547，可改为其他 EPSG，例如：

- `EPSG:4326`：WGS84 经纬度
- `EPSG:4547`：CGCS2000 / 3-degree Gauss-Kruger CM 114E
- `EPSG:3857`：Web Mercator

### 2. 执行质检 + 批量制图

```bash
python run_agent.py --input "D:/你的数据文件夹" --output "D:/输出结果" --config config.example.yaml --make-maps
```

### 3. 只做质检，不出图

```bash
python run_agent.py --input "D:/你的数据文件夹" --output "D:/输出结果" --config config.example.yaml
```

---

## 四、输出结果

运行完成后，输出目录中会生成：

```text
输出结果/
├─ qc_report.xlsx          # 质检问题清单
├─ qc_summary.md           # 质检摘要
├─ data_inventory.csv      # 数据扫描清单
└─ maps/                   # 批量专题图
   ├─ 淹没水深_xxx.png
   ├─ 最大流速_xxx.png
   └─ 转移路线_xxx.png
```

---

## 五、项目结构

```text
flood_gis_agent_project/
├─ run_agent.py
├─ config.example.yaml
├─ requirements.txt
├─ README.md
└─ flood_gis_agent/
   ├─ __init__.py
   ├─ config.py
   ├─ data_scan.py
   ├─ qc.py
   ├─ map_maker.py
   ├─ report.py
   ├─ orchestrator.py
   └─ utils.py
```

---

## 六、你可以根据自己的数据继续扩展

常见扩展方向：

1. 在 `config.example.yaml` 中增加新的图层类型，比如“危险区”“避险转移单元”“水利工程点”等。
2. 在 `qc.py` 中增加更细的验收规则，比如转移人数不能为空、安置区字段必须存在、路线线要素必须与安置点连通等。
3. 在 `map_maker.py` 中调整图例、色带、标题、比例尺、指北针、出图尺寸等。
4. 如果后续想接入大模型，可在质检问题生成后，把 `qc_report.xlsx` 提交给大模型自动生成“整改建议说明”。

---

## 七、当前版本定位

这是一个可运行的基础版，不直接替代 ArcGIS Pro 的专业制图流程，但可以作为：

- 洪水风险图数据初检工具；
- 多方案成果批量审查工具；
- 批量专题图快速预览工具；
- 项目验收前的数据质量自查工具；
- 后续接入大模型形成智能 Agent 的工程底座。
