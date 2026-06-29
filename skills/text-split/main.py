#!/usr/bin/env python3
"""
文案处理 — SRT 字幕 / 拆分文件。
默认生成 SRT，--split 拆为独立 txt。
"""
import sys
import re
from pathlib import Path


def read_lines(txt_path: str) -> list[str]:
    src = Path(txt_path)
    if not src.exists():
        raise FileNotFoundError(f"文件不存在: {txt_path}")
    lines = [l.strip() for l in src.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not lines:
        raise ValueError("文件无有效内容")
    return lines


def estimate_duration(text: str, cps: float = 4.0, min_sec: float = 2.0, max_sec: float = 10.0) -> float:
    chinese_chars = len(re.findall(r'[一-鿿　-〿＀-￯]', text))
    english_words = len(re.findall(r'[a-zA-Z]+', text))
    effective_chars = chinese_chars + english_words * 2
    duration = effective_chars / cps
    return max(min_sec, min(duration, max_sec))


def format_timestamp(total_seconds: float) -> str:
    h = int(total_seconds // 3600)
    m = int((total_seconds % 3600) // 60)
    s = int(total_seconds % 60)
    ms = int((total_seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def txt_to_srt(txt_path: str) -> str:
    src = Path(txt_path)
    lines = read_lines(txt_path)
    out_path = src.parent / f"{src.stem}.srt"
    total = 0.0
    blocks = []
    for i, line in enumerate(lines, 1):
        dur = estimate_duration(line)
        start, end = total, total + dur
        total = end
        blocks.append(f"{i}\n{format_timestamp(start)} --> {format_timestamp(end)}\n{line}\n")
    out_path.write_text("\n".join(blocks), encoding="utf-8")
    print(f"Done: {len(blocks)} subtitles -> {out_path}")
    print(f"Total duration: {format_timestamp(total)}")
    return str(out_path)


def txt_to_split(txt_path: str, merge_last: bool = True) -> str:
    src = Path(txt_path)
    lines = read_lines(txt_path)
    out_dir = src.parent / "script"
    out_dir.mkdir(exist_ok=True)

    # 结语合并到前面一句：最后两行合并为一行
    if merge_last and len(lines) >= 2:
        lines[-2] = lines[-2] + "……" + lines[-1]
        lines = lines[:-1]

    for i, line in enumerate(lines, 1):
        (out_dir / f"{i}.txt").write_text(line, encoding="utf-8")
    print(f"Done: {len(lines)} files -> {out_dir}")
    return str(out_dir)



if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <文案.txt> [--split]")
        print("  --srt    生成 SRT 字幕（默认）")
        print("  --split  拆分为独立 1.txt, 2.txt ...")
        sys.exit(1)

    path = sys.argv[1]
    mode = "srt"
    if len(sys.argv) > 2 and sys.argv[2] == "--split":
        mode = "split"

    if mode == "split":
        txt_to_split(path)
    else:
        txt_to_srt(path)
