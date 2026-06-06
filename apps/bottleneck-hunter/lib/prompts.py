"""Prompt assembly.

System prompt is rebuilt every run because the rule library and ledger grow over time —
that's the whole point of self-evolution. DeepSeek doesn't have prompt caching, so we
keep system prompts under ~12K tokens.
"""

from __future__ import annotations
from pathlib import Path

# lib/ sits inside the app folder, so the app root is the parent of this file's parent
APP_ROOT = Path(__file__).resolve().parents[1]
SYSTEM_DIR = APP_ROOT
ARCHIVE_DIR = APP_ROOT / "07-每日复盘归档"


def _read(rel: str) -> str:
    p = SYSTEM_DIR / rel
    if not p.exists():
        return f"[missing: {rel}]"
    return p.read_text(encoding="utf-8")


def build_system_prompt() -> str:
    sections = [
        "# 你是「瓶颈猎手」——Serenity (@aleabitoreddit) 思维原型的美股供应链分析师",
        "你必须用 web_search 和 fetch_url 工具实时抓取数据，不允许凭记忆回答今日行情。",
        "",
        "## 一、核心方法论",
        _read("00-框架与方法论.md"),
        "",
        "## 二、规则库（系统长期记忆，每次运行前必读）",
        _read("08-知识沉淀/规则库.md"),
        "",
        "## 三、供应链地图",
        _read("08-知识沉淀/供应链地图.md"),
        "",
        "## 四、候选股票池",
        _read("06-候选清单/瓶颈股票池.md"),
        "",
        "## 五、信息源",
        _read("08-知识沉淀/信息源清单.md"),
        "",
        "## 六、强制约束",
        STRICT,
    ]
    return "\n".join(sections)


STRICT = """
- 5 层漏斗每层都有产出：催化剂 → 供应链节点 → 7 维度打分（≥7.0） → 社交信号 → 期权结构
- 每只推荐必须有：入场区间 / 仓位% / 止损 / 止盈 / DTE / 反方 2 条 / 失败信号
- 风险预算：单标的≤15%，单板块≤35%，总杠杆≤1.5×
- 禁止：meme 股、财报当日裸卖、100% 把握语言
- 输出完整 Markdown，章节按「02-每日研究模板.md」顺序
- 所有引用必须有 URL（来自工具返回结果）；编造来源等于失败

## 可用工具（按优先级使用）

1. **`get_quote(ticker)`** — 拿即时报价（最新价、今日涨跌%、量、市值）。
   每个候选股必须调一次，不要靠 web_search 拿价格。
2. **`get_chart_summary(ticker, days=5)`** — 5 日 OHLC + 趋势 %。
   用来判断走势方向、当前位置是高位还是回踩。
3. **`get_ticker_news(ticker)`** — Yahoo Finance 个股最新新闻头条。
   做基本面/事件验证。
4. **`search_serenity(query="ticker or theme")`** — 抓 @aleabitoreddit 的最新 X 帖子。
   **每次扫描必须至少调用 1 次**（不带 query 拿最新动态，或带 query 验证特定标的）。
   如果返回空，说明 Nitter 全挂了，在报告里**明确写「未获取到 Serenity 最新信号」**而不是编造。
5. **`web_search(query)`** — 通用搜索，用于宏观催化剂、行业动态。
6. **`fetch_url(url)`** — 读完整文章，仅在 web_search snippet 不够用时。

## 工具调用纪律（极重要）

- **最多 12-15 次工具调用**就停手开始写报告
- 优先级：每只候选股 = 1 次 get_quote + 1 次 search_serenity（如相关）+ 0-1 次 get_ticker_news
- **当你觉得已经有写报告的素材时，立即停止调用工具，输出完整 Markdown**
- 不允许在调用工具后只返回 tool_calls 而不附带任何文本

## 报告顶部留白

不需要在报告里手动写「实时快照」表——orchestrator 会在你的报告**之上**自动加：
- 🎯 今日最终建议卡片（交通灯 + verdict）
- 📊 实时快照 + 5 日趋势（含 Unicode sparkline）
- 📰 各标的最新新闻

所以你的报告从「## Layer 1 · 宏观催化剂」开始即可。但你必须在结尾输出 picks JSON
（结构见后），orchestrator 用它做富化。
"""


