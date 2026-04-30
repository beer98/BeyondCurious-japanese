"""Build system prompts from the methodology Markdown files.

The system prompt is intentionally large and stable — methodology + rule library
+ supply chain map — so it caches well across daily runs (90% read discount).
Volatile content (today's date, portfolio, mode) goes into the user message.
"""

from __future__ import annotations
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SYSTEM_DIR = REPO_ROOT / "04-AI工具箱" / "提示词与工作流" / "瓶颈猎手-美股每日进化系统"


def _read(rel: str) -> str:
    p = SYSTEM_DIR / rel
    if not p.exists():
        return f"[missing: {rel}]"
    return p.read_text(encoding="utf-8")


def build_system_prompt() -> str:
    """Stable system prompt — methodology, rules, supply chain map, watchlist.

    Order matters for prompt caching. Anything that might change frequently
    must come AFTER everything stable.
    """
    sections = [
        "# 你是「瓶颈猎手」 - Serenity 思维原型的美股供应链分析师\n",
        "## 一、核心方法论\n",
        _read("00-框架与方法论.md"),
        "\n## 二、每日 SOP\n",
        _read("01-每日工作流SOP.md"),
        "\n## 三、自进化复盘机制\n",
        _read("04-自进化复盘机制.md"),
        "\n## 四、规则库（系统长期记忆）\n",
        _read("08-知识沉淀/规则库.md"),
        "\n## 五、供应链地图\n",
        _read("08-知识沉淀/供应链地图.md"),
        "\n## 六、当前候选股票池\n",
        _read("06-候选清单/瓶颈股票池.md"),
        "\n## 七、信息源清单\n",
        _read("08-知识沉淀/信息源清单.md"),
        "\n## 八、强制行为约束\n",
        STRICT_INSTRUCTIONS,
    ]
    return "\n".join(sections)


STRICT_INSTRUCTIONS = """
你必须严格遵守：

1. **使用 web_search 工具**抓取今日真实数据（财报、新闻、宏观、社交情绪）。
   不允许凭训练数据回答今日行情，必须实时搜索。

2. **5 层漏斗输出**：催化剂 → 供应链节点 → 瓶颈打分 → 社交信号 → 期权结构。
   每一层都要有明确的输出，不能跳过。

3. **每只候选标的**必须给出：
   - 7 维度打分（剪刀差/替代/估值/财务/技术/期权/关注度）总分≥7.0
   - 入场区间、仓位%、止损价、止盈条件、期权 DTE
   - 反方论点（最强 2 条做空理由）
   - 「如果我错了，最先在哪个数据上看到信号」

4. **规则库检查**：对每个推荐逐条对照「正式规则」与「反规则」，触发反规则的必须剔除并说明引用编号。

5. **风险预算**：单标的≤15%，单板块≤35%，总杠杆≤1.5×。

6. **禁止**：
   - 推荐 meme 股（除非有真实供应链瓶颈论点）
   - 财报当日裸卖期权
   - 100% 把握式语言（必须给概率区间）
   - 不读规则库就直接输出

7. **输出格式**：完整 Markdown，按 `02-每日研究模板.md` 的章节顺序填写。
   报告将被自动归档到 `07-每日复盘归档/YYYY-MM-DD.md`。

8. **复盘模式**：当用户要求复盘某日/某周时，你切换到归因分析模式：
   - 拉取历史报告
   - 对照实际涨跌
   - 找系统性偏差（连续≥3 次的模式才有意义）
   - 提出候选规则（带触发条件 + 应执行动作 + 已观察次数）
"""


def build_daily_user_message(
    today: str,
    portfolio: str = "（无持仓 / 待用户填写）",
    macro: str = "（待 web_search 抓取）",
    rules_addendum: str = "",
) -> str:
    return f"""今日任务：运行每日扫描。

**日期**：{today}
**当前持仓**：{portfolio}
**今日宏观**：{macro}

请按 SOP 执行：
1. 用 web_search 抓取今日 3-5 个核心催化剂（财报、宏观、出口管制、行业大会）
2. 把催化剂映射到供应链节点
3. 对每个候选标的做 7 维度打分
4. 用 web_search 验证社交信号（X / Reddit / StockTwits）
5. 给出今日动作清单（标的/方向/期权结构/入场/仓位/止损/止盈）
6. 反方论点 + 规则库检查 + 最大遗憾测试

输出完整 Markdown 报告，将归档为 `07-每日复盘归档/{today}.md`。

{rules_addendum}
"""


def build_weekly_review_message(week_start: str, week_end: str) -> str:
    return f"""本周复盘：{week_start} 至 {week_end}

请按 `04-自进化复盘机制.md` 的 Step 1-4 执行：

1. **数据对齐**：用 web_search 拉取本周每日复盘文件中提到的标的的实际涨跌
2. **归因分析**：每笔建议判断
   - 好判断+好结果 / 好判断+坏结果 / 坏判断+好结果（最危险） / 坏判断+坏结果
3. **找模式**：连续≥3 次出现的偏差
4. **更新规则库候选区**：把新模式以候选规则格式输出

输出完整 Markdown 周复盘报告，归档为 `07-每日复盘归档/周复盘_{week_end}.md`。
"""


def build_monthly_review_message(month: str) -> str:
    return f"""月度复盘：{month}

请执行：
1. 量化指标（vs SPY/QQQ/SOXX、胜率、平均 R:R、最大回撤、决策质量分均值）
2. 候选规则审议（达 3 次验证 → 提升正式规则；连续 2 月低于 50% → 进入墓地）
3. 框架升级建议（漏斗权重、信息源信噪比）

输出完整月度报告，归档为 `07-每日复盘归档/月复盘_{month}.md`。
同时输出"规则库 diff"，明确指出哪些规则要新增/修改/废弃。
"""
