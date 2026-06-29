#!/usr/bin/env python3
"""
segment-concat: 片段拼接
将 segments/ 目录下所有 seg_*.mp4 按序号拼接为完整视频。
"""

import sys, os, re, subprocess
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# ── 统一 config 导入 ──
_PIPELINE_SRC = Path.home() / ".claude" / "skills" / "book-video-pipeline" / "src"
if str(_PIPELINE_SRC) not in sys.path:
    sys.path.insert(0, str(_PIPELINE_SRC))


def _get_output_dir():
    try:
        from config import load as load_config
        cfg = load_config()
        if cfg and cfg.get("paths", {}).get("output_dir"):
            return cfg["paths"]["output_dir"]
    except Exception:
        pass
    return os.path.join(os.environ.get("HOMEDRIVE", "D:") + "\\", "自媒体", "视频导出")


def concat(segments_dir, output_path=None, pattern=r"seg_(\d+)"):
    seg_dir = os.path.abspath(segments_dir)
    seg_files = sorted(
        [f for f in os.listdir(seg_dir) if re.search(pattern + r"\.mp4$", f)],
        key=lambda x: int(re.search(pattern, x).group(1))
    )
    if not seg_files:
        print(f"未在 {seg_dir} 找到匹配 {pattern} 的 mp4 文件")
        return
    if output_path is None:
        proj_dir = os.path.dirname(os.path.dirname(seg_dir))
        proj_name = os.path.basename(proj_dir)
        out_dir = _get_output_dir()
        os.makedirs(out_dir, exist_ok=True)
        output_path = os.path.join(out_dir, f"{proj_name}.mp4")
    output_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    list_path = os.path.join(seg_dir, "_concat.txt")
    with open(list_path, "w", encoding="utf-8") as f:
        for sf in seg_files:
            f.write(f"file '{sf}'\n")

    print(f"拼接 {len(seg_files)} 个片段...")
    for i, sf in enumerate(seg_files):
        size = os.path.getsize(os.path.join(seg_dir, sf)) / 1024 / 1024
        print(f"  {i+1}. {sf} ({size:.1f}MB)")

    orig_cwd = os.getcwd()
    os.chdir(seg_dir)
    try:
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", list_path, "-c", "copy", output_path
        ], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    finally:
        os.chdir(orig_cwd)
    os.remove(list_path)
    total_mb = os.path.getsize(output_path) / 1024 / 1024
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", output_path],
        capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    total_s = float(r.stdout.strip())
    print(f"拼接完成: {output_path} ({total_mb:.1f}MB, {total_s:.0f}s)")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="片段拼接工具")
    parser.add_argument("segments_dir")
    parser.add_argument("--output", "-o", default=None)
    parser.add_argument("--pattern", "-p", default=r"seg_(\d+)")
    args = parser.parse_args()
    concat(args.segments_dir, args.output, args.pattern)
