# druckenmiller.skill

> *「推动市场的是流动性，不是盈利。」— Stanley Druckenmiller*

别再看分析师总结了。直接问市场它真正知道什么。

**druckenmiller.skill** 是一个 Claude Code skill，每天运行 Druckenmiller 的投资框架——四个信号，按他真实的思维方式加权——用他的口吻回答。直接。不对冲。不预测。只给信号。

---

## 它做什么

每个工作日，数据 pipeline 对四个信号打分：

| 信号 | 权重 | 衡量什么 |
|------|------|---------|
| 流动性制度 | 35% | Fed 方向、信用状况——唯一真正推动市场的东西 |
| 前瞻盈利 | 25% | 分析师修正趋势——市场共识尚未 price in 的信息 |
| 市场广度 | 25% | 参与健康度——广泛上涨 vs. 危险的大型股集中 |
| 价格信号 | 15% | 盈利超预期但股价下跌——几乎必然是 6 个月后的坏消息预警 |

Skill 读取今日的确信度 JSON，用 Druckenmiller 的口吻给出结论：分数、区间、仓位建议、背离警告。

---

## 安装

将 `SKILL.md` 和 `PERSONA.md` 复制到你的 Claude Code skills 文件夹：

```bash
# 从你的项目根目录
mkdir -p .claude/skills/druckenmiller
curl -o .claude/skills/druckenmiller/SKILL.md \
  https://raw.githubusercontent.com/a0981456759/Druckenmiller/main/SKILL.md
curl -o .claude/skills/druckenmiller/PERSONA.md \
  https://raw.githubusercontent.com/a0981456759/Druckenmiller/main/PERSONA.md
```

或直接 clone：

```bash
git clone https://github.com/a0981456759/Druckenmiller.git
```

然后将 `SKILL.md` 和 `PERSONA.md` 复制到你的 `.claude/skills/druckenmiller/` 文件夹。

---

## 使用方法

问 Claude 任何关于今日市场的问题：

```
今天市场怎样？
确信度是多少？
现在该加仓吗？
Druckenmiller，你怎么看？
```

Skill 自动抓取今日确信度报告。如果报告还没生成，它会告诉你。

---

## 回答方式

Skill 分两层运行：

**1. Persona 先行** — 在任何分析之前，Druckenmiller 的五层人格结构决定回答方式：
- Layer 0：核心规则（流动性第一、不对冲语言、不做预测）
- Layer 1：身份（他是谁，他怎么看自己的工作）
- Layer 2：表达风格（短句、先结论后理由）
- Layer 3：决策逻辑（fat pitch 门槛、出场规则）
- Layer 4：压力下的行为（连亏、分歧、市场狂热时怎么做）

**2. Work Skill 执行** — 抓取 JSON、将分数映射到区间、格式化输出。

**输出示例**（分数 61，moderate）：

> 流动性中性——转向迹象有，但没确认。这不是 fat pitch。
> 61.4，标准仓位，50–69%。不加码，等催化剂。
> 广度健康，盈利上调，这两个不错。但看价格——NVDA、MSFT、AMD 全都盈利好但股价跌。这是 6 个月后的坏消息预警，不是买点。
> *"When you don't see it, don't swing."*

---

## 确信度区间

| 分数 | 区间 | 股票仓位 | 行动 |
|------|------|---------|------|
| 85–100 | Fat Pitch | 90–100% | 全力出手——一年一两次 |
| 70–84 | High Conviction | 70–89% | 积极加仓 |
| 50–69 | Moderate | 50–69% | 标准仓位，等催化剂 |
| 30–49 | Low Conviction | 20–49% | 减仓，现金是仓位 |
| 0–29 | Capital Preservation | 0–19% | 最大防御 |

---

## 数据

作者每日更新确信度报告。如果今日报告尚未生成，Skill 会告知你。

---

## 其他语言

- [English](README.md)

---

## 授权

MIT — 自由使用，欢迎标注来源。

*数据来源：Yahoo Finance、FRED、Financial Modeling Prep。仅供研究，非投资建议。*
