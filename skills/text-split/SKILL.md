---
name: text-split
description: |
  ⚠️ 仅处理纯文本：逐行 txt → SRT 字幕 或 拆分为独立 txt。
  不涉及视频、不生成剪映草稿。视频+文本配对请用 video-text-to-jianying。
  默认输出 SRT，--split 模式存为 1.txt, 2.txt ...
  触发方式：/text-split、/拆分文案、/文案拆分
---

# Text Split：文案处理（纯文本，不涉及视频）

⚠️ **本 skill 只处理文本。** 如需视频+文本配对生成剪映草稿，请用 `/video-text-to-jianying`。如需按句末标点拆为逐行，请用 `/text-sentence`。

读取逐行 txt，支持两种模式：

## SRT 字幕模式（默认）

每行 → 一条字幕，自动估算时长。

```bash
python main.py 文案.txt
```

- 中文语速约 4 字/秒，最少 2 秒，最多 10 秒
- 输出 `原文名.srt`，可直接导入剪映

## 拆句模式

每行 → `1.txt`, `2.txt` ...，保存到 `script/` 子目录。

```bash
python main.py 文案.txt --split
```

- 用于剪映 AI 配音等需要独立文件的场景
- 输出到原文同目录 `script/` 文件夹

### 结语合并规则

源文件的最后一行如果是结语（匹配"感谢…观看/下本书/再见"），会自动合并到倒数第二行的文件末尾。

- 源文件 N 行 → 拆分后 N-1 个文件（结语不单独成文件）
- 例：源文件 42 行，第 42 行是"感谢你的观看，我们下本书再见。"→ 拆分出 1.txt ~ 41.txt，其中 41.txt 的内容是第 41 行 + 第 42 行拼接
- 与 txt-to-prompt 的配合：txt-to-prompt 跳过结语不生成 prompt（生成 N-1 条 prompt），text-split 把结语合并进最后一个文件（生成 N-1 个文件），图片与 split 文件一一对应

## 所需权限

- `Read` — 读取 txt
- `Write` — 写入 srt / txt
- `Bash` — 运行 python
