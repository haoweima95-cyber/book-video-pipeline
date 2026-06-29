---
name: txt-to-prompt
description: |
  读取逐行 txt 文案，为每句话生成统一风格的生图提示词。
  默认油画风，所有提示词保持一致的视觉语言。
  触发方式：/txt-to-prompt、/生图提示词、"生成生图提示词"
---

# Txt to Prompt：文案转生图提示词

读取逐行文案 txt，为每句话生成对应的 AI 生图提示词。
全篇保持统一风格，默认油画风。

---

## 触发信号

- 要求为文案生成配图提示词
- 使用 `/txt-to-prompt`、`/生图提示词` 命令

---

## 工作流程

### Step 1：读取原文 + 参考范例

读取用户指定的 txt（**必须逐行读入，不得凭记忆**），同时读取同目录下的 `text_prompt.txt` 作为风格参考。

### Step 2：跳过结语（如有）

检查最后一行是否为结语类句子。匹配以下模式之一即视为结语，**不为其生成 prompt**：

- 以"感谢"开头且包含"观看/收看/再见/下期/下本书"
- "我们下本书再见""我们下期再见""下期见""明天见"
- 纯行动号召结尾（如"点赞关注转发"）

结语判定后：原文 N 句 → 只生成 N-1 条 prompt。

> 与 text-split 的配合：txt-to-prompt 跳过结语不生成 prompt，text-split 后续会把结语合并到倒数第二个文件末尾。最终 prompt/图片数量 == split 文件数量（都是 N-1）。

### Step 3：逐句生成提示词

**严格按 1 到 N-1 行生成（跳过结语行），不增不减。**

每句生成一个英文 SD prompt。遵循：

**统一视觉语言：**
- 默认油画风（可指定其他风格）
- 场景化、意象化——不直译文字，而用具象画面传达含义
- 用光、色、构图营造氛围

**固定后缀：**
- `painterly brushstrokes, cinematic composition, depth of field, atmospheric lighting`
- `no text, no letters, no numbers`
- `--ar 16:9`

**禁止：**
- 直译式配图（如"一个人在看书"）
- 出现文字、字母、数字
- 风格跳跃（一句写实、一句抽象）
- 任何可能引起不适的意象：人体器官（大脑、心脏、眼球等解剖结构）、骨骼、裸体、血腥、暴力、恐怖、诡异、阴暗、反社会、反人性等，一律用自然景物或建筑器物替代

### Step 4：校验（必须先于输出）

写入 prompt 文件前，必须通过两道强制校验。**任一不通过就停止，修正好再继续。禁止带着有问题的 prompt 进入 sd-image-gen。**

#### 校验 A：数量匹配

```python
# 读原文有效行数（跳过结语）
script_lines = [l.strip() for l in open(script_path, encoding='utf-8').readlines() if l.strip()]
if any(kw in script_lines[-1] for kw in ['感谢', '下本书再见', '下期见']):
    expected = len(script_lines) - 1
else:
    expected = len(script_lines)

# 数生成了多少条 prompt
actual = len([...])  # 已生成的 prompt 列表

if actual != expected:
    raise RuntimeError(f'❌ prompt 数量不匹配：预期 {expected}，实际 {actual}')
```

#### 校验 B：内容安全扫描

用代码逐条扫描每条 prompt，检查是否包含以下禁止词（不区分大小写），命中即停止：

```python
forbidden = [
    # 人体器官 / 解剖结构
    'brain', 'heart', 'eyeball', 'eye', 'skull', 'skeleton', 'bone', 'organ',
    'nervous system', 'spinal', 'artery', 'vein', 'lung', 'liver', 'kidney',
    'dissection', 'anatomy', 'carcass', 'corpse',
    # 手术 / 医疗场景
    'surgery', 'surgeon', 'surgical', 'operating table', 'operating theater',
    'patient on', 'patient in', 'scalpel', 'amputation',
    # 血腥 / 暴力
    'blood', 'gore', 'wound', 'weapon', 'execution', 'killing', 'murder',
    'torture', 'bleeding', 'slaughter',
    # 裸露
    'naked', 'nude', 'bare chest', 'bare body',
    # 恐怖 / 阴暗
    'horror', 'grotesque', 'disturbing', 'terrifying', 'nightmare',
]

for i, prompt in enumerate(prompts, 1):
    lower = prompt.lower()
    for term in forbidden:
        if term in lower:
            # 允许 "eyes" 出现在脸部自然观看语境（如 "gazing with hopeful eyes"）
            if term == 'eye' and ('gazing' in lower or 'looking' in lower or 'watching' in lower or 'viewing' in lower):
                continue
            # 允许 "heart" 出现在 emotional 复合词中（如 "heartbreaking", "heartwarming"）
            if term == 'heart' and ('heartbreaking' in lower or 'heartwarming' in lower or 'heartfelt' in lower or 'disheartening' in lower):
                continue
            # 允许 "organ" 出现在 "organized" 中
            if term == 'organ' and 'organized' in lower:
                continue
            # 允许 "disturbing" 仅用于抽象描述，后面不能跟 imagery/scene/creature
            if term == 'disturbing' and 'disturbingly' in lower:
                continue
            raise RuntimeError(f'❌ Prompt #{i} 包含禁止词 "{term}"：{prompt[:80]}...')
```

**禁止词白名单（这些组合场景中的词不算违规）：**

| 词 | 允许场景 | 示例 |
|----|---------|------|
| `eyes` | 脸部自然观看（gazing/looking/watching with eyes） | `hopeful crowds gazing upward with shining eyes` |
| `heart` | 情绪复合词 | `heartbreaking moment`, `heartwarming scene` |
| `organ` | `organized` 中 | `organized mockery` |
| `disturbing` | `disturbingly` 副词用法 | `disturbingly similar` |

### Step 5：输出

校验通过后，保存为 `原文件名_prompt.txt`，格式：

```
原文第一句
prompt内容

原文第二句
prompt内容
...
```

---

## 所需权限

- `Read` — 读取 txt
- `Write` — 写入 prompt 文件
