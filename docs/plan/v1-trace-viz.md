# v1-trace-viz: 追踪可视化组件

> **PRD Trace**: REQ-0001-003
> **Goal**: 实现追踪列表和树形可视化，显示 span 耗时和状态

---

## Scope

### 做什么
- 显示追踪列表（最近 100 条）
- 点击追踪显示树形结构
- 显示每个 span 的耗时和状态
- 状态用颜色区分（OK=绿色, ERROR=红色）

### 不做什么
- 不实现追踪搜索
- 不实现性能分析
- 不实现实时追踪

---

## Acceptance (DoD)

| # | 验收标准 | 验证方式 |
|---|----------|----------|
| 1 | 追踪列表正确显示 | 单元测试验证 API 调用 |
| 2 | 点击追踪显示树形结构 | 测试验证树渲染 |
| 3 | 显示每个 span 耗时和状态 | 测试验证数据显示 |
| 4 | 错误状态用红色高亮 | 测试验证样式 |

---

## Files

| 文件 | 操作 |
|------|------|
| `edict/frontend/src/api.ts` | 修改 - 添加追踪 API |
| `edict/frontend/src/components/TraceViewer.tsx` | 新增 - 追踪可视化组件 |
| `edict/frontend/src/components/TraceViewer.test.tsx` | 新增 - 组件测试 |
| `edict/frontend/src/store.ts` | 修改 - 添加追踪 Tab |

---

## Steps

### Step 1: 写失败测试 (红)

在 api.ts 中添加追踪 API 类型定义和调用函数，然后写组件测试。

### Step 2: 运行到红

```bash
cd edict/frontend && npm test -- --run
# 预期: TraceViewer 组件不存在，测试失败
```

### Step 3: 实现 (绿)

1. 添加追踪 API 函数到 api.ts
2. 创建 TraceViewer 组件
3. 在 App.tsx 中添加新 Tab

### Step 4: 运行到绿

```bash
cd edict/frontend && npm test -- --run
# 预期: all tests pass
```

### Step 5: 构建验证

```bash
cd edict/frontend && npm run build
# 预期: build success
```

---

## Risks

| 风险 | 缓解方式 |
|------|----------|
| 后端 API 未启动 | Mock 数据测试，优雅降级 |
| 追踪数据过大 | 限制显示数量 |
