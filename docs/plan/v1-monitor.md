# v1-monitor: 性能监控仪表盘

> **PRD Trace**: REQ-0001-004
> **Goal**: 显示 Agent 活跃状态、WebSocket 连接数、API 响应时间

---

## Scope

### 做什么
- 显示 Agent 活跃状态
- 显示 WebSocket 连接状态
- 显示系统健康状态
- 指标每 5 秒自动刷新

### 不做什么
- 不实现历史数据查询
- 不实现告警功能
- 不实现导出功能

---

## Acceptance (DoD)

| # | 验收标准 | 验证方式 |
|---|----------|----------|
| 1 | Agent 状态正确显示 | 测试验证 API 调用 |
| 2 | WebSocket 连接状态显示 | 测试验证状态渲染 |
| 3 | 指标每 5 秒自动刷新 | 测试验证定时器 |
| 4 | 异常状态用红色高亮 | 测试验证样式 |

---

## Files

| 文件 | 操作 |
|------|------|
| `edict/frontend/src/components/MonitorDashboard.tsx` | 新增 - 监控仪表盘组件 |
| `edict/frontend/src/components/MonitorDashboard.test.tsx` | 新增 - 组件测试 |

---

## Steps

### Step 1: 写失败测试 (红)

创建 MonitorDashboard 组件测试。

### Step 2: 运行到红

```bash
cd edict/frontend && npm test -- --run
# 预期: MonitorDashboard 组件不存在，测试失败
```

### Step 3: 实现 (绿)

1. 创建 MonitorDashboard 组件
2. 集成到 App.tsx

### Step 4: 运行到绿

```bash
cd edict/frontend && npm test -- --run
# 预期: all tests pass
```

---

## Risks

| 风险 | 缓解方式 |
|------|----------|
| 后端 API 未启动 | 使用现有 API，优雅降级 |
