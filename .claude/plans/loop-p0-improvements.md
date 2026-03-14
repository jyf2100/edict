# 循环执行计划：P0 级改进实施

> **模式**: sequential (safe)
> **创建时间**: 2026-03-14 17:40
> **预计工时**: 5 天

---

## 目标

实施三省六部 + OpenClaw 的 P0 级核心改进：

1. **双向实时同步** - WebSocket 替代 15 秒轮询
2. **任务控制反向通道** - 看板操作能停止运行中的 Agent

---

## 执行阶段

### Phase 1: 基础设施 (0.5 天) ✅ 完成

- [x] **1.1** 添加 Redis 到 docker-compose.yml (已存在)
- [x] **1.2** 更新 edict/backend/requirements.txt (已存在)
- [x] **1.3** 测试 Redis 连接

### Phase 2: WebSocket 实时推送 (2 天) ✅ 完成

- [x] **2.1** 创建 `edict/backend/app/api/websocket.py` (已存在)
- [x] **2.2** 创建 `edict/backend/app/services/event_publisher.py` (已存在 event_bus.py)
- [x] **2.3** 修改 `edict/frontend/src/api.ts` 添加 WebSocket ✅
- [x] **2.4** 修改 `edict/frontend/src/store.ts` 接收实时更新 ✅
- [x] **2.5** 创建 `scripts/event_publisher.py` 并修改 `scripts/refresh_live_data.py` 发布事件到 Redis ✅
- [x] **2.6** 测试实时同步 ✅ (端到端测试通过)

### Phase 3: 反向控制通道 (1.5 天)

- [x] **3.1** 创建 `edict/backend/app/services/task_control.py` (已存在)
- [x] **3.2** 增强 `dashboard/server.py` 的 task-action API (已存在)
- [x] **3.3** 创建 `scripts/openclaw_control_listener.py` ✅
- [ ] **3.4** 更新 Agent SOUL.md 添加中断检查点
- [ ] **3.5** 测试控制指令 (需要 Redis 运行)

### Phase 4: 集成测试 (1 天)

- [ ] **4.1** 编写单元测试
- [ ] **4.2** 端到端测试
- [ ] **4.3** 文档更新

---

## 质量门控 (Safe 模式)

每个 Phase 完成后必须通过：

1. ✅ **测试通过** - `pytest tests/` 无失败
2. ✅ **类型检查** - `mypy edict/backend/` 无错误
3. ✅ **代码审查** - 检查安全性和代码质量
4. ✅ **功能验证** - 手动验证核心功能

---

## 停止条件

1. 所有 4 个 Phase 完成
2. 集成测试全部通过
3. 用户确认验收

---

## 检查点命令

```bash
# 查看当前进度
cat .claude/plans/loop-p0-improvements.md

# 运行测试
cd edict/backend && pytest

# 启动服务验证
docker compose up -d redis
python3 dashboard/server.py

# 启动 FastAPI 后端
cd edict/backend && uvicorn app.main:app --port 8000

# 停止循环
/loop-stop
```

---

## 文件变更追踪

| 文件 | 状态 | Phase |
|------|------|-------|
| docker-compose.yml | ✅ 已存在 | 1.1 |
| edict/backend/requirements.txt | ✅ 已存在 | 1.2 |
| edict/backend/app/api/websocket.py | ✅ 已存在 | 2.1 |
| edict/backend/app/services/event_bus.py | ✅ 已存在 | 2.2 |
| edict/frontend/src/api.ts | ✅ 已修改 | 2.3 |
| edict/frontend/src/store.ts | ✅ 已修改 | 2.4 |
| edict/frontend/.env.development | ✅ 已创建 | 2.3 |
| edict/frontend/.env.production | ✅ 已创建 | 2.3 |
| scripts/event_publisher.py | ✅ 已创建 | 2.5 |
| scripts/refresh_live_data.py | ✅ 已修改 | 2.5 |
| scripts/openclaw_control_listener.py | ✅ 已创建 | 3.3 |
| agents/*/SOUL.md | 待修改 | 3.4 |
| scripts/test_ws_server.py | ✅ 已创建 | 测试工具 |

---

## 当前状态

**Phase 2 完成**: WebSocket 实时推送 ✅
- ✅ 前端 WebSocket 客户端已实现
- ✅ 同步脚本事件发布器已创建
- ✅ 端到端测试通过 (Redis + WebSocket)

**Phase 3 进行中**: 反向控制通道
- ✅ 控制监听器已创建
- ⏳ Agent 中断检查点 (待 Agent SOUL.md 更新)

**下一步**:
1. 更新 Agent SOUL.md 添加中断检查点
2. 完成集成测试
3. 更新文档
