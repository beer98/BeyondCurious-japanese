# pipboy-ai-vault

我的 AI 知识仓库 + 自动化工具集。两部分：

```
/
├── apps/                       ← 自动化工具（定时跑）
│   └── bottleneck-hunter/      ← 美股每日自进化扫描系统
│
├── knowledge/                  ← 长期沉淀的知识
│   ├── books/                  ← 开源 AI 书籍源稿
│   ├── courses/                ← AI 赋能投资研究课程
│   └── reader-companion/       ← 《动手做 AI Agent》书籍配套
│
└── .github/workflows/          ← GitHub Actions cron 配置
```

## apps · 自动化工具

### 🎯 [bottleneck-hunter](apps/bottleneck-hunter/) - 美股每日自进化扫描

参考 Serenity (@aleabitoreddit) 供应链瓶颈思维方式的美股研究系统。GitHub Actions
工作日盘前自动跑 4 阶段循环：

```
A 复盘昨日 → B 蒸馏规则 → C 今日扫描 → D 红队自审 → git commit
```

成本 ~$1-5/月（DeepSeek API）。详见 [apps/bottleneck-hunter/README.md](apps/bottleneck-hunter/README.md)。

## knowledge · 长期知识

| 路径 | 内容 |
|---|---|
| [`knowledge/books/`](knowledge/books/) | 开源 AI 书籍源稿（《OpenClaw 完全指南》《OPC 2.0 时代》） |
| [`knowledge/courses/`](knowledge/courses/) | AI 赋能投资研究课程资料（含模拟尽调资料包） |
| [`knowledge/reader-companion/`](knowledge/reader-companion/) | 《动手做 AI Agent：零基础玩转智能体》配套代码 |

## 结构原则

- **`apps/`** 放会动的东西（代码、定时任务、产出物归档）
- **`knowledge/`** 放不太动的东西（书稿、课程、参考资料）
- 每个 app 的方法论 + 代码 + 产出都在自己文件夹里，独立可读

## 开发

仓库同时是 Obsidian vault（`.obsidian/`）和 git 仓库。新加内容时：
- 工具类（带定时任务 / 自动化）→ `apps/<name>/`
- 知识类（笔记 / 教程 / 参考）→ `knowledge/<category>/`
