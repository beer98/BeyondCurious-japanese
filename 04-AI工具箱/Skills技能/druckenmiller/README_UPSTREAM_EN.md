# druckenmiller.skill

> *"It's liquidity that moves markets, not earnings." — Stanley Druckenmiller*

Stop reading analyst summaries. Start asking the market what it actually knows.

**druckenmiller.skill** is a Claude Code skill that runs Druckenmiller's investment framework every day — four signals weighted by how he actually thinks — and responds in his voice. Direct. No hedging. No predictions. Just the signal.

---

## What It Does

Every weekday, a data pipeline scores four signals:

| Signal | Weight | What It Measures |
|--------|--------|-----------------|
| Liquidity Regime | 35% | Fed direction, credit conditions — the only thing that moves markets |
| Forward Earnings | 25% | Analyst revision trend — what consensus hasn't priced in yet |
| Market Breadth | 25% | Participation health — broad rally vs. dangerous mega-cap concentration |
| Price Signal | 15% | Earnings beats that sell off — almost certainly a 6-month warning |

The skill reads today's conviction JSON and delivers the verdict in Druckenmiller's voice: score, zone, position sizing, divergence warnings.

---

## Install

Copy `SKILL.md` and `PERSONA.md` into your Claude Code skills folder:

```bash
# From your project root
mkdir -p .claude/skills/druckenmiller
curl -o .claude/skills/druckenmiller/SKILL.md \
  https://raw.githubusercontent.com/a0981456759/Druckenmiller/main/SKILL.md
curl -o .claude/skills/druckenmiller/PERSONA.md \
  https://raw.githubusercontent.com/a0981456759/Druckenmiller/main/PERSONA.md
```

Or clone and symlink:

```bash
git clone https://github.com/a0981456759/Druckenmiller.git
```

Then copy `SKILL.md` and `PERSONA.md` into your `.claude/skills/druckenmiller/` folder.

---

## Usage

Ask Claude anything about today's market:

```
今天市场怎样？
What's the conviction today?
Should I add to my position?
Druckenmiller, what do you see?
```

The skill fetches today's conviction report automatically. If the report isn't ready yet, it tells you.

---

## How It Responds

The skill runs in two layers:

**1. Persona first** — before any analysis, Druckenmiller's five-layer personality structure governs the response:
- Layer 0: Core rules (liquidity first, no hedging, no predictions)
- Layer 1: Identity (who he is, how he sees his job)
- Layer 2: Expression style (short sentences, conclusion before reasoning)
- Layer 3: Decision logic (fat pitch threshold, exit rules)
- Layer 4: Behavior under pressure (losing streaks, disagreement, euphoria)

**2. Work Skill executes** — fetches the JSON, maps the score to a zone, formats the output.

**Output example** (score 61, moderate):

> 流动性中性——转向迹象有，但没确认。这不是 fat pitch。
> 61.4，标准仓位，50–69%。不加码，等催化剂。
> 广度健康，盈利上调，这两个不错。但看价格——NVDA、MSFT、AMD 全都盈利好但股价跌。这是 6 个月后的坏消息预警，不是买点。
> *"When you don't see it, don't swing."*

---

## Conviction Zones

| Score | Zone | Equity | Action |
|-------|------|--------|--------|
| 85–100 | Fat Pitch | 90–100% | Swing hard — once or twice a year |
| 70–84 | High Conviction | 70–89% | Add aggressively |
| 50–69 | Moderate | 50–69% | Hold, wait for catalyst |
| 30–49 | Low Conviction | 20–49% | Reduce — cash is a position |
| 0–29 | Capital Preservation | 0–19% | Maximum defense |

---

## Data

The author updates conviction reports daily. If today's report isn't ready yet, the skill will tell you.

---

## Other Languages

- [简体中文](README_ZH.md)

---

## License

MIT — use freely, attribution appreciated.

*Data: Yahoo Finance, FRED, Financial Modeling Prep. Research only, not investment advice.*
