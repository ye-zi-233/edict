<h1 align="center">⚔️ Edict · Multi-Agent Orchestration</h1>

<p align="center">
  <strong>I modeled an AI multi-agent system after China's 1,300-year-old imperial governance.<br>Turns out, ancient bureaucracy understood separation of powers better than modern AI frameworks.</strong>
</p>

<p align="center">
  <sub>12 AI agents (11 business roles + 1 compatibility role) form the Three Departments & Six Ministries: Queen triages, Planning proposes, Review vetoes, Dispatch assigns, Ministries execute.<br>Built-in <b>institutional review gates</b> that CrewAI doesn't have. A <b>real-time dashboard</b> that AutoGen doesn't have.</sub>
</p>

<p align="center">
  <a href="#-quick-start">🚀 Quick Start</a> ·
  <a href="#-architecture">🏛️ Architecture</a> ·
  <a href="#-features">📋 Features</a> ·
  <a href="README.md">中文</a> ·
  <a href="CONTRIBUTING.md">Contributing</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/OpenClaw-Required-blue?style=flat-square" alt="OpenClaw">
  <img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Agents-12_Specialized-8B5CF6?style=flat-square" alt="Agents">
  <img src="https://img.shields.io/badge/Dashboard-Real--time-F59E0B?style=flat-square" alt="Dashboard">
  <img src="https://img.shields.io/badge/License-MIT-22C55E?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/Zero_Deps-stdlib_only-EC4899?style=flat-square" alt="Zero Dependencies">
</p>

---

---

## 💡 The Idea

Most multi-agent frameworks let AI agents talk freely, producing opaque results you can't audit or intervene in. **Edict** takes a radically different approach — borrowing the governance system that ran China for 1,400 years:

```
You (Master) → Queen (Triage) → Planning Dept → Review Dept → Dispatch Dept → 6 Ministries → Report Back
   主人              公主               中书省          门下省         尚书省           六部          回奏
```

This isn't a cute metaphor. It's **real separation of powers** for AI:

- **Queen (公主)** triages messages — casual chat gets auto-replied, real commands become tasks
- **Planning (中书省)** breaks your command into actionable sub-tasks
- **Review (门下省)** audits the plan — can reject and force re-planning
- **Dispatch (尚书省)** assigns approved tasks to specialist ministries
- **7 Ministries** execute in parallel, each with distinct expertise
- **Data sanitization** auto-strips file paths, metadata, and junk from task titles
- Everything flows through a **real-time dashboard** you can monitor and intervene

---

## 🤔 Why Edict?

> **"Instead of one AI doing everything wrong, 9 specialized agents check each other's work."**

| | CrewAI | MetaGPT | AutoGen | **Edict** |
|---|:---:|:---:|:---:|:---:|
| **Built-in review/veto** | ❌ | ⚠️ | ⚠️ | **✅ Dedicated reviewer** |
| **Real-time Kanban** | ❌ | ❌ | ❌ | **✅ 10-panel dashboard** |
| **Task intervention** | ❌ | ❌ | ❌ | **✅ Stop / Cancel / Resume** |
| **Full audit trail** | ⚠️ | ⚠️ | ❌ | **✅ Memorial archive** |
| **Agent health monitoring** | ❌ | ❌ | ❌ | **✅ Heartbeat detection** |
| **Hot-swap LLM models** | ❌ | ❌ | ❌ | **✅ From the dashboard** |
| **Skill management** | ❌ | ❌ | ❌ | **✅ View / Add skills** |
| **News aggregation** | ❌ | ❌ | ❌ | **✅ Daily digest + webhook** |
| **Setup complexity** | Med | High | Med | **Low · Docker Compose** |

> **Core differentiator: Institutional review + Full observability + Real-time intervention**

<details>
<summary><b>🔍 Why the "Review Department" is the killer feature (click to expand)</b></summary>

<br>

CrewAI and AutoGen agents work in a **"done, ship it"** mode — no one checks output quality. It's like a company with no QA department where engineers push code straight to production.

Edict's **Review Department (门下省)** exists specifically for this:

- 📋 **Audit plan quality** — Is the Planning Department's decomposition complete and sound?
- 🚫 **Veto subpar output** — Not a warning. A hard reject that forces re-planning.
- 🔄 **Mandatory rework loop** — Nothing passes until it meets standards.

