# 三省六部数据同步架构

## 数据流全景图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           OpenClaw Runtime (外部)                            │
│  ~/.openclaw/                                                               │
│  ├── openclaw.json ─────────────────────────────────────────────────────────┼──┐
│  │   └── agents.list[{id, workspace, model, subagents}]                     │  │
│  │                                                                          │  │
│  ├── agents/{id}/sessions/sessions.json ────────────────────────────────────┼──┼──┐
│  │   └── {sessionKey: {sessionId, updatedAt, aborted, tokens, ...}}        │  │  │
│  │                                                                          │  │  │
│  └── workspace-{id}/                                                        │  │  │
│      ├── SOUL.md ◄──────────────────── agents/{id}/SOUL.md (部署)           │  │  │
│      └── skills/{name}/SKILL.md                                             │  │  │
│                                                                              │  │  │
└──────────────────────────────────────────────────────────────────────────────┘  │  │
                                                                                  │  │
                    ┌─────────────────────────────────────────────────────────────┘  │
                    │                                                            │
                    ▼                                                            ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              同步脚本层 (scripts/)                                    │
│                                                                                      │
│  run_loop.sh ─── 每 15 秒执行 ──────────────────────────────────────────────────────►│
│       │                                                                              │
│       ├──► sync_agent_config.py                                                      │
│       │    └── 读取 openclaw.json + skills 目录                                       │
│       │    └── 写入 data/agent_config.json                                            │
│       │    └── 部署 SOUL.md → workspace-{id}/                                         │
│       │                                                                               │
│       ├──► sync_from_openclaw_runtime.py                                             │
│       │    └── 读取 ~/.openclaw/agents/*/sessions/sessions.json                       │
│       │    └── 构建 Task 对象 (状态映射、活动解析)                                       │
│       │    └── 合并 JJC-* 旨意任务                                                     │
│       │    └── 写入 data/tasks_source.json                                            │
│       │                                                                               │
│       ├──► sync_officials_stats.py                                                   │
│       │    └── 聚合 token 消耗、完成数、活跃度                                          │
│       │    └── 写入 data/officials_stats.json                                         │
│       │                                                                               │
│       ├──► apply_model_changes.py                                                    │
│       │    └── 读取 data/pending_model_changes.json                                   │
│       │    └── 写入 openclaw.json (模型热切换)                                         │
│       │    └── 执行 openclaw gateway restart                                          │
│       │                                                                               │
│       └──► refresh_live_data.py                                                      │
│            └── 聚合 tasks + officials + metrics                                       │
│            └── 添加心跳检测、今日统计                                                   │
│            └── 写入 data/live_status.json                                             │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              数据层 (data/)                                           │
│                                                                                      │
│  ├── tasks_source.json     ← 任务池 (JJC-* + OC-*)                                   │
│  ├── agent_config.json     ← Agent 配置缓存 (skills, model, workspace)               │
│  ├── officials_stats.json  ← Agent 统计 (tokens, 完成数, 活跃度)                      │
│  ├── live_status.json      ← 聚合实时数据 (看板 API 直接消费)                          │
│  ├── sync_status.json      ← 同步状态 (上次同步时间、耗时、错误)                        │
│  └── pending_model_changes.json  ← 待应用的模型切换请求                               │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              后端服务层                                               │
│                                                                                      │
│  dashboard/server.py (stdlib-only, 端口 7891)                                        │
│  │                                                                                   │
│  ├── GET /api/live-status      → 读取 data/live_status.json                         │
│  ├── GET /api/agent-config     → 读取 data/agent_config.json                        │
│  ├── GET /api/tasks            → 读取 data/tasks_source.json                        │
│  ├── POST /api/set-model       → 写入 data/pending_model_changes.json               │
│  ├── POST /api/task-action     → 修改 tasks_source.json (stop/cancel/resume)        │
│  ├── POST /api/scheduler-scan  → 触发巡检，自动重试卡住任务                           │
│  └── ...                                                                            │
│                                                                                      │
│  edict/backend/app/ (FastAPI v2, 可选)                                               │
│  │                                                                                   │
│  ├── Redis Event Bus                                                                 │
│  ├── WebSocket 实时推送                                                               │
│  └── PostgreSQL 持久化                                                                │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              前端展示层                                               │
│                                                                                      │
│  dashboard.html (单文件前端)                                                          │
│  │   └── 轮询 GET /api/live-status (每 5 秒)                                          │
│  │   └── 10 个功能面板 (看板、监控、奏折、模型配置...)                                   │
│                                                                                      │
│  React 前端 (edict/frontend/)                                                        │
│  │   └── Zustand 状态管理                                                             │
│  │   └── 13 个功能组件                                                                │
│  │   └── Vite 构建 → dashboard/dist/                                                 │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## 详细同步流程

### 1. 配置同步 (sync_agent_config.py)

```python
# 数据流向
~/.openclaw/openclaw.json
    │
    ▼ 读取 agents.list[]
scripts/sync_agent_config.py
    │
    ├── 读取 ~/.openclaw/workspace-{id}/skills/ (发现已安装 Skills)
    │
    ▼
data/agent_config.json
{
    "generatedAt": "2026-03-14 16:30:00",
    "defaultModel": "anthropic/claude-sonnet-4-6",
    "knownModels": [...],
    "agents": [
        {
            "id": "zhongshu",
            "label": "中书省",
            "role": "中书令",
            "duty": "起草任务令与优先级",
            "emoji": "📜",
            "model": "anthropic/claude-sonnet-4-6",
            "workspace": "~/.openclaw/workspace-zhongshu",
            "skills": [
                {"name": "code_review", "path": "...", "description": "..."}
            ],
            "allowAgents": ["menxia", "shangshu"]
        },
        ...
    ]
}
```

### 2. 会话同步 (sync_from_openclaw_runtime.py)

```python
# 数据流向
~/.openclaw/agents/{agent_id}/sessions/sessions.json
    │
    ▼ 读取所有 agent 的 sessions
scripts/sync_from_openclaw_runtime.py
    │
    ├── 构建 Task 对象 (state_from_session 映射)
    ├── 解析 JSONL 会话日志 (load_activity)
    ├── 过滤非活跃会话
    │
    ▼ 合并 JJC-* 旨意任务
data/tasks_source.json
[
    {
        "id": "OC-zhongshu-abc12345",
        "title": "中书省会话",
        "official": "中书令",
        "org": "中书省",
        "state": "Doing",
        "now": "思考中: 正在规划任务方案...",
        "activity": [...],
        "sourceMeta": {
            "agentId": "zhongshu",
            "sessionKey": "...",
            "updatedAt": 1708089600000,
            "inputTokens": 1000,
            "outputTokens": 500
        }
    },
    {
        "id": "JJC-20260314-001",
        "title": "审查代码安全性",
        "state": "Menxia",
        "flow_log": [...],
        "todos": [...],
        "progress_log": [...]
    }
]
```

### 3. 实时数据刷新 (refresh_live_data.py)

```python
# 数据流向
data/tasks_source.json + data/officials_stats.json + data/sync_status.json
    │
    ▼ 聚合 + 计算指标
scripts/refresh_live_data.py
    │
    ├── 添加心跳检测 (active/warn/stalled)
    ├── 计算今日完成数、总完成数、阻塞数
    ├── 构建历史记录
    │
    ▼
data/live_status.json
{
    "generatedAt": "2026-03-14 16:30:00",
    "officials": [...],
    "tasks": [...],  // 带 heartbeat 字段
    "history": [...],
    "metrics": {
        "officialCount": 12,
        "todayDone": 3,
        "totalDone": 15,
        "inProgress": 5,
        "blocked": 1
    },
    "syncStatus": {"ok": true, "durationMs": 45},
    "health": {"syncOk": true, "syncLatencyMs": 45}
}
```

## 前后端 API 交互

### 后端 → 前端 (读取)

| API | 数据源 | 用途 |
|-----|--------|------|
| `GET /api/live-status` | `data/live_status.json` | 看板主数据 (任务+统计+心跳) |
| `GET /api/agent-config` | `data/agent_config.json` | Agent 列表 + Skills |
| `GET /api/tasks` | `data/tasks_source.json` | 原始任务列表 |
| `GET /api/sync-status` | `data/sync_status.json` | 同步状态 |

### 前端 → 后端 (写入)

| API | 数据源 | 触发动作 |
|-----|--------|----------|
| `POST /api/set-model` | `data/pending_model_changes.json` | 模型热切换 |
| `POST /api/task-action` | `data/tasks_source.json` | 叫停/取消/恢复任务 |
| `POST /api/archive-task` | `data/tasks_source.json` | 归档任务 |

## 双向写入机制

```
┌───────────────────────────────────────────────────────────────────────┐
│                        写入场景                                        │
├───────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  1. Agent → 看板 (单向)                                                │
│     ┌─────────────┐      kanban_update.py      ┌──────────────┐       │
│     │ OpenClaw    │ ──────────────────────────►│ tasks_source │       │
│     │ Agent       │   create/state/flow/done   │ .json        │       │
│     └─────────────┘                            └──────────────┘       │
│                                                                       │
│  2. 看板 → OpenClaw (通过文件)                                         │
│     ┌─────────────┐   pending_model_changes   ┌──────────────┐       │
│     │ 前端看板    │ ──────────────────────────►│ openclaw.json│       │
│     │ (set-model) │   apply_model_changes.py  │ (model字段)  │       │
│     └─────────────┘                            └──────────────┘       │
│                                                                       │
│  3. 看板 → 任务状态 (直接)                                              │
│     ┌─────────────┐   server.py 直接修改    ┌──────────────┐         │
│     │ 前端看板    │ ────────────────────────►│ tasks_source │         │
│     │ (stop/cancel)│   + trigger refresh     │ .json        │         │
│     └─────────────┘                          └──────────────┘         │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

## 并发安全

所有 JSON 文件读写都通过 `file_lock.py` 的原子操作：

```python
# 原子读
data = atomic_json_read(path, default)

# 原子写
atomic_json_write(path, data)

# 原子更新 (读 → 修改 → 写)
def modifier(data):
    data['field'] = new_value
    return data
atomic_json_update(path, modifier, default)
```

这确保了：
- 多 Agent 同时调用 `kanban_update.py` 不会互相覆盖
- 后端 API 和同步脚本同时访问 `data/*.json` 不会冲突