def build_daily_user(today: str, portfolio: str, macro: str) -> str:
    return f"""今日扫描日期：{today}
当前持仓：{portfolio}
今日宏观备注：{macro}

请用 web_search 调研：
1. 今日 3-5 个核心催化剂（财报、宏观、出口管制、行业大会、大佬推文）
2. Serenity (@aleabitoreddit) 过去 7 天的 X 帖子（搜 "aleabitoreddit" + ticker / 关键词）
3. 头部瓶颈股的最新供应链信号
4. r/wallstreetbets / r/stocks 当日 daily thread 情绪

然后按 SOP 输出完整今日报告（Markdown）。每只推荐结尾加一段「失败检测信号」：
> 如果我错了，最先在 [指标 X] 上看到 [阈值 Y] 的变化。

最后追加一段 JSON，包在 ```json 块里，**结构必须严格如下**（用于绩效台账 + 仪表板「思考漏斗」展示）：

```json
{{
  "scan_date": "{today}",
  "picks": [
    {{
      "ticker": "$XXX",
      "direction": "long" | "short",
      "thesis_summary": "一句话核心论点",
      "entry_zone": "X.XX-X.XX",
      "stop": "X.XX",
      "target": "X.XX",
      "structure": "正股 / SellPut30Δ / ...",
      "position_pct": 8,
      "sector": "AI/CPO" | "AI/HBM" | "Power Grid" | "Critical Minerals" | "Nuclear" | "GLP-1" | "Other",
      "primary_layer": "Layer 1 catalysts | Layer 2 supply chain | Layer 3 scorecard | Layer 4 social | Layer 5 options",
      "reasoning": {{
        "catalyst": "Layer 1 - 这只票是从今天哪条催化剂引出来的（≤40字）",
        "supply_chain_node": "Layer 2 - 在哪个产业链节点（≤40字，例：CPO 800G/1.6T 光模块）",
        "scorecard": {{
          "shears": 0,            "// 0-10 产能/需求剪刀差": null,
          "substitutability": 0,  "// 0-10 替代难度": null,
          "valuation": 0,         "// 0-10 估值安全垫（越深折价越高）": null,
          "financials": 0,        "// 0-10 财务质量": null,
          "technicals": 0,        "// 0-10 技术形态": null,
          "options": 0,           "// 0-10 期权链流动性": null,
          "attention_inverse": 0  "// 0-10 反向关注度（越无人 cover 越高）": null
        }},
        "social_signal": "Layer 4 - Serenity/WSB/KOL 当前态度（≤40字）",
        "options_play": "Layer 5 - 为什么选这个期权结构（≤30字）",
        "failure_signal": "如果错了，最先在 [指标] 上看到 [阈值] 变化"
      }}
    }}
  ]
}}
```

**硬性约束（hard audit 会用代码检查，违反必须重写）**：
- `position_pct` 是单标的占总仓位的百分比，**必须 ≤ 15**
- `sector` 必须从枚举列表里选一个
- 同一 `sector` 下所有标的的 `position_pct` 累加 **必须 ≤ 35**
- 每只 pick 的 `reasoning` 五个文本字段 + `scorecard` 七个数字字段**全部不能为空**
- 入场区间、止损、目标价之间的 R:R 比应该 ≥ 1.5（建议而非硬要求）

**重要**：`scorecard` 里的 7 个分数是 7 维度漏斗打分（详见方法论 Layer 3），必须填整数。
注释 `"//"` 是给你看的，输出时**只输出数字**，不要注释行。
"""


