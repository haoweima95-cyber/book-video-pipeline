---
name: sd-image-gen
description: |
  使用 SiliconFlow API + Tongyi-MAI/Z-Image-Turbo 生成图片。
  支持单张、多张、批量模式。
  触发方式：/sd、/生图、"生成图片""AI画图"
---

# SD Image Gen：AI 图片生成

调用 SiliconFlow 国际版 API，使用 `Tongyi-MAI/Z-Image-Turbo` 模型生成图片。6 秒出图。

---

## 触发信号

- 要求生成图片 / AI 画图
- 使用 `/sd`、`/生图` 命令
- "帮我生成一张..."

---

## 使用方式

```bash
python main.py "<提示词>" [参数]
```

> ⚠️ **Windows 下必须带 `PYTHONIOENCODING=utf-8`**，否则 emoji 报 GBK 编码错误：
> ```bash
> PYTHONIOENCODING=utf-8 python main.py "一只橘猫在窗台上晒太阳"
> ```

### 单张生成

```bash
PYTHONIOENCODING=utf-8 python main.py "一只橘猫在窗台上晒太阳"
PYTHONIOENCODING=utf-8 python main.py "赛博朋克城市夜景" -o cyberpunk.png
```

### 多张生成（同提示词）

```bash
PYTHONIOENCODING=utf-8 python main.py "水墨山水" -n 4 -o ./output/
```

### 批量生成（从文件）

```bash
PYTHONIOENCODING=utf-8 python main.py -f prompts_only.txt -o ./images/
```

`prompts_only.txt` 每行一个英文提示词，`#` 开头为注释。

> ⚠️ **`prompts_only.txt` 必须在项目根目录，与文案同级。** 不要放进 `images/`。如果上游 txt-to-prompt 生成的是中英对照版（`_prompt.txt`），提取纯英文行到 `_prompts_only.txt`：
> ```bash
> grep "^[a-z]" *_prompt.txt > *_prompts_only.txt
> ```

### 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `prompt` | 提示词 | 必填 |
| `-n` | 生成数量 | 1 |
| `-s` | 尺寸 | 1024x1024 |
| `-o` | 输出路径 | 自动命名 |
| `-m` | 模型 | Tongyi-MAI/Z-Image-Turbo |
| `-f` | 批量文件 | — |
| `--list-models` | 列出可用模型 | — |

---

## Prompt 禁忌

禁止以下意象，违者不生成：

- **人体器官（大脑、心脏、眼球等解剖结构）** — 一律用意象替代（如"发光的灯笼""指南针""灯塔"代表直觉/思考，"暖流""火焰"代表情绪）
- **人体骨骼、骷髅、头骨** — 考古/古生物/医学场景也不行
- **裸体、裸露人体轮廓、半裸** — 人物必须着衣
- **血腥暴力** — 血液、伤口、武器攻击、处决、战争场面
- **恐怖诡异** — 鬼怪、惊悚、畸形、令人不安的超现实
- **阴暗反社会** — 绝望、自残、反人类、反社会暗示

所有意象必须正向、健康、阳光。场景用自然景物或建筑器物替代（如"倒塌的城墙""风吹过的荒野""对峙的剪影"）。

## 输出

图片保存为 PNG 格式。自动命名规则：`时间戳_提示词前20字.png`。

---

## 所需权限

- `Bash` — 运行 Python 脚本
- 网络 — 调用 SiliconFlow API
- `Write` — 保存图片文件
