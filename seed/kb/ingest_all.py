"""批量 ingest：为 raw/ 每篇文案创建 wiki/sources/ 页面。"""
import os, re, json
from pathlib import Path
from datetime import datetime

KB = Path(os.path.expanduser("~/kb/book-scripts"))
RAW = KB / "raw"
SRC = KB / "wiki" / "sources"

SRC.mkdir(parents=True, exist_ok=True)
today = datetime.now().strftime("%Y-%m-%d")

# --- Helper: extract book name from garbled filename ---
# These are already in git as raw bytes, so pathlib reads them correctly
# The filename looks like: 《书名》高赞文案.txt or 《书名》口播文案.txt

files = sorted(RAW.glob("*.txt"))
print(f"Found {len(files)} source files\n")

created = []
for fp in files:
    raw_name = fp.stem  # without .txt
    # Try to extract book name between 《》
    m = re.search(r'《(.+?)》', raw_name)
    book_name = m.group(1) if m else raw_name[:30]

    text = fp.read_text(encoding="utf-8")
    chars = len(text.replace("\n", "").replace(" ", ""))
    lines = [l for l in text.splitlines() if l.strip()]

    # Estimate structure sections based on content markers
    has_question_open = any("你有没有" in l or "你知道吗" in l for l in lines[:3])
    has_book_intro = any("今天我要" in l or "带你走进" in l or "推荐" in l for l in lines[:10])

    # Extract first and last few sentences for structure analysis
    first_3 = lines[:3] if len(lines) >= 3 else lines
    last_2 = lines[-2:] if len(lines) >= 2 else lines

    # --- Create source page ---
    slug = re.sub(r'[^\w一-鿿\-　-〿＀-￯]', '', book_name)[:30]
    md_name = f"{slug}.md"

    frontmatter = f"""---
title: "《{book_name}》"
type: source
date: {today}
tags: [读书文案, 口播]
source_file: "raw/{fp.name}"
word_count: {chars}
---
"""

    body = f"""# 《{book_name}》高赞文案

**来源文件**: `raw/{fp.name}`
**字数**: {chars:,} 字
**录入日期**: {today}

## 书籍概要

{book_name}相关的高赞口播文案。

## 文案结构

- **开头方式**: {"反问式钩子" if has_question_open else "叙述式引入"}
- **书籍引入**: {"有" if has_book_intro else "无"}明确的书籍推荐过渡
- **总句数**: {len(lines)} 句
- **首句**: {first_3[0][:80] if first_3 else ''}
- **尾句**: {last_2[-1][:80] if last_2 else ''}

## 核心观点

（待补充：阅读原文后提取主要论点）

## 表达技法

（待补充：分析开头、过渡、论证、结尾的写作技巧）

## 金句摘录

（待补充：最具传播力的几句话）

---

## 相关链接

- 待关联实体和综述页面
"""

    md_path = SRC / md_name
    md_path.write_text(frontmatter + body, encoding="utf-8")
    created.append({"book": book_name, "file": md_name, "chars": chars, "lines": len(lines)})
    print(f"  [{len(created):>2}] {book_name} ({chars}字, {len(lines)}句)")

# --- Update index.md ---
idx_path = KB / "index.md"
idx_content = idx_path.read_text(encoding="utf-8")
# Add source links if not already present
source_links = "\n".join(f"- [{c['book']}](wiki/sources/{c['file']}): {c['chars']}字口播文案" for c in created)
new_section = f"\n## 来源页面 ({len(created)} 篇)\n\n{source_links}\n"

if "## 来源页面" not in idx_content:
    idx_content += new_section
else:
    # Replace existing section
    idx_content = re.sub(r'## 来源页面.*?(?=\n## |\Z)', new_section.rstrip(), idx_content, flags=re.DOTALL)

idx_path.write_text(idx_content, encoding="utf-8")

# --- Update log.md ---
log_path = KB / "log.md"
with open(log_path, "a", encoding="utf-8") as f:
    f.write(f"\n## {today} - 批量 ingest\n")
    f.write(f"- 录入 {len(created)} 篇来源页面\n")
    for c in created:
        f.write(f"  - 《{c['book']}》({c['chars']}字, {c['lines']}句)\n")

print(f"\nDone: {len(created)} source pages created")
print(f"Output: {SRC}")
