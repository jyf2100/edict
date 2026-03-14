# v1-index: P2 级前端改进

> **版本**: v1
> **创建时间**: 2026-03-14
> **关联 PRD**: PRD-0001

---

## 愿景

为三省六部 Edict 系统提供完整的前端功能，实现：
1. 稳定的 WebSocket 实时连接
2. 可视化权限管理
3. 追踪链路展示
4. 性能监控

---

## 里程碑

| # | 名称 | 范围 | DoD | 状态 |
|---|------|------|-----|------|
| M1 | WebSocket 重连 | REQ-0001-001 | 重连测试通过 | ✅ done |
| M2 | 权限界面 | REQ-0001-002 | E2E 权限操作 | ✅ done |
| M3 | 追踪可视化 | REQ-0001-003 | 追踪树渲染正确 | ✅ done |
| M4 | 监控仪表盘 | REQ-0001-004 | 指标实时更新 | ✅ done |

---

## 计划索引

- [v1-ws-reconnect.md](./v1-ws-reconnect.md) - WebSocket 重连优化
- [v1-permission-ui.md](./v1-permission-ui.md) - 权限管理界面
- [v1-trace-viz.md](./v1-trace-viz.md) - 追踪可视化
- [v1-monitor.md](./v1-monitor.md) - 监控仪表盘

---

## 追溯矩阵

| Req ID | PRD | Plan | 测试 | 状态 |
|--------|-----|------|------|------|
| REQ-0001-001 | PRD-0001 §1 | v1-ws-reconnect | api.test.ts (8 tests) | ✅ |
| REQ-0001-002 | PRD-0001 §2 | v1-permission-ui | PermissionMatrix.test.tsx (5 tests) | ✅ |
| REQ-0001-003 | PRD-0001 §3 | v1-trace-viz | TraceViewer.test.tsx (5 tests) | ✅ |
| REQ-0001-004 | PRD-0001 §4 | v1-monitor | MonitorPanel.test.tsx (5 tests) | ✅ |

---

## ECN 索引

(暂无)

---

## 差异列表

### v1 回顾 (2026-03-14)

**已满足**:
- REQ-0001-001: WebSocket 自动重连 - 8 个单元测试全绿
- REQ-0001-002: 权限管理界面 - 5 个组件测试全绿
- REQ-0001-003: 追踪可视化 - 5 个组件测试全绿
- REQ-0001-004: 性能监控增强 - 5 个组件测试全绿
- 集成测试通过: 23 tests, build success

**未满足**:
- 无

**新增发现**:
- MonitorPanel 已有完整功能，只需增强 WebSocket 状态显示
- 后端 API 已完备 (auth_matrix, tracing)，前端集成顺畅
