# 瓶颈猎手 · 美股每日自进化系统

> 思维原型：Serenity（@aleabitoreddit on X，原 Reddit WSB）——AI / 半导体供应链分析师，主张「逆向拆解供应链 → 锁定无人关注的瓶颈点 → 在机构轮动前建仓」，并以期权卖方策略择时放大收益。

## 这套系统是干什么的

每天用一套**固定 SOP** 让 AI（Claude / GPT / Gemini 任意一个）：

1. **扫描** 当日美股盘前 / 盘中 / 盘后的催化剂、社交情绪、供应链信号；
2. **复用 Serenity 的思维链** 进行二阶 / 三阶推理（不是看 K 线，是看产业链位置）；
3. **筛出 3–5 只今日值得行动的票**，给出仓位、入场区间、止损、退出条件；
4. **晚间复盘**，把当日命中 / 未命中的归因写入「知识沉淀」，下次自动调用——这就是「自进化」。

## 目录

| 文件 | 用途 |
|---|---|
| `00-框架与方法论.md` | Serenity 思维原型 + 我们落地的 5 层筛选漏斗 |
| `01-每日工作流SOP.md` | 盘前 / 盘中 / 盘后三段式时间表，每段做什么 |
| `02-每日研究模板.md` | Copy-paste 用的当日研究 Markdown 模板 |
| `03-持仓与交易日志.md` | 真实持仓 + 每笔交易的入场 / 出场理由 |
| `04-自进化复盘机制.md` | 周复盘 / 月复盘，把战胜 & 败因蒸馏成规则 |
| `05-Claude执行提示词.md` | 直接喂给 Claude / GPT 的 system prompt，可一键运行 |
| `06-候选清单/` | 当前监控的瓶颈股票池（按板块） |
| `07-每日复盘归档/` | 每天一个文件，命名 `YYYY-MM-DD.md` |
| `08-知识沉淀/` | 经过复盘验证的可复用规则 / 反规则 |

## 快速开始

### A. 完全自动化（推荐）

仓库已配好 GitHub Actions，配置好 secret 后**每个交易日盘前自动跑**：

1. 在 GitHub repo Settings → Secrets → Actions 加 `ANTHROPIC_API_KEY`
2. 可选：Settings → Variables 设 `CLAUDE_MODEL=claude-opus-4-7` `CLAUDE_EFFORT=xhigh`
3. 三个 workflow 自动生效：
   - `daily-scan.yml` · 工作日盘前 07:30 ET 自动跑 → 报告 commit 到 `07-每日复盘归档/YYYY-MM-DD.md`
   - `weekly-review.yml` · 周日 19:00 ET 自动周复盘
   - `monthly-review.yml` · 月底自动月复盘 + 规则库 diff
4. 任何一个都可在 GitHub Actions 页面手动 `Run workflow` 立即触发
5. Claude 用内置 `web_search` + `web_fetch` 工具实时抓催化剂、财报、社交情绪——**不需要任何额外 API key**

### B. 本地手动跑

```bash
pip install -r scripts/requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
python scripts/run_scan.py daily       # 当日扫描
python scripts/run_scan.py weekly      # 周复盘
python scripts/run_scan.py monthly     # 月复盘
python scripts/run_scan.py review --date 2026-04-30   # 重新复盘某日
```

可选环境变量：`PORTFOLIO`、`MACRO_NOTE`、`CLAUDE_MODEL`、`CLAUDE_EFFORT`、`CLAUDE_MAX_TOKENS`。

### C. 纯手动（粘贴提示词模式）

读 `05-Claude执行提示词.md`，把内容粘到 Claude/GPT 网页对话框。

## 自动化架构

```
GitHub Actions cron ─┐
                     ├──> scripts/run_scan.py ──> Claude Opus 4.7
本地 CLI ────────────┘                              + adaptive thinking
                                                    + web_search 实时抓数据
                                                    + 系统提示词 prompt cache
                                                    │
                                                    ▼
                              07-每日复盘归档/YYYY-MM-DD.md
                                                    │
                                                    ▼
                                    git commit & push（自动）
```

**成本估算**（Opus 4.7 + xhigh effort）：
- 每日扫描 ≈ $0.5-2（system prompt 约 30K tok，二次以后 90% 缓存读）
- 周复盘 ≈ $1-3
- 月复盘 ≈ $2-5
- 月度总成本 ≈ $20-50

**降本方案**：
- 把 `CLAUDE_MODEL=claude-sonnet-4-6` → 成本降到 1/3
- 把 `CLAUDE_EFFORT=medium` → 再降 30%

## ⚠️ 风险声明

本系统是**研究框架与决策辅助工具**，不是投资建议。期权卖方策略尤其需要先具备：择时能力、组合保证金账户、严格止损纪律。亏钱不要找 AI 算账。
