---
name: video-compose
description: |
  视频 + 音频 + ASS字幕 → 成品片段。将配音和字幕烧录到视频，裁切到音频长度。
  支持单文件合成、自动配对、批量合成。拼接请用 segment-concat。
  触发方式：/video-compose、/视频合成、"合成视频"
---

# video-compose：视频+音频+字幕合成

## 使用方式

### 1. 三文件合成

```bash
python main.py compose 视频.mp4 音频.wav 字幕.ass
```

### 2. 自动配对（推荐）

给定视频和 txt，自动查找 voice_output 下的 wav/ass 并合成：

```bash
python main.py auto 001_video.mp4 1.txt
```

### 3. 批量合成

```bash
python main.py batch script/ images_video/
```

自动配对：`1.txt + 001_*.mp4`, `2.txt + 002_*.mp4` ...
如果缺少配音/字幕，自动调用 voice-subtitle 生成。

### 4. 最终拼接

⚠️ 拼接不在本 skill 内，请使用 `segment-concat`：

```bash
python <segment-concat-dir>/main.py segments/
```

## 输出

- 单片：`segments/seg_001.mp4`（1920×1080, h264 + aac）
- 拼接：由 `segment-concat` 输出到上级目录 `final.mp4`

## ffmpeg 参数

| 参数 | 值 |
|------|-----|
| 视频编码 | libx264, CRF 22, preset fast |
| 音频编码 | aac 192k |
| 字幕方式 | ASS 滤镜烧录（硬字幕） |
