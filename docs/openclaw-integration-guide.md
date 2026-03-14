# 三省六部 Edict 与 OpenClaw 整合指南

> **版本**: 1.0
> **更新日期**: 2026-03-14
> **适用环境**: macOS / Linux (Python 3.9+)

---

## 目录

1. [架构概览](#1-架构概览)
2. [前置条件](#2-前置条件)
3. [整合步骤](#3-整合步骤)
4. [配置详解](#4-配置详解)
5. [启动与验证](#5-启动与验证)
6. [数据同步机制](#6-数据同步机制)
7. [常见问题排查](#7-常见问题排查)
8. [扩展开发](#8-扩展开发)

---

## 1. 架构概览

### 1.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户交互层                                      │
│                                                                             │
│   飞书/Telegram/Signal ─────────────────────────────────────────────────►   │
│                                    │                                        │
│                                    ▼                                        │
│                           ┌─────────────────┐                               │
│                           │  OpenClaw       │                               │
│                           │  Gateway        │◄─────────────────────┐        │
│                           │  (消息路由)     │                      │        │
│                           └────────┬────────┘                      │        │
│                                    │                                │        │
│                    ┌───────────────┼───────────────┐               │        │
│                    ▼               ▼               ▼               │        │
│              ┌──────────┐   ┌──────────┐   ┌──────────┐           │        │
│              │  太子    │   │ 中书省   │   │  ...     │           │        │
│              │ Agent    │   │ Agent    │   │ 12个Agent│           │        │
│              └────┬─────┘   └────┬─────┘   └────┬─────┘           │        │
│                   │              │              │                  │        │
│                   └──────────────┼──────────────┘                  │        │
│                                  ▼                                 │        │
│                        ~/.openclaw/                                │        │
│                        ├── agents/*/sessions/                      │        │
│                        └── workspace-*/                            │        │
│                                                                     │        │
└─────────────────────────────────────────────────────────────────────┼────────┘
                                                                      │
                    ┌─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           三省六部 Edict                                      │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                        同步层 (scripts/)                              │  │
│   │                                                                     │  │
│   │   run_loop.sh ─── 每15秒 ───► sync_from_openclaw_runtime.py        │  │
│   │        │                      sync_agent_config.py                  │  │
│   │        │                      refresh_live_data.py                  │  │
│   │        │                      apply_model_changes.py                │  │
│   │        ▼                                                            │  │
│   │   data/                                                             │  │
│   │   ├── tasks_source.json      (任务池)                               │  │
│   │   ├── agent_config.json      (Agent配置)                            │  │
│   │   └── live_status.json       (看板数据)                             │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                        服务层 (dashboard/)                            │  │
│   │                                                                     │  │
│   │   server.py (port:7891)                                             │  │
│   │   ├── GET /api/live-status     → 看板数据                           │  │
│   │   ├── GET /api/agent-config    → Agent配置                          │  │
│   │   ├── POST /api/set-model      → 模型切换                           │  │
│   │   └── POST /api/task-action    → 任务操作                           │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                        前端层                                        │  │
│   │                                                                     │  │
│   │   http://127.0.0.1:7891  (dashboard.html 或 React)                  │  │
│   │   ├── 旨意看板 (Kanban)                                              │  │
│   │   ├── 省部调度 (Monitor)                                             │  │
│   │   ├── 奏折阁 (Memorials)                                             │  │
│   │   └── ... 10个功能面板                                               │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 数据流向

```
用户消息 ──► 飞书 ──► OpenClaw Gateway ──► 太子Agent
                                              │
                                              ▼
                   ┌──────────────────────────────────────────────┐
                   │              Agent 协作链                     │
                   │                                              │
                   │   太子 ──► 中书省 ──► 门下省 ──► 尚书省      │
                   │                                    │         │
                   │                              ┌─────┼─────┐   │
                   │                              ▼     ▼     ▼   │
                   │                            户部  礼部  兵部... │
                   └──────────────────────────────────────────────┘
                                              │
                                              ▼
                   ┌──────────────────────────────────────────────┐
                   │              数据同步层                       │
                   │                                              │
                   │   sessions.json ──► sync_*.py ──► data/     │
                   │                                              │
                   └──────────────────────────────────────────────┘
                                              │
                                              ▼
                   ┌──────────────────────────────────────────────┐
                   │              看板展示层                       │
                   │                                              │
                   │   server.py ──► HTTP API ──► 前端看板        │
                   │                                              │
                   └──────────────────────────────────────────────┘
```

---

## 2. 前置条件

### 2.1 系统要求

| 项目 | 最低要求 | 推荐配置 |
|------|----------|----------|
| **操作系统** | macOS 12+ / Ubuntu 20.04+ | macOS 14+ / Ubuntu 22.04+ |
| **Python** | 3.9+ | 3.11+ |
| **Node.js** | 18+ (可选，用于构建前端) | 20+ |
| **内存** | 4GB | 8GB+ |
| **磁盘** | 2GB | 5GB+ |

### 2.2 必需软件

```bash
# 1. 检查 Python 版本
python3 --version  # 需要 3.9+

# 2. 检查 OpenClaw CLI (必须已安装)
openclaw --version
# 如果未安装，访问 https://openclaw.ai 获取安装指南

# 3. 检查 OpenClaw 配置文件是否存在
ls ~/.openclaw/openclaw.json
# 如果不存在，先运行 openclaw init 完成初始化
```

### 2.3 OpenClaw 初始化 (如未完成)

```bash
# 初始化 OpenClaw
openclaw init

# 配置 LLM Provider (以 Anthropic 为例)
openclaw config set anthropic_api_key "sk-ant-..."

# 启动 Gateway
openclaw gateway start

# 验证 Gateway 运行
curl http://127.0.0.1:7890/health
```

---

## 3. 整合步骤

### 3.1 步骤一：克隆仓库

```bash
# 克隆 Edict 仓库
git clone https://github.com/cft0808/edict.git
cd edict

# 查看当前版本
git log -1 --oneline
```

### 3.2 步骤二：执行安装脚本

```bash
# 赋予执行权限
chmod +x install.sh

# 执行安装 (自动完成以下操作)
./install.sh
```

**安装脚本执行内容**:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         install.sh 执行流程                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Step 1: 检查依赖                                                       │
│  ├── openclaw CLI 是否存在                                              │
│  ├── python3 版本检查                                                   │
│  └── ~/.openclaw/openclaw.json 是否存在                                 │
│                                                                         │
│  Step 2: 备份已有数据                                                   │
│  └── ~/.openclaw/backups/pre-install-YYYYMMDD-HHMMSS/                   │
│                                                                         │
│  Step 3: 创建 12 个 Agent Workspace                                     │
│  ├── ~/.openclaw/workspace-taizi/                                       │
│  ├── ~/.openclaw/workspace-zhongshu/                                    │
│  ├── ~/.openclaw/workspace-menxia/                                      │
│  ├── ~/.openclaw/workspace-shangshu/                                    │
│  └── ... (共12个)                                                       │
│                                                                         │
│  Step 4: 部署 SOUL.md 人格模板                                          │
│  └── agents/*/SOUL.md → ~/.openclaw/workspace-*/SOUL.md                 │
│                                                                         │
│  Step 5: 注册 Agents 到 openclaw.json                                   │
│  └── 更新 agents.list 配置                                              │
│                                                                         │
│  Step 6: 初始化 data/ 目录                                              │
│  ├── data/tasks_source.json                                             │
│  ├── data/agent_config.json                                             │
│  └── data/live_status.json                                              │
│                                                                         │
│  Step 7: 构建前端 (可选，需要 Node.js)                                   │
│  └── cd edict/frontend && npm install && npm run build                  │
│                                                                         │
│  Step 8: 首次数据同步                                                   │
│  └── python3 scripts/sync_agent_config.py                               │
│  └── python3 scripts/refresh_live_data.py                               │
│                                                                         │
│  Step 9: 重启 OpenClaw Gateway                                          │
│  └── openclaw gateway restart                                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.3 步骤三：验证安装

```bash
# 检查 Agent 是否已注册
cat ~/.openclaw/openclaw.json | python3 -c "
import json, sys
cfg = json.load(sys.stdin)
agents = cfg.get('agents', {}).get('list', [])
for ag in agents:
    print(f\"  - {ag['id']}: {ag.get('workspace', 'N/A')}\")"
```

**预期输出**:
```
  - taizi: /Users/xxx/.openclaw/workspace-taizi
  - zhongshu: /Users/xxx/.openclaw/workspace-zhongshu
  - menxia: /Users/xxx/.openclaw/workspace-menxia
  - shangshu: /Users/xxx/.openclaw/workspace-shangshu
  - hubu: /Users/xxx/.openclaw/workspace-hubu
  - libu: /Users/xxx/.openclaw/workspace-libu
  - bingbu: /Users/xxx/.openclaw/workspace-bingbu
  - xingbu: /Users/xxx/.openclaw/workspace-xingbu
  - gongbu: /Users/xxx/.openclaw/workspace-gongbu
  - libu_hr: /Users/xxx/.openclaw/workspace-libu_hr
  - zaochao: /Users/xxx/.openclaw/workspace-zaochao
```

### 3.4 步骤四：启动服务

```bash
# 终端 1: 启动数据刷新循环 (后台运行)
nohup bash scripts/run_loop.sh > /tmp/sansheng_loop.log 2>&1 &

# 检查是否启动成功
tail -f /tmp/sansheng_loop.log

# 终端 2: 启动看板服务器
python3 dashboard/server.py

# 终端 3: (可选) 查看 OpenClaw Gateway 日志
tail -f /tmp/openclaw/openclaw-*.log
```

### 3.5 步骤五：访问看板

```bash
# 打开浏览器
open http://127.0.0.1:7891
```

**看到以下界面表示整合成功**:
- 旨意看板 (Kanban) 显示任务列表
- 省部调度 (Monitor) 显示 Agent 状态
- 官员总览 (Officials) 显示 12 个 Agent

---

## 4. 配置详解

### 4.1 openclaw.json 核心配置

**文件位置**: `~/.openclaw/openclaw.json`

```json
{
  "version": "1.0",
  "agents": {
    "defaults": {
      "model": {
        "primary": "anthropic/claude-sonnet-4-6"
      }
    },
    "list": [
      {
        "id": "taizi",
        "workspace": "/Users/xxx/.openclaw/workspace-taizi",
        "model": {"primary": "anthropic/claude-sonnet-4-6"},
        "subagents": {
          "allowAgents": ["zhongshu"]
        }
      },
      {
        "id": "zhongshu",
        "workspace": "/Users/xxx/.openclaw/workspace-zhongshu",
        "subagents": {
          "allowAgents": ["menxia", "shangshu"]
        }
      },
      {
        "id": "menxia",
        "workspace": "/Users/xxx/.openclaw/workspace-menxia",
        "subagents": {
          "allowAgents": ["shangshu", "zhongshu"]
        }
      },
      {
        "id": "shangshu",
        "workspace": "/Users/xxx/.openclaw/workspace-shangshu",
        "subagents": {
          "allowAgents": ["zhongshu", "menxia", "hubu", "libu", "bingbu", "xingbu", "gongbu", "libu_hr"]
        }
      }
      // ... 其他六部配置
    ]
  }
}
```

### 4.2 权限矩阵配置

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Agent 调用权限矩阵                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   From ↓ \ To →  太子  中书  门下  尚书  户  礼  兵  刑  工  吏          │
│   ─────────────────────────────────────────────────────────────────────│
│   太子            —     ✅                              禁止跨级       │
│   中书省          ✅    —     ✅    ✅                                  │
│   门下省                ✅    —     ✅                                  │
│   尚书省                ✅    ✅    —     ✅  ✅  ✅  ✅  ✅  ✅         │
│   六部+吏部                                     ✅  只能汇报           │
│                                                                         │
│   规则：                                                                │
│   1. 太子只能调中书省 (不能越级)                                         │
│   2. 中书省可调门下省(审议)和尚书省(咨询)                                 │
│   3. 门下省可回调中书省(封驳)和尚书省(派发)                               │
│   4. 尚书省可调六部执行任务                                               │
│   5. 六部只能向尚书省汇报                                                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.3 SOUL.md 人格模板结构

**文件位置**: `agents/{agent_id}/SOUL.md`

```markdown
# [官职名称]

你是[角色描述]。

## 核心职责
1. 职责1
2. 职责2
3. 职责3

## 工作流程
### 收到任务时
1. 步骤1
2. 步骤2

## 输出规范
- 格式要求
- 必须包含的字段

## 看板命令
\`\`\`bash
python3 scripts/kanban_update.py create ...
python3 scripts/kanban_update.py progress ...
\`\`\`

## 语气
[风格描述]
```

### 4.4 数据目录结构

**文件位置**: `data/`

```
data/
├── tasks_source.json       # 任务池 (同步脚本写入)
├── agent_config.json       # Agent 配置缓存
├── live_status.json        # 看板聚合数据
├── sync_status.json        # 同步状态
├── officials_stats.json    # Agent 统计
├── pending_model_changes.json  # 待应用的模型变更
└── model_change_log.json   # 模型变更历史
```

---

## 5. 启动与验证

### 5.1 启动命令速查

```bash
# ═══════════════════════════════════════════════════════════════
# 方式 1: 前台启动 (推荐调试时使用)
# ═══════════════════════════════════════════════════════════════

# 终端 1: 数据刷新循环
bash scripts/run_loop.sh

# 终端 2: 看板服务器
python3 dashboard/server.py --port 7891

# ═══════════════════════════════════════════════════════════════
# 方式 2: 后台启动 (推荐生产使用)
# ═══════════════════════════════════════════════════════════════

# 启动数据刷新 (nohup)
nohup bash scripts/run_loop.sh > /tmp/sansheng_loop.log 2>&1 &
echo $! > /tmp/sansheng_loop.pid

# 启动看板服务器 (nohup)
nohup python3 dashboard/server.py > /tmp/sansheng_server.log 2>&1 &
echo $! > /tmp/sansheng_server.pid

# ═══════════════════════════════════════════════════════════════
# 停止服务
# ═══════════════════════════════════════════════════════════════

kill $(cat /tmp/sansheng_loop.pid) 2>/dev/null
kill $(cat /tmp/sansheng_server.pid) 2>/dev/null
```

### 5.2 验证检查清单

```bash
# ✅ 检查 1: OpenClaw Gateway 运行
curl -s http://127.0.0.1:7890/health | python3 -m json.tool

# ✅ 检查 2: Edict 看板 API 响应
curl -s http://127.0.0.1:7891/api/live-status | python3 -m json.tool | head -20

# ✅ 检查 3: Agent 配置已同步
curl -s http://127.0.0.1:7891/api/agent-config | python3 -c "
import json, sys
cfg = json.load(sys.stdin)
print(f'Agent 数量: {len(cfg.get(\"agents\", []))}')"

# ✅ 检查 4: 数据刷新循环运行
ps aux | grep run_loop.sh | grep -v grep

# ✅ 检查 5: 文件锁工作正常
python3 -c "
from scripts.file_lock import atomic_json_write, atomic_json_read
from pathlib import Path
test_file = Path('/tmp/test_lock.json')
atomic_json_write(test_file, {'test': 'ok'})
print('文件锁测试:', atomic_json_read(test_file))"

# ✅ 检查 6: 浏览器访问
echo "打开 http://127.0.0.1:7891 验证看板界面"
```

### 5.3 首次下旨测试

通过飞书/Telegram 向太子发送测试消息：

```
传旨：帮我写一个 Hello World Python 脚本
```

**预期行为**:
1. 太子回复"已收到旨意"
2. 看板上出现新任务 (JJC-*)
3. 任务流转: 太子 → 中书省 → 门下省 → ...
4. 最终完成，太子回复皇上

---

## 6. 数据同步机制

### 6.1 同步脚本详解

#### sync_from_openclaw_runtime.py

**职责**: 将 OpenClaw 会话转换为看板任务

**数据流**:
```
~/.openclaw/agents/{id}/sessions/sessions.json
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ sync_from_openclaw_runtime.py                           │
│                                                         │
│ 1. 遍历所有 Agent 目录                                   │
│ 2. 读取 sessions.json                                   │
│ 3. 构建任务对象:                                         │
│    - id: OC-{agent_id}-{session_id[:8]}                 │
│    - state: Doing/Review/Next/Blocked                   │
│    - activity: 最近10条活动                              │
│ 4. 过滤:                                                │
│    - 排除24小时前的会话                                   │
│    - 只保留 Doing/Blocked                               │
│ 5. 合并 JJC-* 旨意任务                                   │
│ 6. 写入 data/tasks_source.json                          │
└─────────────────────────────────────────────────────────┘
```

#### sync_agent_config.py

**职责**: 同步 Agent 配置并部署 SOUL.md

```python
# 核心逻辑
def main():
    # 1. 读取 openclaw.json
    cfg = json.loads(OPENCLAW_CFG.read_text())

    # 2. 构建 Agent 配置
    for ag in cfg['agents']['list']:
        agent_config = {
            'id': ag['id'],
            'label': ID_LABEL[ag['id']]['label'],
            'model': normalize_model(ag.get('model')),
            'workspace': ag['workspace'],
            'skills': get_skills(ag['workspace']),
            'allowAgents': ag['subagents']['allowAgents']
        }

    # 3. 部署 SOUL.md
    deploy_soul_files()

    # 4. 同步 scripts/ 到各 workspace
    sync_scripts_to_workspaces()
```

### 6.2 同步间隔配置

**文件**: `scripts/run_loop.sh`

```bash
# 默认配置
INTERVAL="${1:-15}"        # 数据刷新间隔: 15秒
SCAN_INTERVAL="${2:-120}"  # 巡检间隔: 120秒
SCRIPT_TIMEOUT=30          # 脚本超时: 30秒

# 自定义配置 (启动时指定)
bash scripts/run_loop.sh 30 300  # 30秒刷新，5分钟巡检
```

### 6.3 并发安全机制

**文件**: `scripts/file_lock.py`

```python
# 原子写入 (防止数据损坏)
def atomic_json_write(path, data):
    temp_path = path.with_suffix('.tmp')
    temp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    temp_path.replace(path)  # 原子操作

# 原子更新 (读-改-写)
def atomic_json_update(path, modifier, default):
    data = atomic_json_read(path, default)
    data = modifier(data)
    atomic_json_write(path, data)
```

---

## 7. 常见问题排查

### 7.1 问题诊断流程图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           问题诊断流程                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  问题: 看板无数据                                                        │
│  │                                                                      │
│  ├──► 检查 OpenClaw Gateway                                             │
│  │    └── curl http://127.0.0.1:7890/health                             │
│  │         ├── 失败 → 启动 Gateway: openclaw gateway start              │
│  │         └── 成功 ↓                                                   │
│  │                                                                      │
│  ├──► 检查同步脚本                                                       │
│  │    └── cat /tmp/sansheng_loop.log | tail -20                         │
│  │         ├── 有错误 → 修复错误                                         │
│  │         └── 无错误 ↓                                                 │
│  │                                                                      │
│  ├──► 检查数据文件                                                       │
│  │    └── ls -la data/*.json                                            │
│  │         ├── 文件不存在 → 手动同步: python3 scripts/sync_*.py         │
│  │         └── 文件存在 ↓                                               │
│  │                                                                      │
│  └──► 检查看板服务器                                                     │
│       └── curl http://127.0.0.1:7891/api/live-status                    │
│            ├── 失败 → 重启服务器: python3 dashboard/server.py            │
│            └── 成功 → 检查前端浏览器控制台                                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7.2 常见错误及解决方案

#### 错误 1: `exec format error`

```bash
# 症状
exec /usr/local/bin/python3: exec format error

# 原因: Docker 镜像架构不匹配

# 解决方案
docker run --platform linux/amd64 -p 7891:7891 cft0808/sansheng-demo
```

#### 错误 2: 任务总超时

```bash
# 症状
任务状态卡在 Doing，最终超时

# 诊断
# 1. 检查 Agent 是否活跃
curl -s http://127.0.0.1:7891/api/agents-status | python3 -m json.tool

# 2. 检查 Gateway 日志
grep -i "error\|fail" /tmp/openclaw/openclaw-*.log | tail -20

# 3. 手动触发重试
curl -X POST http://127.0.0.1:7891/api/scheduler-scan \
  -H 'Content-Type: application/json' \
  -d '{"thresholdSec":60}'
```

#### 错误 3: Skill 下载失败

```bash
# 症状
python3 scripts/skill_manager.py import-official-hub 报错

# 原因: 网络问题

# 解决方案
# 1. 测试网络
curl -I https://raw.githubusercontent.com/openclaw-ai/skills-hub/main/code_review/SKILL.md

# 2. 使用代理
export https_proxy=http://your-proxy:port
python3 scripts/skill_manager.py import-official-hub --agents zhongshu
```

#### 错误 4: 看板显示异常

```bash
# 症状
看板界面空白或数据显示异常

# 诊断
# 1. 检查浏览器控制台 (F12)
# 2. 检查 API 响应
curl -s http://127.0.0.1:7891/api/live-status | python3 -m json.tool

# 3. 强制刷新数据
python3 scripts/refresh_live_data.py
```

### 7.3 日志位置

| 组件 | 日志位置 |
|------|----------|
| 数据刷新循环 | `/tmp/sansheng_loop.log` |
| 看板服务器 | 终端输出 / `/tmp/sansheng_server.log` |
| OpenClaw Gateway | `/tmp/openclaw/openclaw-*.log` |
| 同步状态 | `data/sync_status.json` |

---

## 8. 扩展开发

### 8.1 添加新 Agent

```bash
# 1. 创建人格模板
mkdir -p agents/new_agent
cat > agents/new_agent/SOUL.md << 'EOF'
# 新部门 · 职责描述

你是新部门的负责人。

## 核心职责
1. 职责1
2. 职责2

## 看板命令
\`\`\`bash
python3 scripts/kanban_update.py progress ...
\`\`\`
EOF

# 2. 注册到 ID_LABEL (sync_agent_config.py)
# 编辑 scripts/sync_agent_config.py:
ID_LABEL['new_agent'] = {
    'label': '新部门',
    'role': '官职',
    'duty': '职责描述',
    'emoji': '🆕'
}

# 3. 配置权限 (install.sh)
# 编辑 install.sh 的 AGENTS 数组:
{"id": "new_agent", "subagents": {"allowAgents": ["shangshu"]}}

# 4. 重新安装
./install.sh
```

### 8.2 添加新 Skill

```bash
# 方式 1: CLI 添加远程 Skill
python3 scripts/skill_manager.py add-remote \
  --agent zhongshu \
  --name custom_skill \
  --source https://raw.githubusercontent.com/your-repo/skills/main/custom_skill/SKILL.md \
  --description "自定义技能"

# 方式 2: 手动创建本地 Skill
mkdir -p ~/.openclaw/workspace-zhongshu/skills/custom_skill
cat > ~/.openclaw/workspace-zhongshu/skills/custom_skill/SKILL.md << 'EOF'
# 自定义技能

技能描述...

## 使用场景
- 场景1
- 场景2

## 执行步骤
1. 步骤1
2. 步骤2
EOF

# 刷新配置
python3 scripts/sync_agent_config.py
```

### 8.3 自定义同步逻辑

```bash
# 创建自定义同步脚本
cat > scripts/custom_sync.py << 'EOF'
#!/usr/bin/env python3
"""自定义数据同步脚本"""
import json, pathlib
from file_lock import atomic_json_write

DATA = pathlib.Path(__file__).parent.parent / 'data'

def main():
    # 1. 从外部系统获取数据
    external_tasks = fetch_external_tasks()

    # 2. 合并到任务池
    tasks = atomic_json_read(DATA / 'tasks_source.json', [])
    tasks.extend(external_tasks)
    atomic_json_write(DATA / 'tasks_source.json', tasks)

    print(f'同步完成: {len(external_tasks)} 条任务')

def fetch_external_tasks():
    # 实现你的数据获取逻辑
    return []

if __name__ == '__main__':
    main()
EOF

chmod +x scripts/custom_sync.py

# 添加到 run_loop.sh
# 编辑 scripts/run_loop.sh，在循环中添加:
safe_run "$SCRIPT_DIR/custom_sync.py"
```

### 8.4 扩展看板 API

```python
# 编辑 dashboard/server.py

# 添加新端点示例
elif path == '/api/custom-endpoint' and method == 'GET':
    # 读取自定义数据
    custom_data = read_json(DATA / 'custom_data.json', {})
    self._send_json({'ok': True, 'data': custom_data})

elif path == '/api/custom-action' and method == 'POST':
    body = self._read_json()
    # 处理请求
    result = process_custom_action(body)
    self._send_json({'ok': True, 'result': result})
```

---

## 附录

### A. 命令速查表

| 命令 | 用途 |
|------|------|
| `./install.sh` | 一键安装 |
| `bash scripts/run_loop.sh` | 启动数据刷新 |
| `python3 dashboard/server.py` | 启动看板服务器 |
| `python3 scripts/sync_agent_config.py` | 手动同步 Agent 配置 |
| `python3 scripts/sync_from_openclaw_runtime.py` | 手动同步会话数据 |
| `python3 scripts/kanban_update.py create ...` | 创建任务 |
| `python3 scripts/kanban_update.py progress ...` | 更新进展 |
| `python3 scripts/skill_manager.py list-remote` | 列出远程 Skills |

### B. 文件位置速查

| 文件 | 位置 |
|------|------|
| OpenClaw 配置 | `~/.openclaw/openclaw.json` |
| Agent Workspace | `~/.openclaw/workspace-{id}/` |
| 会话数据 | `~/.openclaw/agents/{id}/sessions/sessions.json` |
| 任务池 | `data/tasks_source.json` |
| Agent 配置 | `data/agent_config.json` |
| 看板数据 | `data/live_status.json` |

### C. 端口说明

| 端口 | 服务 |
|------|------|
| 7890 | OpenClaw Gateway |
| 7891 | Edict 看板服务器 |
| 5173 | Vite 开发服务器 (前端开发) |

---

**文档版本**: 1.0
**最后更新**: 2026-03-14