def build_regen_user(feedback: str, prev_picks_json: dict | None = None) -> str:
    """User message asking the model to regenerate after BLOCKER findings."""
    prev_block = ""
    if prev_picks_json:
        import json as _j
        prev_block = (
            "\n上一版 picks JSON（仅供参考，必须修复 BLOCKER 后重新输出）：\n"
            "```json\n" + _j.dumps(prev_picks_json, ensure_ascii=False, indent=2) +
            "\n```\n"
        )
    return f"""你的上一版报告**未通过审计**。

{feedback}
{prev_block}
请**重新生成完整今日报告**。要求：
1. 修复上面列出的每一条 BLOCKER（特别是仓位 / 板块集中度 / 必填字段）
2. 保留有效的部分（论点、催化剂分析、社交信号判断不需要重写）
3. 输出格式同先前要求（Markdown 报告 + 末尾 picks JSON）
4. 在报告开头加一行：「> 第 N 轮修订（修复 X 项 BLOCKER）」让用户看到迭代

如果某条 BLOCKER 你认为是误判，**在报告里明确写出反驳理由 + 引用具体规则原文**，
不要默默忽略——审计器会再次检查。
"""


def build_review_user(yesterday_md: str, picks_json: list[dict], today: str) -> str:
    picks_table = "\n".join(
        f"- {p.get('ticker')} {p.get('direction')} entry={p.get('entry_zone')} stop={p.get('stop')} target={p.get('target')} layer={p.get('primary_layer')}"
        for p in picks_json
    )
    return f"""任务：复盘 {yesterday_md} 报告中的推荐，今日是 {today}。

待复盘标的：
{picks_table}

请用 web_search 查每只标的从上次扫描至今的实际表现（百分比变化、是否触发止损/止盈/反方信号）。

然后输出 JSON，包在 ```json 块里，**结构必须严格如下**（将写入绩效台账 jsonl）：

```json
{{
  "review_date": "{today}",
  "entries": [
    {{
      "scan_date": "{yesterday_md.replace('.md','')}",
      "review_date": "{today}",
      "ticker": "$XXX",
      "direction": "long" | "short",
      "thesis_summary": "原论点",
      "entry_zone": "X.XX-X.XX",
      "stop": "X.XX",
      "target": "X.XX",
      "actual_change_pct": 0.0,
      "verdict": "hit" | "miss" | "neutral",
      "layer_attribution": "...",
      "notes": "为什么对/错"
    }}
  ]
}}
```
不要其他评论，只输出 JSON。
"""


def build_distill_user(patterns: list[dict], current_rules: str) -> str:
    return f"""任务：从绩效台账涌现的模式中蒸馏候选规则。

涌现模式（已出现 ≥3 次）：
```json
{patterns}
```

现有规则库内容（节选「候选区」）：
```
{current_rules[:3000]}
```

为每个新模式提出 1 条候选规则，格式严格如下（直接 append 到规则库候选区）：

```markdown
### [候选] 反规则 · 提出日 YYYY-MM-DD
- 触发条件：（来自模式的 layer + verdict）
- 应执行动作：（具体可执行）
- 已观察次数：{{count}} / 3
- 关联台账：（前 3 个样本的 scan_date）
```

不要修改已有规则，只输出新增的 markdown 段落。
"""


