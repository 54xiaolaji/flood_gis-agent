# -*- coding: utf-8 -*-

from pathlib import Path
from typing import Optional

from .config import AgentConfig
from .data_scan import DataScanner
from .map_maker import MapMaker
from .qc import QualityChecker
from .report import ReportWriter


class FloodGisAgent:
    """
    洪水风险图制图质检一体化 Agent。

    工作流：
    1. 扫描输入目录中的 GIS 数据；
    2. 根据文件名、字段名和配置关键词识别图层类型；
    3. 执行质检规则；
    4. 生成数据清单和质检报告；
    5. 可选：批量输出专题图。
    """

    def __init__(
        self,
        input_dir: Path,
        output_dir: Path,
        config: AgentConfig,
        make_maps: bool = False,
        max_files: Optional[int] = None,
    ):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.config = config
        self.make_maps = make_maps
        self.max_files = max_files

    def run(self):
        print("一、扫描 GIS 数据...")
        scanner = DataScanner(self.input_dir, self.config, max_files=self.max_files)
        layers = scanner.scan()
        print(f"已扫描到 {len(layers)} 个 GIS 数据文件。")

        print("二、执行质检规则...")
        checker = QualityChecker(layers, self.config)
        issues = checker.run()
        print(f"发现质检问题 {len(issues)} 项。")

        print("三、生成质检报告...")
        writer = ReportWriter(layers, issues, self.output_dir)
        writer.write_all()

        if self.make_maps:
            print("四、批量输出专题图...")
            maker = MapMaker(layers, self.config, self.output_dir)
            outputs = maker.make_all()
            print(f"已输出专题图 {len(outputs)} 张。")
        else:
            print("四、未启用批量制图。如需出图，请添加 --make-maps。")