This isn't an optional plugin — **it's part of the architecture**. Every command must pass through Review. No exceptions.

This is why Edict produces reliable results on complex tasks: there's a mandatory quality gate before anything reaches execution. Emperor Taizong figured this out 1,300 years ago — **unchecked power inevitably produces errors**.

</details>

---

## ✨ Features

### 🏛️ Twelve-Department Agent Architecture
- **Queen** (公主) message triage — auto-reply casual chat, create tasks for real commands
- **Three Departments** (Planning · Review · Dispatch) for governance
- **Seven Ministries** (Finance · Docs · Engineering · Compliance · Infrastructure · HR + Briefing) for execution
- Strict permission matrix — who can message whom is enforced
- Each agent: own workspace, own skills, own LLM model
- **Data sanitization** — auto-strips file paths, metadata, invalid prefixes from titles/remarks

### 📋 Command Center Dashboard (10 Panels)

| Panel | Description |
|-------|------------|
| 📋 **Edicts Kanban** | Task cards by state, filters, search, heartbeat badges, stop/cancel/resume |
| 🔭 **Department Monitor** | Pipeline visualization, distribution charts, health cards |
| 📜 **Memorial Archive** | Auto-generated archives with 5-phase timeline |
| 📜 **Edict Templates** | 9 presets with parameter forms, cost estimates, one-click dispatch |
| 👥 **Officials Overview** | Token leaderboard, activity stats |
| 📰 **Daily Briefing** | Auto-curated news, subscription management, Feishu push |
| ⚙️ **Model Config** | Per-agent LLM switching, automatic Gateway restart |
| 🛠️ **Skills Config** | View installed skills, add new ones |
| 💬 **Sessions** | Live session monitoring with channel labels |
| 🎬 **Court Ceremony** | Immersive daily opening animation with stats |

---

## 🖼️ Screenshots

### Edicts Kanban
![Kanban](docs/screenshots/01-kanban-main.png)

<details>
<summary>📸 More screenshots</summary>

### Agent Monitor
![Monitor](docs/screenshots/02-monitor.png)

### Task Detail
![Detail](docs/screenshots/03-task-detail.png)

### Model Config
![Models](docs/screenshots/04-model-config.png)

### Skills
![Skills](docs/screenshots/05-skills-config.png)

### Officials
![Officials](docs/screenshots/06-official-overview.png)

### Sessions
![Sessions](docs/screenshots/07-sessions.png)

### Memorials Archive
![Memorials](docs/screenshots/08-memorials.png)

### Command Templates
![Templates](docs/screenshots/09-templates.png)

### Daily Briefing
![Briefing](docs/screenshots/10-morning-briefing.png)

### Court Ceremony
![Ceremony](docs/screenshots/11-ceremony.png)

</details>

---

## 🚀 Quick Start