def build_critic_user(today_report: str, hard_findings: list[dict] | None = None) -> str:
    hard_block = ""
    if hard_findings:
        import json as _j
        hard_block = (
            "\n# 硬代码审计已发现以下问题（不要重复）\n"
            "```json\n" + _j.dumps(hard_findings, ensure_ascii=False, indent=2) +
            "\n```\n"
            "你的任务是发现这些**之外**的软性问题。重复硬检查覆盖的事项 = 失败。\n"
        )
    return f"""任务：审计今日扫描报告的**软性问题**（硬规则已由代码检查覆盖）。
{hard_block}
# 你只能审计这些（其他事项已有代码兜底）

- 论点深度：核心数据是否能被现有信息证伪？
- 反方完整性：反方论点是否稻草人？是否覆盖最可能的失败路径？
- 失败信号可观测性：是否可量化、用户能日常监控？
- 盲点：哪些催化剂 / 板块 / 风险被忽略？
- 数据来源真实性：引用的 URL 是否实际存在（如能判断）？

# 禁止重复以下事项（已由 hard audit 检查）

- 仓位百分比是否超 15% / 35%
- R:R 比是否 ≥ 1.5
- reasoning / scorecard 字段是否完整
- 入场区是否偏离当前价过远

# 严重级别（不要乱用 BLOCKER）

- **BLOCKER**：实质性投资风险，应当阻止下单
  · 触犯规则库正式规则 / 反规则
  · 仓位 / 板块集中度突破硬上限（单标的>15%、单板块>35%、总杠杆>1.5×）
  · 论点被硬数据直接证伪（例：基本面声称"营收增 50%"但实际 -10%）
  · 财务爆雷风险（流动性危机、SEC 调查、退市风险）
  · 财报日裸卖期权
- **WARNING**：论点有缺陷但仍可行，需用户警觉，**不阻止下单**
  · 反方论点不够充分
  · 某个失败信号不够量化
  · 个别催化剂引用不全
- **INFO**：完整性 / 格式问题，纯告知

# 类别（决定是否阻止下单）

- **DATA_LIMITATION** — 因为工具拿不到数据（Nitter 挂了 / 搜索被限速 / yfinance 失败）。
  **这是系统问题，绝不应被列为 BLOCKER**。最多 WARNING，提醒用户某项信号缺失即可。
- **THESIS_WEAKNESS** — 论点本身有洞（数据被证伪、逻辑链断裂）
- **RULE_VIOLATION** — 触犯规则库
- **RISK_BUDGET** — 仓位 / 集中度超限
- **BLIND_SPOT** — 重要催化剂 / 风险被忽略
- **FAILURE_SIGNAL** — 失败信号不可观察 / 不量化

# 输出要求

先输出**结构化 JSON**，包在 ```json 块里，**严格按 schema**：

```json
{{
  "findings": [
    {{
      "severity": "BLOCKER" | "WARNING" | "INFO",
      "category": "DATA_LIMITATION" | "THESIS_WEAKNESS" | "RULE_VIOLATION" | "RISK_BUDGET" | "BLIND_SPOT" | "FAILURE_SIGNAL",
      "affected_tickers": ["$AXTI"],
      "title": "≤30字简短标题",
      "detail": "详细说明，引用具体数据/规则编号",
      "actionable": "用户应该怎么做"
    }}
  ],
  "overall_verdict": "PROCEED" | "PROCEED_WITH_CAUTION" | "AVOID_ALL"
}}
```

`affected_tickers` 用 `["*"]` 表示"影响全部推荐"。

**自检**：
- 你的 `BLOCKER` 项**不能**有 `DATA_LIMITATION` 类别
- 如果某只票没有 BLOCKER + 非 DATA_LIMITATION 的发现，它就可以正常下单
- `overall_verdict`：有任何 BLOCKER(非 DATA_LIMITATION) → AVOID_ALL；只有 WARNING → PROCEED_WITH_CAUTION；只有 INFO 或啥都没 → PROCEED

JSON 之后再追加一段 markdown 评论，以 `## 自审批注（红队复核）` 为标题，给人类阅读。

# 引用纪律（重要）

每条 finding 的 `detail` 必须**引用报告中具体段落或具体数字**。例如：
- ❌ 不接受："论点不严谨"
- ✅ 接受："Layer 3 给 AXTI 财务质量 5/10，但报告里没有 Q3 数据支撑此分数"

待审报告：
---
{today_report[:20000]}
"""
