# 读书视频生成流水线

从书名到成片，一条龙生成读书口播短视频。

## 安装后必做

**1. 配置 API Key**

在 Claude Code 的 `settings.json`（`~/.claude/settings.json`）中设置环境变量：

```json
{
  "env": {
    "IMAGE_API_KEY": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  }
}
```

`config.yaml` 通过 `${IMAGE_API_KEY}` 引用，不会存明文。

**2. 安装依赖**

```bash
cd ~/.claude/skills/book-video-pipeline
pip install -r requirements.txt
```

**3. 如果需要本地 CosyVoice 配音（可选）**

```bash
setup.bat
```

会下载 5.3GB 模型并安装默认音色。不用本地配音可跳过——生图、视频合成等步骤不依赖 CosyVoice。

**4. 知识库（script-gen 依赖）**

`/script-gen` 需要 `~/kb/book-scripts/` 知识库才能生成高质量文案。没有的话联系作者获取，或用其他方式提供文案 txt。

---

## 系统要求

| 组件 | 必需 | 说明 |
|------|------|------|
| Python 3.10+ | ✅ | 推荐 3.12 |
| ffmpeg | ✅ | 添加到 PATH，`ffmpeg -version` 验证 |
| SiliconFlow API Key | ✅ | [cloud.siliconflow.cn](https://cloud.siliconflow.cn) 注册获取 |
| CosyVoice 模型 ~5.3GB | 可选 | 仅本地配音需要，云端配音无需 |

---

## 架构

```
book-video-pipeline/          ← 编排 + 配置 + 种子数据
├── SKILL.md                  ← 流水线编排指令
├── config.yaml               ← 唯一配置，所有 skill 从这里读
├── config.example.yaml
├── init.py                   ← 首次运行初始化向导
├── src/config.py             ← 唯一 Python 文件：配置加载器
├── seed/samples/             ← 种子范本（script-gen 质量基准）
├── seed/voice/               ← 默认音色
└── fonts/                    ← 备用字幕字体

skills/text-sentence/         ← 每个步骤是独立 skill，可单独调用
skills/text-split/
skills/script-gen/
skills/txt-to-prompt/
skills/sd-image-gen/          ← 从 pipeline config.yaml 读 API key
skills/img-to-video/
skills/voice-subtitle/        ← 从 pipeline config.yaml 读配音配置
skills/video-compose/
skills/segment-concat/
skills/writing-feedback/
```

每个 skill 有且只有一份 `main.py` + `SKILL.md`。pipeline 不重复存代码，只做编排。

---

## 使用

```
/book-video-pipeline start <书名>   完整流程：文案→生图→配音→成片
/book-video-pipeline script <书名>  仅文案生成（审阅后停止）
/book-video-pipeline video <项目>   从已有素材续跑：配音→成片
```

Step 3 是用户审阅阻断点，AI 会等你确认"改好了"才继续。你也可以单独调用每个 skill：

```
/script-gen <书名>      生成文案
/sd-image-gen           生图
/img-to-video           图片转视频
/voice-subtitle         配音+字幕
```

---

## 项目输出结构

```
D:\自媒体\<书名>\
├── <书名>口播文案.txt       ← 合并/拆分后的逐行文案
├── 视频简介与分段.txt        ← 标题 + 简介 + 标签
├── images/                  ← AI 生图 (001_xxx.png)
├── images_video/            ← 缩放视频 (001_xxx.mp4)
└── script/
    ├── 1.txt ... N.txt      ← 逐句拆分
    ├── voice_output/        ← WAV + ASS 配音字幕
    └── segments/            ← 合成片段 (seg_001.mp4)
```

成片输出到 `config.yaml` 中 `paths.output_dir`（默认 `D:\自媒体\视频导出\<书名>.mp4`）。

---

## 常见问题

**Q: 提示 "API key 为空"**
A: 检查 `settings.json` → `env.IMAGE_API_KEY` 是否设置。新开窗口后该环境变量才会生效。

**Q: 图片生成失败**
A: 检查 SiliconFlow 账户余额。可以先用 `python skills/sd-image-gen/main.py --list-models` 测试连通性。

**Q: CosyVoice 合成失败**
A: 确保 `~/.cosyvoice/voices/` 下至少有一个音色。`python skills/voice-subtitle/main.py list` 查看。

**Q: 字幕中文乱码**
A: 确认系统有 SimHei（黑体）字体，或 pipeline `fonts/` 下有备用 SIMHEI.TTF。

**Q: 文案质量差**
A: 确保 `~/kb/book-scripts/` 知识库存在且 `seed/samples/` 未被删除——script-gen 依赖这两个来源建立质量基准。
