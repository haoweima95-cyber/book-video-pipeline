---
name: img-to-video
description: |
  PNG 图片批量转 10 秒放大 MP4 视频。默认 1920x1080，缓慢放大特效。
  触发方式：/img-to-video、/图片转视频
---
# Img to Video：图片转放大视频

```bash
python main.py <图片文件夹> [输出文件夹] [--speed 0.5]
```

| 参数 | 说明 | 默认 |
|------|------|------|
| `--speed` | 缩放速度倍率 | 1.0（0.5=慢一半） |

默认输出到同目录 `_video` 子文件夹。