**Prerequisites:**
- [OpenClaw](https://openclaw.ai) Gateway running and network-accessible
- Gateway HTTP API enabled (`gateway.http.endpoints.responses.enabled = true`)
- Docker + Docker Compose

```bash
git clone https://github.com/cft0808/edict.git
cd edict
cp .env.example .env
# Edit .env — set OPENCLAW_HOME, OPENCLAW_GATEWAY_URL, etc.
docker compose up -d
```

Open http://localhost:7891

#### Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `PUID` / `PGID` | Container user UID/GID, must match OpenClaw directory owner | `1000` |
| `OPENCLAW_HOME` | OpenClaw home directory on host | `~/.openclaw` |
| `OPENCLAW_GATEWAY_URL` | Gateway address (use `host.docker.internal` from container) | `http://host.docker.internal:18789` |
| `OPENCLAW_GATEWAY_TOKEN` | Gateway auth token, leave empty if no auth | empty |
| `DASHBOARD_PORT` | Dashboard port | `7891` |
| `SYNC_INTERVAL` | Data refresh interval (seconds) | `15` |

> NAS users: set `PUID`/`PGID` to match the UID/GID of the OpenClaw directory owner (check via `id` command or NAS admin panel).

---

## 🏛️ Architecture

```
                           ┌───────────────────────────────────┐
                           │         👑 Master (You)            │
                           │     Feishu · Telegram · Signal     │
                           └─────────────────┬─────────────────┘
                                             │ Issue edict
                           ┌─────────────────▼─────────────────┐
                           │     👑 Queen (公主)                │
                           │   Triage: chat → reply / cmd → task │
                           └─────────────────┬─────────────────┘
                                             │ Forward edict
                           ┌─────────────────▼─────────────────┐
                           │      📜 Planning Dept (中书省)      │
                           │     Receive → Plan → Decompose      │
                           └─────────────────┬─────────────────┘
                                             │ Submit for review
                           ┌─────────────────▼─────────────────┐
                           │       🔍 Review Dept (门下省)       │
                           │     Audit → Approve / Reject 🚫     │
                           └─────────────────┬─────────────────┘
                                             │ Approved ✅
                           ┌─────────────────▼─────────────────┐
                           │      📮 Dispatch Dept (尚书省)      │
                           │   Assign → Coordinate → Collect     │
                           └───┬──────┬──────┬──────┬──────┬───┘
                               │      │      │      │      │
                         ┌─────▼┐ ┌───▼───┐ ┌▼─────┐ ┌───▼─┐ ┌▼─────┐
                         │💰 Fin.│ │📝 Docs│ │⚔️ Eng.│ │⚖️ Law│ │🔧 Ops│
                         │ 户部  │ │ 礼部  │ │ 兵部  │ │ 刑部 │ │ 工部  │
                         └──────┘ └──────┘ └──────┘ └─────┘ └──────┘
                                                               ┌──────┐
                                                               │📋 HR  │
                                                               │ 吏部  │
                                                               └──────┘
```

### Agent Roles

| Dept | Agent ID | Role | Expertise |
|------|----------|------|-----------|
| 👑 **Queen** | `gongzhu` | Triage, summarize | Chat detection, intent extraction |
| 📜 **Planning** | `zhongshu` | Receive, plan, decompose | Requirements, architecture |
| 🔍 **Review** | `menxia` | Audit, gatekeep, veto | Quality, risk, standards |
| 📮 **Dispatch** | `shangshu` | Assign, coordinate, collect | Scheduling, tracking |
| 💰 **Finance** | `hubu` | Data, resources, accounting | Data processing, reports |
| 📝 **Documentation** | `libu` | Docs, standards, reports | Tech writing, API docs |
| ⚔️ **Engineering** | `bingbu` | Code, algorithms, checks | Development, code review |
| ⚖️ **Compliance** | `xingbu` | Security, compliance, audit | Security scanning |
| 🔧 **Infrastructure** | `gongbu` | CI/CD, deploy, tooling | Docker, pipelines |
| 📋 **HR** | `libu_hr` | Agent management, training | Registration, permissions |
| 🌅 **Briefing** | `zaochao` | Daily briefing, news | Scheduled reports, summaries |
| 🔮 **Nüwa** | `nvwa` | Soul guardian, agent tuning | SOUL.md management, prompt optimization, new agent creation |

### Permission Matrix

| From ↓ \ To → | Queen | Planning | Review | Dispatch | Ministries |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **Queen** | — | ✅ | | | |
| **Planning** | ✅ | — | ✅ | ✅ | |
| **Review** | | ✅ | — | ✅ | |
| **Dispatch** | | ✅ | ✅ | — | ✅ all |
| **Ministries** | | | | ✅ | |

### State Machine

```
Master → Queen Triage → Planning → Review → Assigned → Executing → ✅ Done
                              ↑          │                       │
                              └── Veto ──┘              Blocked ──
```

---

## 📁 Project Structure

```
edict/
├── agents/                     # 12 agent personality templates (SOUL.md)
│   ├── gongzhu/               #   Queen (triage)
│   ├── zhongshu/               #   Planning Dept
│   ├── menxia/                 #   Review Dept
│   ├── shangshu/               #   Dispatch Dept
│   ├── hubu/ libu/ bingbu/     #   Finance / Docs / Engineering
│   ├── xingbu/ gongbu/         #   Compliance / Infrastructure
│   ├── libu_hr/                #   HR Dept
│   ├── zaochao/                #   Morning Briefing
│   └── nvwa/                   #   Nüwa · Soul Guardian (meta-agent)
├── edict/frontend/             # React 18 frontend (Vite + TypeScript + Zustand)
│   ├── src/components/         # 13 UI components
│   ├── src/api.ts              # API layer
│   ├── src/store.ts            # State management (Zustand)
│   └── src/index.css           # Styles (CSS variables theme)
├── dashboard/
│   ├── dist/                   # React build output (npm run build)
│   ├── dashboard.html          # Legacy dashboard (deprecated, kept for reference)
│   └── server.py               # API server (stdlib, zero deps)
├── scripts/                    # Data sync & automation scripts
│   ├── kanban_update.py        #   Kanban CLI with data sanitization (~300 lines)
│   └── ...                     #   fetch_morning_news, sync, screenshots, etc.
├── tests/                      # E2E tests
│   └── test_e2e_kanban.py      #   Kanban sanitization tests (17 assertions)
├── data/                       # Runtime data (gitignored)
├── docs/                       # Documentation + screenshots
├── Dockerfile                  # Docker image (dashboard + sync)
├── docker-compose.yaml          # Docker Compose orchestration
├── .env.example                # Docker deployment config template
└── LICENSE                     # MIT
```

---

## 🔧 Technical Highlights

| | |
|---|---|
| **React 18 Frontend** | TypeScript + Vite + Zustand, 13 components |
| **stdlib Backend** | `server.py` on `http.server`, zero dependencies |
| **Agent Thinking Visible** | Real-time display of agent thinking, tool calls, results |
| **Docker Deploy** | `docker compose up -d` launches all services |
| **15s Auto-sync** | Live data refresh with countdown |
| **Daily Ceremony** | Immersive opening animation |

---

## 🗺️ Roadmap

> Full roadmap with contribution opportunities: [ROADMAP.md](ROADMAP.md)

### Phase 1 — Core Architecture ✅
- [x] Twelve-department agent architecture + permissions
- [x] Queen triage layer (chat vs task auto-routing)
- [x] Real-time dashboard (10 panels)
- [x] Task stop / cancel / resume
- [x] Memorial archive (5-phase timeline)
- [x] Edict template library (9 presets)
- [x] Court ceremony animation
- [x] Daily news + Feishu webhook push
- [x] Hot-swap LLM models + skill management
- [x] Officials overview + token stats
- [x] Session monitoring
- [x] Edict data sanitization (title/remark cleaning, dirty data rejection)
- [x] Duplicate task overwrite protection
- [x] E2E kanban tests (17 assertions)

### Phase 2 — Institutional Depth 🚧
- [ ] Imperial approval mode (human-in-the-loop)
- [ ] Merit/demerit ledger (agent scoring)
- [ ] Express courier (inter-agent message visualization)
- [ ] Imperial Archives (knowledge base + citation)

### Phase 3 — Ecosystem
- [x] Docker Compose full deployment
- [ ] Notion / Linear adapters
- [ ] Annual review (yearly performance reports)
- [ ] Mobile responsive + PWA
- [ ] ClawHub marketplace listing

---

## 🤝 Contributing

All contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md)

