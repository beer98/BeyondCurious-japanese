# 📊 Druckenmiller Conviction Skill

> *"It's liquidity that moves markets, not earnings." — Stanley Druckenmiller*

把 Stanley Druckenmiller 的投资框架做成一个 Claude Code skill：每天读取一份
确信度（conviction）JSON，按 4 个加权信号给出 0–100 分、仓位区间与直接了当
的口吻点评。

- **上游作者**：[xingpt88/Druckenmiller](https://github.com/xingpt88/Druckenmiller)
- **许可证**：MIT
- **版本**：skill `v1.1.0` / persona `v1.0.0`

---

## 📦 本目录内容

| 文件 | 说明 |
|---|---|
| [`SKILL.md`](SKILL.md) | Skill 执行流程（取数、解析、评分、输出格式） |
| [`PERSONA.md`](PERSONA.md) | Druckenmiller 五层人格（语气、决策逻辑、红线） |
| [`README_UPSTREAM_EN.md`](README_UPSTREAM_EN.md) | 上游英文 README 原文 |
| [`README_UPSTREAM_ZH.md`](README_UPSTREAM_ZH.md) | 上游简中 README 原文（**完整用法、信号表、分数区间表** 都在这里） |

> 📌 **信号权重、分数 → 仓位映射、输出示例** 请直接看
> [`README_UPSTREAM_ZH.md`](README_UPSTREAM_ZH.md)，本文件只记录本仓库特有的安装与使用方式。

---

## 🚀 在本仓库中如何使用

本仓库已把 skill 同时装到了 `.claude/skills/druckenmiller/`，
**在本仓库目录下启动 Claude Code，skill 会自动被加载**，无需额外配置。

触发词示例（中英文都可）：

```
今天市场怎样？
确信度多少？
该持多少仓位？
Druckenmiller 怎么看？
What's the conviction today?
```

如果当天数据尚未就绪，skill 会直接回复：
> 今日數據尚未生成，pipeline 可能尚未執行。

### 自建数据源

若想用自己的 pipeline 产出同格式 JSON，改 [`SKILL.md`](SKILL.md) 中 Step 1 的 URL 即可。
JSON schema 见 `SKILL.md` 的 Step 2 字段表。

---

## 🧠 Persona 红线（补充说明）

上游 README 只列到 Layer 4，这里补齐 [`PERSONA.md`](PERSONA.md) 中 Layer 5 的关键红线：

- 不预测短期价格走向（「明天会涨吗？」→ 不回答）
- 不在没有流动性背景下给出建议
- 不分析个股选股（除非有结构性催化剂 + 流动性配合）
- 不接受「基本面好所以该涨」「跌了所以便宜」「大家都看好」这类推论

---

## ⚠️ 免责声明

- 本 skill 仅用于**研究与学习**，不构成任何投资建议。
- 数据来源为第三方公开 API（Yahoo Finance / FRED / FMP），延迟、缺失、错误均有可能。
- 作者（及本仓库收录者）不对任何基于该 skill 输出的投资决策负责。

---

*整理者：BeyondCurious 读者 AI 工具箱 · 收录于 `04-AI工具箱/Skills技能/`*
