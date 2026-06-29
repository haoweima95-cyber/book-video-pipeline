#!/usr/bin/env python3
"""
PNG → MP4 — 图片转缓慢放大视频。
默认 10 秒，zoompan 从 1.0 放大到 1.08（缓慢呼吸感）。
--speed 控制缩放速度（默认 1.0，0.5 = 慢一半）。
"""
import sys, subprocess
from pathlib import Path

SEC = 10
ZOOM_SPEED = 0.0003  # 基准速度（per frame at 30fps，speed=1.0 时 10s 从 1.0→1.08）


def png_to_mp4(png_path: str, mp4_path: str, speed: float = 1.0):
    zoom = ZOOM_SPEED * speed
    subprocess.run([
        "ffmpeg", "-y", "-loop", "1", "-i", png_path,
        "-vf", f"scale=1920:1080:force_original_aspect_ratio=decrease,"
               f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,"
               f"zoompan=z='min(zoom+{zoom},1.08)':d={SEC*30}:s=1920x1080",
        "-c:v", "libx264", "-t", str(SEC), "-pix_fmt", "yuv420p",
        mp4_path,
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def batch_convert(img_dir: str, out_dir: str = None, speed: float = 1.0):
    img_dir = Path(img_dir)
    if out_dir is None:
        out_dir = img_dir.parent / f"{img_dir.name}_video"
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    pngs = sorted(img_dir.glob("*.png"))
    for f in pngs:
        mp4 = out_dir / f"{f.stem}.mp4"
        if mp4.exists():
            continue
        print(f"  {f.name} -> {mp4.name}")
        png_to_mp4(str(f), str(mp4), speed)
    print(f"Done: {len(pngs)} files -> {out_dir}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <图片文件夹> [输出文件夹] [--speed 1.0]")
        print("  --speed  缩放速度倍率，默认 1.0，0.5 = 慢一半")
        sys.exit(1)

    img_dir = sys.argv[1]
    out_dir = None
    speed = 1.0

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--speed" and i + 1 < len(sys.argv):
            speed = float(sys.argv[i + 1])
            i += 2
        elif not sys.argv[i].startswith("--") and out_dir is None:
            out_dir = sys.argv[i]
            i += 1
        else:
            i += 1

    batch_convert(img_dir, out_dir, speed)
