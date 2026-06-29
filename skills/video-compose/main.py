#!/usr/bin/env python3
"""
video-compose: 视频 + 音频 + 字幕 → 成品片段
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

DEFAULTS = {"vcodec": "libx264", "crf": 22, "preset": "fast", "acodec": "aac", "abitrate": "192k"}


def _get_font_path():
    try:
        from config import load as load_config
        cfg = load_config()
        if cfg and cfg.get("paths", {}).get("font_path"):
            p = cfg["paths"]["font_path"]
            if os.path.exists(p):
                return p.replace("\\", "/").replace(":", "\\:")
    except Exception:
        pass
    sys_font = "C\\:/Windows/Fonts/simhei.ttf"
    if os.path.exists("C:/Windows/Fonts/simhei.ttf"):
        return sys_font
    pkg_font = os.path.join(os.path.dirname(__file__), "..", "fonts", "SIMHEI.TTF")
    pkg_font = os.path.abspath(pkg_font)
    if os.path.exists(pkg_font):
        return pkg_font.replace("\\", "/").replace(":", "\\:")
    return sys_font


def compose(video_path, wav_path, ass_path=None, subtitle_text=None,
            output_path=None, duration=None):
    if duration is None:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", wav_path],
            capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        duration = float(r.stdout.strip())
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", video_path],
        capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    video_dur = float(r.stdout.strip())
    tpad_filter = ""
    if duration > video_dur:
        gap = duration - video_dur + 0.5
        tpad_filter = f",tpad=stop_mode=clone:stop_duration={gap:.3f}"
    if output_path is None:
        out_dir = os.path.dirname(wav_path)
        basename = os.path.splitext(os.path.basename(wav_path))[0]
        output_path = os.path.join(out_dir, f"{basename}_composed.mp4")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    if ass_path and os.path.exists(ass_path):
        video_abs = os.path.abspath(video_path)
        wav_abs = os.path.abspath(wav_path)
        abs_output = os.path.abspath(output_path)
        ass_dir = os.path.dirname(os.path.abspath(ass_path))
        ass_name = os.path.basename(ass_path)
        orig_cwd = os.getcwd()
        os.chdir(ass_dir)
        try:
            cmd = ["ffmpeg", "-y", "-i", video_abs, "-i", wav_abs, "-t", str(duration)]
            cmd += ["-vf", f"scale=1920:1080,ass={ass_name}{tpad_filter}"]
            cmd += ["-map", "0:v:0", "-map", "1:a:0",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                    "-c:a", "aac", "-b:a", "192k", abs_output]
            subprocess.run(cmd, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        finally:
            os.chdir(orig_cwd)
    elif subtitle_text:
        font_path = _get_font_path()
        safe_text = subtitle_text.replace(":", "\\:").replace("\\", "/").replace("'", "\\'")
        cmd = ["ffmpeg", "-y", "-i", video_path, "-i", wav_path, "-t", str(duration)]
        cmd += ["-vf", (
            f"drawtext=fontfile={font_path}:"
            f"text='{safe_text}':"
            f"fontsize=44:fontcolor=white:borderw=3:bordercolor=black:"
            f"x=(w-text_w)/2:y=h-text_h-80{tpad_filter}"
        )]
        cmd += ["-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                "-c:a", "aac", "-b:a", "192k", output_path]
        subprocess.run(cmd, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        cmd = ["ffmpeg", "-y", "-i", video_path, "-i", wav_path, "-t", str(duration)]
        if tpad_filter:
            cmd += ["-vf", f"scale=1920:1080{tpad_filter}"]
        cmd += ["-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                "-c:a", "aac", "-b:a", "192k", output_path]
        subprocess.run(cmd, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    size_mb = os.path.getsize(output_path) / 1024 / 1024
    print(f"  → {os.path.basename(output_path)} ({size_mb:.1f}MB, {duration:.1f}s)")
    return output_path


def _find_wav_ass(voice_dir, idx):
    wav_path = ass_path = None
    if not os.path.exists(voice_dir):
        return None, None
    for f in os.listdir(voice_dir):
        if f.startswith(f"{idx}. "):
            full = os.path.join(voice_dir, f)
            if f.endswith(".wav"):
                wav_path = full
            elif f.endswith(".ass"):
                ass_path = full
    return wav_path, ass_path


def batch_compose(txt_dir, video_dir):
    txt_files = sorted(
        [f for f in os.listdir(txt_dir) if f.endswith(".txt") and f.split(".")[0].isdigit()],
        key=lambda x: int(x.rsplit(".", 1)[0])
    )
    video_files = sorted(
        [f for f in os.listdir(video_dir) if f.endswith(".mp4")],
        key=lambda x: int(x.split("_")[0]) if x.split("_")[0].isdigit() else 0
    )
    if not txt_files:
        print("未找到编号 txt 文件")
        return []
    print(f"批量合成 {len(txt_files)} 个片段...")
    voice_dir = os.path.join(txt_dir, "voice_output")
    out_dir = os.path.join(txt_dir, "segments")
    os.makedirs(out_dir, exist_ok=True)
    results, skipped = [], 0
    for i, tf in enumerate(txt_files):
        if i >= len(video_files):
            skipped += 1
            continue
        idx = int(tf.rsplit(".", 1)[0])
        video_path = os.path.join(video_dir, video_files[i])
        wav_path, ass_path = _find_wav_ass(voice_dir, idx)
        if wav_path is None or ass_path is None:
            skipped += 1
            continue
        out_path = os.path.join(out_dir, f"seg_{idx:03d}.mp4")
        try:
            compose(video_path, wav_path, ass_path, output_path=out_path)
            results.append(out_path)
        except Exception as e:
            print(f"  失败 {tf}: {e}")
            skipped += 1
    print(f"完成: {len(results)}/{len(txt_files)} 个片段" + (f"（跳过 {skipped} 个）" if skipped else ""))
    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="视频+音频+字幕合成")
    sub = parser.add_subparsers(dest="cmd")
    p_comp = sub.add_parser("compose", help="三文件合成")
    p_comp.add_argument("video")
    p_comp.add_argument("wav")
    p_comp.add_argument("ass", nargs="?", default=None)
    p_comp.add_argument("--output", "-o", default=None)
    p_batch = sub.add_parser("batch", help="批量配对合成")
    p_batch.add_argument("txt_dir")
    p_batch.add_argument("video_dir")
    sub.add_parser("defaults", help="显示默认参数")
    args = parser.parse_args()
    if args.cmd == "compose":
        compose(args.video, args.wav, args.ass, output_path=args.output)
    elif args.cmd == "batch":
        batch_compose(args.txt_dir, args.video_dir)
    elif args.cmd == "defaults":
        for k, v in DEFAULTS.items():
            print(f"  {k}: {v}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
