#!/usr/bin/env python3

import os
import re
import argparse
import subprocess
import shutil
import time
from pathlib import Path


def extract_latency_from_path(latency_dir: Path) -> int:
    match = re.search(r'latency(\d+)', latency_dir.name, re.IGNORECASE)
    if match:
        return int(match.group(1))
    else:
        raise ValueError(f"无法从目录名 '{latency_dir.name}' 提取 latency")

def extract_tp_pp_ep(filename: str):
    """从文件名提取 tp, pp, ep"""
    tp = re.search(r'tp(\d+)', filename)
    pp = re.search(r'pp(\d+)', filename)
    ep = re.search(r'ep(\d+)', filename)

    tp_val = tp.group(1) if tp else "1"
    pp_val = pp.group(1) if pp else "1"
    ep_val = ep.group(1) if ep else "1"

    return tp_val, pp_val, ep_val

def main():
    parser = argparse.ArgumentParser(description="批量运行 SimAI_analytical（按 tp/pp/ep 命名，支持子目录输出）")
    parser.add_argument('--workLoadInput_dir', required=True, help='包含 latencyXXX 子目录的 workload 根目录')
    parser.add_argument('--output_dir', required=True, help='最终输出根目录')
    parser.add_argument('--num-gpus', type=int, default=32)
    parser.add_argument('--gpus-per-node', type=int, default=8)
    parser.add_argument('--nvlink-bandwidth', type=float, default=360)
    parser.add_argument('--nic-bandwidth', type=float, default=48.5)
    parser.add_argument('--nodes-per-switch', type=int, default=8)

    args = parser.parse_args()
    if args.num_gpus < 1 or args.gpus_per_node < 1 or args.num_gpus % args.gpus_per_node:
        parser.error('num-gpus must be a positive multiple of gpus-per-node')

    workLoadInput_dir = Path(args.workLoadInput_dir).resolve()
    output_dir = Path(args.output_dir).resolve()

    if not workLoadInput_dir.is_dir():
        raise FileNotFoundError(f"--workLoadInput_dir 不存在: {workLoadInput_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    simai_bin = Path("./bin/SimAI_analytical").resolve()
    if not simai_bin.exists():
        raise FileNotFoundError(f"SimAI_analytical 二进制未找到: {simai_bin}")

    cwd = Path(os.getcwd()).resolve()
    # ✅ SimAI 实际输出目录
    simai_output_subdir = cwd / "results"
    print(f"ℹ️  SimAI 实际输出目录: {simai_output_subdir}")
    simai_output_subdir.mkdir(parents=True, exist_ok=True)

    latency_dirs = sorted(
        [d for d in workLoadInput_dir.iterdir() if d.is_dir() and re.match(r'latency\d+', d.name, re.IGNORECASE)],
        key=lambda x: extract_latency_from_path(x)
    )

    if not latency_dirs:
        print(f"警告: 在 {workLoadInput_dir} 中未找到任何 latencyXXX 子目录")
        return

    for latency_dir in latency_dirs:
        latency = extract_latency_from_path(latency_dir)
        print(f"\n--- 处理 latency={latency} ---")

        workload_files = sorted(latency_dir.glob("*.txt"))
        if not workload_files:
            print(f"⚠️  跳过 {latency_dir}：无 .txt 文件")
            continue

        print(f"📁 发现 {len(workload_files)} 个 workload 文件")

        for workload_file in workload_files:
            print(f"\n  → 处理文件: {workload_file.name}")

            # 提取 tp, pp, ep
            tp, pp, ep = extract_tp_pp_ep(workload_file.name)
            r_prefix = f"qwen3moe_ep{ep}_tp{tp}_pp{pp}_latency{latency}_"

            out_subdir = output_dir / f"latency{latency}"
            out_subdir.mkdir(exist_ok=True)
            log_file = out_subdir / f"simai_run_ep{ep}_tp{tp}_pp{pp}.log"

            cmd = [
                str(simai_bin),
                "-w", str(workload_file),
                "-g", str(args.num_gpus),
                "-nv", str(args.nvlink_bandwidth),
                "-nic", str(args.nic_bandwidth),
                "-n_p_s", str(args.nodes_per_switch),
                "-g_p_s", str(args.gpus_per_node),
                "-r", r_prefix
            ]

            print(f"  命令: {' '.join(cmd)}")

            # 清理旧输出（防止残留）
            for old_file in simai_output_subdir.glob(f"{r_prefix}*"):
                old_file.unlink()

            # 执行 SimAI
            with open(log_file, 'w') as f:
                result = subprocess.run(cmd, cwd=str(cwd), stdout=f, stderr=subprocess.STDOUT, text=True)

            if result.returncode != 0:
                print(f"❌ SimAI 失败 (ep{ep}, tp{tp}, pp{pp})，退出码 {result.returncode}")
                print(f"   日志: {log_file}")
                exit(1)

            # ⏳ 等待文件生成（最多 5 秒）
            max_wait = 5
            found_files = []
            for _ in range(max_wait * 2):  # 每 0.5 秒检查一次
                found_files = list(simai_output_subdir.glob(f"{r_prefix}*"))
                if found_files:
                    break
                time.sleep(0.5)

            if not found_files:
                print(f"❌ 错误: 运行成功但未在 {simai_output_subdir} 中找到 {r_prefix}* 文件！")
                print(f"   该目录当前内容: {[f.name for f in simai_output_subdir.iterdir()] if simai_output_subdir.exists() else '空'}")
                exit(1)

            # 移动文件
            moved = 0
            for src in found_files:
                dst = out_subdir / src.name
                shutil.move(str(src), str(dst))
                moved += 1
                print(f"    📤 移动: {src.name} → {out_subdir}")

            print(f"  ✅ 成功完成 (ep{ep}, tp{tp}, pp{pp})，移动 {moved} 个文件")

    print("\n🎉 所有 SimAI 分析任务完成！")

if __name__ == "__main__":
    main()
