# -*- coding: utf-8 -*-
"""
洪水风险图制图质检一体化 Agent 启动脚本

示例：
python run_agent.py --input "D:/data" --output "D:/result" --config config.example.yaml --make-maps
"""

import argparse
from pathlib import Path

from flood_gis_agent.config import load_config
from flood_gis_agent.orchestrator import FloodGisAgent


def parse_args():
    parser = argparse.ArgumentParser(description="洪水风险图制图质检一体化 Agent")
    parser.add_argument("--input", required=True, help="输入数据文件夹")
    parser.add_argument("--output", required=True, help="输出结果文件夹")
    parser.add_argument("--config", default="config.example.yaml", help="配置文件路径")
    parser.add_argument("--make-maps", action="store_true", help="是否批量出图")
    parser.add_argument("--max-files", type=int, default=None, help="最多扫描文件数量，调试时可使用")
    return parser.parse_args()


def main():
    args = parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)
    config_path = Path(args.config)

    if not input_dir.exists():
        raise FileNotFoundError(f"输入文件夹不存在：{input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    config = load_config(config_path)
    agent = FloodGisAgent(
        input_dir=input_dir,
        output_dir=output_dir,
        config=config,
        make_maps=args.make_maps,
        max_files=args.max_files,
    )
    agent.run()

    print("\n运行完成。")
    print(f"输出目录：{output_dir.resolve()}")
    print("主要结果：qc_report.xlsx、qc_summary.md、data_inventory.csv")
    if args.make_maps:
        print("专题图目录：maps/")


if __name__ == "__main__":
    main()