- 🎨 **UI** — themes, responsiveness, animations
- 🤖 **New agents** — specialized roles
- 📦 **Skills** — ministry-specific packages
- 🔗 **Integrations** — Notion · Jira · Linear · GitHub Issues
- 🌐 **i18n** — Japanese · Korean · Spanish
- 📱 **Mobile** — responsive, PWA

---

## � Examples

The `examples/` directory contains real end-to-end use cases:

| Example | Command | Departments |
|---------|---------|-------------|
| [Competitive Analysis](examples/competitive-analysis.md) | "Analyze CrewAI vs AutoGen vs LangGraph" | Planning→Review→Finance+Engineering+Docs |
| [Code Review](examples/code-review.md) | "Review this FastAPI code for security issues" | Planning→Review→Engineering+Compliance |
| [Weekly Report](examples/weekly-report.md) | "Generate this week's engineering team report" | Planning→Review→Finance+Docs |

Each case includes: Full command → Planning proposal → Review feedback → Ministry outputs → Final report.

---

## 📄 License

[MIT](LICENSE) · Built by the [OpenClaw](https://openclaw.ai) community

---

<p align="center">
  <sub>If this project made you smile, give it a ⭐</sub><br><br>
  <strong>⚔️ Governing AI with the wisdom of ancient empires</strong><br>
  <sub>以古制御新技，以智慧驾驭 AI</sub>
</p>

[![Star History Chart](https://api.star-history.com/svg?repos=cft0808/edict&type=Date)](https://star-history.com/#cft0808/edict&Date)
