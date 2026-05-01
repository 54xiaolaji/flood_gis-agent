# -*- coding: utf-8 -*-

from collections import Counter, defaultdict
from pathlib import Path
from typing import List

from .data_scan import LayerMeta
from .qc import QualityIssue


class ReportWriter:
    def __init__(self, layers: List[LayerMeta], issues: List[QualityIssue], output_dir: Path):
        self.layers = layers
        self.issues = issues
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_all(self):
        self.write_inventory()
        self.write_qc_report()
        self.write_summary()

    def write_inventory(self):
        import pandas as pd

        rows = [x.to_dict() for x in self.layers]
        df = pd.DataFrame(rows)
        df.to_csv(self.output_dir / "data_inventory.csv", index=False, encoding="utf-8-sig")

    def write_qc_report(self):
        import pandas as pd

        rows = [x.to_dict() for x in self.issues]
        df = pd.DataFrame(rows)
        if df.empty:
            df = pd.DataFrame(
                [{
                    "severity": "OK",
                    "layer_name": "",
                    "layer_path": "",
                    "issue_type": "未发现明显问题",
                    "description": "按当前规则未发现明显质检问题。",
                    "suggestion": "可结合人工复核和项目验收规范进一步检查。",
                }]
            )

        with pd.ExcelWriter(self.output_dir / "qc_report.xlsx", engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="质检问题清单", index=False)

            summary = (
                df.groupby(["severity", "issue_type"], dropna=False)
                .size()
                .reset_index(name="count")
            )
            summary.to_excel(writer, sheet_name="问题统计", index=False)

    def write_summary(self):
        issue_counter = Counter([x.severity for x in self.issues])
        type_counter = Counter([x.issue_type for x in self.issues])
        matched_counter = Counter([x.matched_title or "未匹配" for x in self.layers])

        lines = []
        lines.append("# 洪水风险图制图质检一体化 Agent 运行摘要\n")
        lines.append("## 一、数据扫描情况\n")
        lines.append(f"- 扫描到 GIS 数据文件：{len(self.layers)} 个")
        lines.append(f"- 矢量数据：{sum(1 for x in self.layers if x.kind == 'vector')} 个")
        lines.append(f"- 栅格数据：{sum(1 for x in self.layers if x.kind == 'raster')} 个")
        lines.append("")

        lines.append("## 二、识别到的图层类型\n")
        for name, count in matched_counter.most_common():
            lines.append(f"- {name}：{count} 个")
        lines.append("")

        lines.append("## 三、质检问题统计\n")
        if not self.issues:
            lines.append("- 按当前规则未发现明显问题。")
        else:
            for sev in ["ERROR", "WARN", "INFO", "OK"]:
                if issue_counter.get(sev, 0):
                    lines.append(f"- {sev}：{issue_counter[sev]} 项")
        lines.append("")

        lines.append("## 四、主要问题类型\n")
        if not type_counter:
            lines.append("- 暂无。")
        else:
            for issue_type, count in type_counter.most_common():
                lines.append(f"- {issue_type}：{count} 项")
        lines.append("")

        lines.append("## 五、建议使用方式\n")
        lines.append("1. 先处理 ERROR 类问题，例如读取失败、坐标系缺失、空图层、空几何。")
        lines.append("2. 再处理 WARN 类问题，例如字段缺失、坐标系不一致、空间范围疑似错位。")
        lines.append("3. 对淹没水深、到达时间、淹没历时、最大流速等关键成果，建议结合人工图面复核。")
        lines.append("4. 若图层未被正确识别，可在 config.example.yaml 中补充关键词。")
        lines.append("")

        (self.output_dir / "qc_summary.md").write_text("\n".join(lines), encoding="utf-8")
