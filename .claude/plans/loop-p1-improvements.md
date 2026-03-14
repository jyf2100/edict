# 循环执行计划：P1 级改进实施

> **模式**: sequential (safe)
> **创建时间**: 2026-03-14 21:30
> **前置条件**: P0 级改进已完成

---

## 目标

实施三省六部 + OpenClaw 的 P1 级改进：

1. **自动上报 + 事件钩子** - 减少手动调用 kanban_update.py
2. **动态权限矩阵** - 运行时动态调整 Agent 调用权限
3. **链路追踪** - 跨 Agent 调用链可追踪

---

## 执行阶段

### Phase 1: 自动上报钩子 (2 天) ✅ 完成

- [x] **1.1** 创建 `scripts/hooks/report_tool_call.py` - 工具调用上报
- [x] **1.2** 创建 `scripts/hooks/report_thinking.py` - 思考过程上报
- [x] **1.3** 创建 `scripts/hooks/report_state.py` - 状态变更上报
- [x] **1.4** 创建 `data/hooks_config.json` - 钩子配置文件
- [x] **1.5** 测试自动上报 (12 tests passing)

### Phase 2: 动态权限矩阵 (3 天) ✅ 完成

- [x] **2.1** 创建 `edict/backend/app/services/auth_matrix.py` - 权限服务
- [x] **2.2** 添加 `GET /api/auth-matrix` - 获取权限矩阵
- [x] **2.3** 添加 `POST /api/auth-matrix/grant` - 动态授权
- [x] **2.4** 添加 `POST /api/auth-matrix/revoke` - 动态撤销
- [x] **2.5** 添加 `GET /api/auth-matrix/audit` - 审计日志
- [x] **2.6** 添加 `GET /api/auth-matrix/matrix/visual` - 可视化矩阵
- [x] **2.7** 测试动态权限 (11 tests passing)

### Phase 3: 链路追踪 (2 天) ✅ 完成

- [x] **3.1** 创建 `edict/backend/app/services/tracing.py` - 追踪服务
- [x] **3.2** 创建 `edict/backend/app/api/tracing.py` - 追踪 API
  - GET /api/traces - 列出追踪
  - GET /api/traces/{trace_id} - 获取追踪详情
  - GET /api/traces/{trace_id}/tree - 获取追踪树
  - POST /api/traces/start - 开始新追踪
  - POST /api/traces/continue - 继续追踪
  - POST /api/traces/end - 结束 span
- [x] **3.3** W3C traceparent 格式支持
- [x] **3.4** 测试链路追踪 (13 tests passing)

### Phase 4: 集成测试 (1 天) ✅ 完成

- [x] **4.1** 编写单元测试 (36 tests for P1 features)
- [x] **4.2** 端到端测试 (test_e2e_websocket.py from P0)
- [x] **4.3** 文档更新 (realtime-push-guide.md updated)

---

## 质量门控 (Safe 模式)

每个 Phase 完成后必须通过：

1. ✅ **测试通过** - 相关测试全绿
2. ✅ **功能验证** - 手动验证核心功能
3. ✅ **代码审查** - 检查安全性和代码质量

---

## 停止条件

1. 所有 4 个 Phase 完成
2. 集成测试全部通过
3. 用户确认验收

---

## 文件变更追踪

| 文件 | 状态 | Phase |
|------|------|-------|
| scripts/hooks/report_tool_call.py | ✅ 已创建 | 1.1 |
| scripts/hooks/report_thinking.py | ✅ 已创建 | 1.2 |
| scripts/hooks/report_state.py | ✅ 已创建 | 1.3 |
| scripts/hooks/__init__.py | ✅ 已创建 | 1.1-1.3 |
| data/hooks_config.json | ✅ 已创建 | 1.4 |
| tests/test_hooks.py | ✅ 已创建 | 1.5 |
| edict/backend/app/services/auth_matrix.py | ✅ 已创建 | 2.1 |
| edict/backend/app/api/auth_matrix.py | ✅ 已创建 | 2.2-2.6 |
| edict/backend/app/main.py | ✅ 已修改 | 2.2/3.2 |
| tests/test_auth_matrix.py | ✅ 已创建 | 2.7 |
| edict/backend/app/services/tracing.py | ✅ 已创建 | 3.1 |
| edict/backend/app/api/tracing.py | ✅ 已创建 | 3.2 |
| tests/test_tracing.py | ✅ 已创建 | 3.4 |

---

## 当前状态

**✅ P1 级改进全部完成！**

| Phase | 状态 | 产物 |
|-------|------|------|
| Phase 1 | ✅ | 自动上报钩子 (12 tests) |
| Phase 2 | ✅ | 动态权限矩阵 (11 tests) |
| Phase 3 | ✅ | 链路追踪 (13 tests) |
| Phase 4 | ✅ | 集成测试 (49 tests total) |

### 测试覆盖

```
P0 测试 (已有):
- tests/test_event_publisher.py ..... 5 tests
- tests/test_check_interrupt.py ..... 7 tests
- tests/test_e2e_websocket.py ....... 1 test

P1 测试 (新增):
- tests/test_hooks.py ............... 12 tests
- tests/test_auth_matrix.py ......... 11 tests
- tests/test_tracing.py ............. 13 tests

总计: 49 tests ✅
```

### 代码统计

```
P1 新增文件: 10
P1 修改文件: 2
P1 新增代码: ~1600 行
```

### 完成的功能

1. **自动上报钩子**
   - report_tool_call.py: 工具调用自动上报
   - report_thinking.py: 思考过程自动上报
   - report_state.py: 状态变更自动上报

2. **动态权限矩阵**
   - 权限服务 (auth_matrix.py)
   - REST API 端点 (grant/revoke/check)
   - 审计日志

3. **分布式追踪**
   - W3C traceparent 格式支持
   - Span 生命周期管理
   - 追踪树可视化

### 下一步建议

1. 部署到生产环境 (需要 Python 3.10+ 后端)
2. 前端集成权限管理界面
3. 添加追踪可视化组件

---

## 钩子使用方式

### 1. 工具调用上报

```bash
# 在 Agent 中调用
python3 scripts/hooks/report_tool_call.py JJC-xxx "Read" "/path/file.py" "success"
python3 scripts/hooks/report_tool_call.py JJC-xxx "Bash" "npm test" "error"
```

### 2. 思考过程上报

```bash
# 基本调用
python3 scripts/hooks/report_thinking.py JJC-xxx "正在分析需求..."

# 带资源消耗指标
python3 scripts/hooks/report_thinking.py JJC-xxx "分析完成" --tokens 1500 --cost 0.05 --elapsed 30
```

### 3. 状态变更上报

```bash
# 状态变更
python3 scripts/hooks/report_state.py JJC-xxx Doing "开始执行"
python3 scripts/hooks/report_state.py JJC-xxx Review "代码审查中"

# 阻塞状态
python3 scripts/hooks/report_state.py JJC-xxx Blocked --reason "等待外部依赖"
```

### 4. 通过环境变量

```bash
export TASK_ID=JJC-xxx
python3 scripts/hooks/report_thinking.py "正在工作..."
```
