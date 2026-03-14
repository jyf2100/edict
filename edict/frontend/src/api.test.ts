/**
 * WebSocket 重连策略测试
 * REQ-0001-001: WebSocket 自动重连
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// 直接导入函数（测试将失败，因为函数还未导出）
import {
  calculateReconnectDelay,
  ConnectionStatus,
  getWSRetryCount,
  resetWSRetryCount,
} from './api';

// ── 测试指数退避计算函数 ──

describe('calculateReconnectDelay', () => {
  it('should return 2000ms for first retry (2^1 = 2s)', () => {
    expect(calculateReconnectDelay(0)).toBe(2000);
  });

  it('should return 4000ms for second retry (2^2 = 4s)', () => {
    expect(calculateReconnectDelay(1)).toBe(4000);
  });

  it('should return 8000ms for third retry (2^3 = 8s)', () => {
    expect(calculateReconnectDelay(2)).toBe(8000);
  });

  it('should return 16000ms for fourth retry (2^4 = 16s)', () => {
    expect(calculateReconnectDelay(3)).toBe(16000);
  });

  it('should return 32000ms for fifth retry (2^5 = 32s)', () => {
    expect(calculateReconnectDelay(4)).toBe(32000);
  });

  it('should cap at 32000ms (max delay)', () => {
    expect(calculateReconnectDelay(5)).toBe(32000);
    expect(calculateReconnectDelay(10)).toBe(32000);
    expect(calculateReconnectDelay(100)).toBe(32000);
  });
});

// ── 测试最大重试次数 ──

describe('WebSocket max retries', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    resetWSRetryCount();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should track retry count correctly', () => {
    expect(getWSRetryCount()).toBe(0);
  });
});

// ── 测试连接状态枚举 ──

describe('ConnectionStatus', () => {
  it('should have correct status values', () => {
    expect(ConnectionStatus.CONNECTED).toBe('connected');
    expect(ConnectionStatus.CONNECTING).toBe('connecting');
    expect(ConnectionStatus.DISCONNECTED).toBe('disconnected');
    expect(ConnectionStatus.RECONNECTING).toBe('reconnecting');
  });
});
