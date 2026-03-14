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
| M2 | 权限界面 | REQ-0001-002 | E2E 权限操作 | ⏳ todo |
| M3 | 追踪可视化 | REQ-0001-003 | 追踪树渲染正确 | ⏳ todo |
| M4 | 监控仪表盘 | REQ-0001-004 | 指标实时更新 | ⏳ todo |

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
| REQ-0001-002 | PRD-0001 §2 | v1-permission-ui | e2e/permissions.spec.ts | ⏳ |
| REQ-0001-003 | PRD-0001 §3 | v1-trace-viz | e2e/traces.spec.ts | ⏳ |
| REQ-0001-004 | PRD-0001 §4 | v1-monitor | e2e/monitor.spec.ts | ⏳ |

---

## ECN 索引

(暂无)

---

## 差异列表

(执行过程中记录)
