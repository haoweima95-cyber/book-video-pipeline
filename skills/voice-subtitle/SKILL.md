---
name: voice-subtitle
description: |
  配音 + 字幕生成。为逐行 txt 生成 CosyVoice2 配音 WAV 和分段 ASS 字幕。
  默认字幕样式：SimHei 50px 加粗，纯黑描边 3px，无阴影，底部居中，
  按标点逐句分段，自动清理句末标点（保留问号引号）。
  触发方式：/voice-subtitle、/配音字幕、"生成配音字幕"
---

# voice-subtitle：配音 + 字幕生成

## 使用方式

### 1. 克隆音色（首次）

```bash
python main.py clone 音色名 "ref.wav" "参考文本"
```

### 2. 生成配音+字幕

```bash
# 单文件
python main.py gen 1.txt

# 批量
python main.py gen-batch script/

# 批量（只处理指定文件，号数分隔，支持范围）
python main.py gen-batch script/ --files "1,3,5-8"
```

输出到 txt 同目录的 `voice_output/`：

```
voice_output/
├── 1. 前20字.wav      # 配音
├── 1. 前20字.ass      # ASS 分段字幕
├── 2. 前20字.wav
├── 2. 前20字.ass
...
```

### 3. 管理

```bash
python main.py list          # 列出音色
python main.py delete 名      # 删除音色
python main.py defaults      # 查看默认参数
```

## 默认参数（当前最优配置）

| 参数 | 值 |
|------|-----|
| 字幕字体 | SimHei 50px 加粗 |
| 字色 | 纯白 `&H00FFFFFF` |
| 描边 | 3px 纯黑 `&H00000000` |
| 阴影 | 无 |
| 对齐 | 底部居中，距底 80px |
| 分段 | 按标点逐句展示 |
| 清理 | 句末逗号句号不显示，问号引号书名号保留 |
| 每行字数 | ≤25 字自动换行 |
| 配音模型 | CosyVoice2-0.5B (CPU), speed=1.1 |
