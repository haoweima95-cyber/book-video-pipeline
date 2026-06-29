#!/usr/bin/env python3
"""
按句末标点拆为逐行 — 原地覆盖原文件。

两种模式：
  --sentences  纯按句末标点断句（。！？；……），不做合并/拆分，供审阅
  --merge      合并短句(≤60字) + 拆分长句(>60字) + 结语保护，审阅后执行
"""

import sys
import re
from pathlib import Path

MAX_CHARS = 60  # 每行目标最大字符数

# 合适的长句切分点（优先级从高到低）
SPLIT_PUNCT = ["，", "；", "：", "、", ","]


def _split_long_line(line: str) -> list[str]:
    """把超过 MAX_CHARS 的行在合适标点处切成多段。"""
    if len(line) <= MAX_CHARS:
        return [line]

    parts = []
    remaining = line
    while len(remaining) > MAX_CHARS:
        cut = -1
        window = remaining[:MAX_CHARS]
        for i in range(len(window) - 1, MAX_CHARS // 2, -1):
            if window[i] in SPLIT_PUNCT:
                cut = i + 1
                break
        if cut == -1:
            cut = MAX_CHARS
        parts.append(remaining[:cut])
        remaining = remaining[cut:].lstrip()

    if remaining:
        parts.append(remaining)
    return parts


def _merge_short(lines: list[str]) -> list[str]:
    """贪心合并短行：buffer + 下一行 ≤ MAX_CHARS 就合并。"""
    if not lines:
        return lines

    merged = []
    buf = ""
    for line in lines:
        if not line:
            if buf:
                merged.extend(_split_long_line(buf))
                buf = ""
            merged.append(line)
            continue

        if not buf:
            buf = line
        elif len(buf) + len(line) <= MAX_CHARS:
            buf += line
        else:
            merged.extend(_split_long_line(buf))
            buf = line

    if buf:
        merged.extend(_split_long_line(buf))
    return merged


def _pure_split(text: str) -> list[str]:
    """纯按句末标点断句，不做合并/拆分。"""
    text = re.sub(r'([。！？；])([」』"》）\)]?)', r'\1\2\n', text)
    text = re.sub(r'(……)(?=\S)', r'\1\n', text)
    return [l.strip() for l in text.splitlines() if l.strip()]


def _merge_mode_split(text: str) -> list[str]:
    """断句 + 合并短行 + 拆分长行 + 结语保护。"""
    text = re.sub(r'([。！？；])([」』"》）\)]?)', r'\1\2\n', text)
    text = re.sub(r'(……)(?=\S)', r'\1\n', text)

    lines = [l.strip() for l in text.splitlines() if l.strip()]

    CLOSING = "感谢你的观看，我们下本书再见。"
    closing_lines = []
    body_lines = []
    for l in lines:
        if CLOSING in l:
            if l == CLOSING:
                closing_lines.append(l)
            else:
                body = l[:l.index(CLOSING)]
                if body.strip():
                    body_lines.append(body.strip())
                closing_lines.append(CLOSING)
        else:
            body_lines.append(l)

    return _merge_short(body_lines) + closing_lines


def txt_to_sentences(txt_path: str, mode: str = "sentences") -> str:
    src = Path(txt_path)
    if not src.exists():
        raise FileNotFoundError(f"文件不存在: {txt_path}")

    text = src.read_text(encoding="utf-8")

    if mode == "merge":
        lines = _merge_mode_split(text)
    else:
        lines = _pure_split(text)

    src.write_text("\n".join(lines) + "\n", encoding="utf-8")

    label = "pure split" if mode == "sentences" else "merge+split"
    print(f"Done ({label}): {len(lines)} lines -> {src}")
    return str(src)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python main.py <文案.txt> --sentences  纯按标点断句，供审阅")
        print("  python main.py <文案.txt> --merge      合并短句(≤60字)+拆分长行(>60字)")
        sys.exit(1)

    path = sys.argv[1]
    mode = "sentences"
    if len(sys.argv) > 2 and sys.argv[2] == "--merge":
        mode = "merge"

    txt_to_sentences(path, mode)
