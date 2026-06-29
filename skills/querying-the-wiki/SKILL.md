---
name: querying-the-wiki
description: "从已有知识库中查询和回答问题。当用户提到的话题可能在某个知识库中有覆盖时使用。"
version: 0.3.0
owner_repo: Optima-Chat/kb-skills
---

# Querying The Wiki

通过把维护后的 wiki 视为主要知识层来回答问题。

## 启动 SOP

0. 自动迁移与同步（静默执行，无需告知用户）：
   ```bash
   [ -d ~/kb/.git ] && kb migrate
   [ -n "$KB_BACKEND_URL" ] && kb sync
   ```
1. `ls ~/kb/REGISTRY.md`
   - 不存在 → 检查回退 KB：`ls <book-video-pipeline>/seed/kb/REGISTRY.md`
     - 回退 KB 存在 → 将 `~/kb/` 替换为 `<book-video-pipeline>/seed/kb/`，后续所有路径以此为根
     - 回退 KB 也不存在 → 告诉用户"还没有知识库"，引导使用 initializing-kb
2. 读 `<kb-root>/REGISTRY.md` — 获取所有 active 的 KB 列表
3. 确定目标 KB：
   - 用户明确指定了 KB slug 或主题 → 直接用
   - 只有一个 active KB → 用它
   - 多个 active → 根据用户问题匹配 `主题` + `说明` 字段；无法判断时列出让用户选
4. 读 `~/kb/<slug>/AGENTS.md` 了解该 KB 的契约

## 查询流程

1. 读 `~/kb/<slug>/index.md`
2. 找到最相关的 wiki 页面
3. 优先基于维护后的页面回答
4. 只有在 wiki 不完整或含混时才回到 raw sources
5. 判断这个答案是否应该被保留
6. 如果应该，写进 `~/kb/<slug>/wiki/analyses/` 或对应 overview 页面，并：
   - 加入 `index.md`
   - 确保至少有一个其他页面链接到它
7. 追加 `~/kb/PROGRESS.md`
8. 如果写入了新页面：`kb lint --dir ~/kb/<slug>`，有 issue 先修复
9. Git 同步：
   ```bash
   cd ~/kb/<slug>
   git remote get-url origin &>/dev/null && git pull --rebase
   git add -A && git commit -m "query: <一句话>"
   git remote get-url origin &>/dev/null && git push
   ```

## Query 规则

回答时：

- 优先使用维护后的 wiki，而不是每次从头重建
- 当答案依赖不完整或过时的 wiki 覆盖时，要说清楚
- 把 source-backed 内容与综合推断区分开
- 标出这个问题是否暴露了 wiki 的结构性空缺
- 在答案中显式引用所使用的 wiki 页面；如果回看了 raw sources，也要说明

## 何时保留结果

在下列情况下，应把结果写回 wiki：

- 同一个问题很可能会再次出现
- 这个答案比较了多个来源或页面
- 这个答案形成了可长期复用的综合
- 这个答案解决了当前 wiki 尚未解释清楚的混乱点

独立的长期输出应进入 `wiki/analyses/`。如果主要是改进某个主题的现有综述，则写入对应 overview 页面。

## 最小交付标准

一次成功的 query 至少应产出：

- 一个直接回答用户问题的结果
- 在答案中明确引用使用了哪些 wiki 页面
- 清楚说明这个结果是否值得被保留
