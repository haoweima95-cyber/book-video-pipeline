---
name: book-video-pipeline
description: |
  一站式读书视频生成流水线：从书名到成片，自动完成文案→生图→配音→合成。
  /book-video-pipeline、/读书视频、"做读书视频""生成读书视频"
---

# 📖 读书视频生成流水线

从书名到成片，一条龙生成读书口播短视频。每个步骤委托给对应的独立 skill。

## 架构

```
book-video-pipeline/          ← 编排 + 配置 + 种子数据
├── SKILL.md                  ← 本文件：纯编排指令
├── config.yaml               ← 唯一配置，所有 skill 从这里读
├── config.example.yaml
├── init.py
├── src/config.py             ← 唯一 Python：配置加载器
├── seed/samples/             ← 种子范本（script-gen 质量基准）
└── seed/voice/               ← 默认音色

skills/text-sentence/         ← 独立 skill（代码 + 指令合一）
skills/sd-image-gen/
skills/voice-subtitle/
...                            ← 每个 skill 有且只有一份 main.py + SKILL.md
```

## 初始化

每次加载本 skill 时，先检测 `config.yaml` 是否存在。如果不存在（新安装），按以下清单逐项引导。

### 检查清单

按顺序执行，一项确认后再下一项：

**1. 环境检查**
```bash
python --version && ffmpeg -version
```
需要 Python 3.10+ 和 ffmpeg 在 PATH 中。

**2. 安装 pip 依赖**
```bash
pip install -r requirements.txt
```

**3. API Key**
检查 `~/.claude/settings.json` 的 `env.IMAGE_API_KEY` 是否设置。未设置则指导用户去 [cloud.siliconflow.cn](https://cloud.siliconflow.cn) 获取。

**4. config.yaml**
```bash
cp config.example.yaml config.yaml
```
按用户环境修改 `paths.project_root`、`paths.output_dir`、`image.base_url`、`tts.provider`。

**5. CosyVoice（可选，仅本地配音）**
```bash
setup.bat
```
下载 5.3GB 模型，需良好网络。

**6. 知识库（可选）**
告知：`/script-gen` 需要 `~/kb/book-scripts/`，无则文案质量受限。

### 全部通过后

```
初始化完成: Python ✅ ffmpeg ✅ 依赖 ✅ API Key ✅ config ✅
试试: /book-video-pipeline start <书名>
```

## 命令

### start <书名> — 完整流程

```
Step 1: 建项目文件夹
  mkdir -p "<project_root>/<书名>/images/"
  mkdir -p "<project_root>/<书名>/images_video/"
  mkdir -p "<project_root>/<书名>/script/"

Step 2: 生成口播文案 + 断句 + 合并拆分
  Skill("script-gen", "<书名>")
  （script-gen 内部完成: 生成文案 → --sentences 断句 → --merge 合并拆分 → 视频简介）
  输出: <书名>/<书名>口播文案.txt + <书名>/视频简介与分段.txt

Step 3: ⏸️ 用户审阅修改文案（必须等待确认，不可跳过）

Step 4: 拆分单句
  python <text-split>/main.py "文案.txt" --split               → script/N.txt

Step 5: 生成生图提示词
  Skill("txt-to-prompt")                                       → 文案_prompt.txt

Step 6: 生成图片
  grep "^[a-z]" *_prompt.txt > prompts_only.txt                ← 从交错文件中提取纯 prompt
  python <sd-image-gen>/main.py -f "prompts_only.txt" -o images/

Step 7: 图片转视频
  python <img-to-video>/main.py images/ images_video/

Step 8: 生成配音字幕
  python <voice-subtitle>/main.py gen-batch script/
  # 或只处理指定文件: python <voice-subtitle>/main.py gen-batch script/ --files "1,3,5-8"

Step 9: 合成片段
  python <video-compose>/main.py batch script/ images_video/

Step 10: 拼接成片
  python <segment-concat>/main.py script/segments/

Step 11: 整理写作经验
  Skill("writing-feedback")
```

### script <书名> — 仅生成文案（Step 1-3）

执行 `start` 流程的 Step 1 到 Step 3，用户审阅后停止。

### video <项目目录> — 配音+合成+拼接（Step 8-10）

从已有 `script/N.txt` 和 `images_video/` 开始，执行 Step 8-10。

### voice clone <名称> <参考音频> <参考文本> — 克隆自定义音色

```bash
python <voice-subtitle>/main.py clone "<名称>" "<参考音频路径>" "<参考文本>"
```

### config — 查看/修改配置

查看当前配置：
```bash
python src/config.py
```
或直接编辑 `config.yaml`。

## 项目结构

```
<project_root>/<书名>/
├── <书名>口播文案.txt       ← 逐行文案（可编辑）
├── 视频简介与分段.txt        ← 标题+简介+标签+封面
├── images/                  ← AI 生图
├── images_video/            ← 缩放视频
└── script/
    ├── N.txt                ← 逐句拆分
    ├── voice_output/        ← WAV + ASS
    └── segments/            ← 合成 MP4
```

成片输出到 `<output_dir>/<书名>.mp4`。

## 依赖

Python 3.10+, ffmpeg, SiliconFlow API key, CosyVoice（本地配音）
