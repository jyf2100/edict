# v1-ws-reconnect: WebSocket 自动重连优化

> **PRD Trace**: REQ-0001-001
> **Goal**: 实现 WebSocket 断线后自动重连，使用指数退避策略，提升连接稳定性

---

## Scope

### 做什么
- 实现指数退避重连策略 (2^n 秒，最多 32 秒)
- 添加连接状态指示器 UI 组件
- 最多重试 5 次
- 重连成功后恢复订阅

### 不做什么
- 不实现心跳检测（已有）
- 不实现离线消息队列
- 不实现多端同步

---

## Acceptance (DoD)

| # | 验收标准 | 验证方式 |
|---|----------|----------|
| 1 | 断线后自动重连 | 手动关闭后端，观察控制台日志 |
| 2 | 使用指数退避 (2, 4, 8, 16, 32 秒) | 单元测试验证间隔计算 |
| 3 | 最多重试 5 次后放弃 | 单元测试 |
| 4 | 显示连接状态指示器 | E2E 测试 |
| 5 | 重连成功后恢复订阅 | 集成测试 |

---

## Files

| 文件 | 操作 |
|------|------|
| `edict/frontend/src/api.ts` | 修改 - 添加指数退避逻辑 |
| `edict/frontend/src/components/ConnectionStatus.tsx` | 新增 - 状态指示器组件 |
| `edict/frontend/src/store.ts` | 修改 - 集成状态指示器 |
| `edict/frontend/src/__tests__/api.test.ts` | 新增 - 单元测试 |

---

## Steps

### Step 1: 写失败测试 (红)

```typescript
// edict/frontend/src/__tests__/api.test.ts
describe('WebSocket Reconnect', () => {
  it('should use exponential backoff for retries', () => {
    // 测试指数退避计算
    expect(calculateReconnectDelay(0)).toBe(2000);  // 2^1 = 2s
    expect(calculateReconnectDelay(1)).toBe(4000);  // 2^2 = 4s
    expect(calculateReconnectDelay(2)).toBe(8000);  // 2^3 = 8s
    expect(calculateReconnectDelay(3)).toBe(16000); // 2^4 = 16s
    expect(calculateReconnectDelay(4)).toBe(32000); // 2^5 = 32s
    expect(calculateReconnectDelay(5)).toBe(32000); // max 32s
  });

  it('should give up after 5 retries', () => {
    const ws = createMockWS();
    ws.simulateClose();
    // 验证第 6 次不会尝试重连
    expect(ws.reconnectAttempts).toBeLessThanOrEqual(5);
  });
});
```

### Step 2: 运行到红

```bash
cd edict/frontend && npm test -- --run
# 预期: calculateReconnectDelay is not defined
```

### Step 3: 实现 (绿)

1. 添加 `calculateReconnectDelay` 函数
2. 修改 `connectWS` 使用指数退避
3. 添加 `_wsRetryCount` 变量

### Step 4: 运行到绿

```bash
cd edict/frontend && npm test -- --run
# 预期: all tests pass
```

### Step 5: 添加 ConnectionStatus 组件

### Step 6: E2E 测试

---

## Risks

| 风险 | 缓解方式 |
|------|----------|
| 后端长时间不可用 | 5 次后放弃，显示离线状态 |
| 网络抖动 | 指数退避避免频繁重连 |
