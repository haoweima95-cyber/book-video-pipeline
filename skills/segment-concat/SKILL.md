---
name: segment-concat
description: |
  将 segments/ 目录下所有 seg_*.mp4 片段按序号拼接为完整视频。
  用于 /voice-subtitle → /video-compose 流程的最后一步。
  触发方式：/segment-concat、/拼接、"拼接片段""合成完整视频"
---

# segment-concat：片段拼接

## 使用方式

```bash
# 默认输出到 D:\自媒体\视频导出\<项目名>_final.mp4
python main.py segments/

# 指定输出路径
python main.py segments/ -o 成片.mp4
```

## 输出

```
D:\自媒体\视频导出\<项目名>.mp4    （h264 copy，无损拼接）
```

项目名从 segments 路径自动推断（segments 目录往上两级）。

## 工作流位置

```
/voice-subtitle  →  /video-compose  →  /segment-concat
   配音+字幕           合成片段              拼接成片
```
