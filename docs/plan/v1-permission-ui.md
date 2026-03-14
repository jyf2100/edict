# v1-permission-ui: 权限管理前端界面

> **PRD Trace**: REQ-0001-002
> **Goal**: 实现可视化的权限矩阵管理界面，支持授权/撤销操作和审计日志查看

---

## Scope

### 做什么
- 显示权限矩阵（网格视图）
- 点击单元格授权/撤销
- 显示审计日志
- 操作后实时刷新（无需手动刷新页面）

### 不做什么
- 不实现批量操作
- 不实现权限模板
- 不实现导出功能

---

## Acceptance (DoD)

| # | 验收标准 | 验证方式 |
|---|----------|----------|
| 1 | 权限矩阵正确显示 | 单元测试验证 API 调用 |
| 2 | 点击单元格可授权/撤销 | E2E 测试模拟点击 |
| 3 | 操作后数据实时更新 | 测试验证状态更新 |
| 4 | 审计日志显示最近 100 条 | 测试验证日志渲染 |

---

## Files

| 文件 | 操作 |
|------|------|
| `edict/frontend/src/api.ts` | 修改 - 添加权限 API |
| `edict/frontend/src/components/PermissionMatrix.tsx` | 新增 - 权限矩阵组件 |
| `edict/frontend/src/components/PermissionMatrix.test.tsx` | 新增 - 组件测试 |
| `edict/frontend/src/store.ts` | 修改 - 添加权限状态 |

---

## Steps

### Step 1: 写失败测试 (红)

在 api.ts 中添加权限 API 类型定义和调用函数，然后写组件测试。

### Step 2: 运行到红

```bash
cd edict/frontend && npm test -- --run
# 预期: PermissionMatrix 组件不存在，测试失败
```

### Step 3: 实现 (绿)

1. 添加权限 API 函数到 api.ts
2. 创建 PermissionMatrix 组件
3. 添加权限状态到 store.ts
4. 在 App.tsx 中添加新 Tab

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
| 权限矩阵过大 | 分页或限制显示数量 |
