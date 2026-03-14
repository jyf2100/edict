# P0 级改进 - 实时推送与反向控制

## 概述

本次改进实现了两个核心功能：

1. **WebSocket 实时推送** - 替代 15 秒轮询，实现毫秒级数据同步
2. **反向控制通道** - 看板操作能远程停止运行中的 Agent

## 架构图

```
┌─────────────────┐                      ┌─────────────────┐
│   Frontend      │◄───── WebSocket ────►│   FastAPI       │
│   (React)       │      Port 8000       │   Backend       │
│                 │                      │                 │
│   api.ts ───────┤                      │   websocket.py  │
│   store.ts      │                      │   event_bus.py  │
└─────────────────┘                      └────────┬────────┘
                                                  │
                                         ┌────────▼────────┐
                                         │     Redis       │
                                         │   Pub/Sub       │
                                         └────────┬────────┘
                                                  │
         ┌────────────────────────────────────────┼────────────────────────────────────────┐
         │                                        │                                        │
         ▼                                        ▼                                        ▼
┌─────────────────┐                      ┌─────────────────┐                      ┌─────────────────┐
│ refresh_live    │                      │ openclaw_control│                      │  Dashboard      │
│ _data.py        │                      │ _listener.py    │                      │  server.py      │
│ (事件发布)       │                      │ (控制监听)       │                      │  (HTTP API)     │
└─────────────────┘                      └─────────────────┘                      └─────────────────┘
         │                                        │
         │ 发布 sync.complete                      │ 监听 edict:control:*
         ▼                                        ▼
   前端自动刷新                              任务状态变更
```

## 快速开始

### 1. 启动 Redis

```bash
# Docker 方式
docker run -d --name edict-redis -p 6379:6379 redis:7-alpine

# 或 Homebrew 方式
brew install redis && brew services start redis
```

### 2. 启动后端服务

```bash
# 启动控制监听器 (后台运行)
python3 scripts/openclaw_control_listener.py &

# 启动 Dashboard API
python3 dashboard/server.py &

# 启动 FastAPI 后端 (需要 Python 3.10+)
cd edict/backend && uvicorn app.main:app --port 8000 &
```

### 3. 启动前端

```bash
cd edict/frontend && npm run dev
```

### 4. 验证

打开浏览器控制台，应看到：

```
[WS] Connected to ws://127.0.0.1:8000/ws
[Store] WebSocket connected, reducing polling interval
```

## WebSocket 实时推送

### 事件类型

| 事件 | 触发时机 | 数据 |
|------|----------|------|
| `sync.complete` | 数据刷新完成 | `{record_count, duration_ms, ...}` |
| `task.status` | 任务状态变更 | `{task_id, state, agent_id}` |
| `agent.heartbeat` | Agent 心跳 | `{agent_id, status}` |

### 前端集成

```typescript
// api.ts
import { connectWS, subscribeWS, sendWS } from './api';

// 连接 WebSocket
connectWS(() => {
  console.log('WebSocket connected');
});

// 订阅事件
const unsubscribe = subscribeWS((event) => {
  if (event.topic === 'sync.complete') {
    // 刷新数据
    loadLiveStatus();
  }
});

// 发送消息
sendWS({ type: 'ping' });
```

### 后端发布事件

```python
from event_publisher import publish_event, publish_sync_complete

# 发布同步完成事件
publish_sync_complete(record_count=10, duration_ms=50)

# 发布任务状态变更
publish_event('task.status', {
    'task_id': 'JJC-001',
    'state': 'Doing',
    'agent_id': 'zhongshu'
})
```

## 反向控制通道

### 控制指令格式

```json
{
  "action": "stop",      // stop | cancel | resume
  "task_id": "JJC-001",
  "reason": "皇上叫停",
  "request_id": "req-001"
}
```

### 发送控制指令

```bash
# 通过 Redis 发布
python3 -c "
import redis, json
r = redis.from_url('redis://localhost:6379/0', decode_responses=True)
r.publish('edict:control:task', json.dumps({
    'action': 'stop',
    'task_id': 'JJC-001',
    'reason': '测试'
}))
"
```

### Agent 中断检查

在 Agent SOUL.md 中已添加中断检查点，Agent 应在关键操作前检查：

```bash
# 检查任务是否应该中断
python3 scripts/check_interrupt.py JJC-001

# 返回值说明：
# continue → 继续执行
# stop     → 任务被叫停
# cancel   → 任务被取消
```

### 中断处理流程

```bash
# 1. 检查中断
if ! python3 scripts/check_interrupt.py JJC-xxx >/dev/null 2>&1; then
    # 2. 保存进度
    python3 scripts/kanban_update.py progress JJC-xxx "⏸️ 收到中断信号" "..."

    # 3. 停止执行
    echo "⏸️ 任务已暂停"
    exit 0
fi

# 4. 继续正常流程
```

## 测试

### 单元测试

```bash
python3 tests/test_event_publisher.py -v
python3 tests/test_check_interrupt.py -v
```

### 端到端测试

```bash
# 需要 Redis 运行
python3 scripts/test_e2e_websocket.py
```

## 故障排除

### WebSocket 连接失败

1. 检查 Redis 是否运行：`docker ps | grep redis`
2. 检查端口是否被占用：`lsof -i :8000`
3. 检查防火墙设置

### 事件未推送

1. 检查 Redis Pub/Sub：`redis-cli` → `PSUBSCRIBE edict:pubsub:*`
2. 检查事件发布器日志：`refresh_live_data.py` 应显示 "Event publisher connected"
3. 检查 WebSocket 连接状态：浏览器控制台应显示 `[WS] Connected`

### 控制指令无响应

1. 检查控制监听器是否运行：`ps aux | grep openclaw_control_listener`
2. 检查任务是否存在：`cat data/tasks_source.json | grep JJC-xxx`
3. 检查日志输出

## 文件清单

| 文件 | 用途 |
|------|------|
| `edict/frontend/src/api.ts` | WebSocket 客户端 |
| `edict/frontend/src/store.ts` | 状态管理 + 实时更新 |
| `scripts/event_publisher.py` | 事件发布器 |
| `scripts/openclaw_control_listener.py` | 控制监听器 |
| `scripts/check_interrupt.py` | 中断检查工具 |
| `scripts/test_e2e_websocket.py` | 端到端测试 |
| `agents/*/SOUL.md` | Agent 中断检查点 |
