/**
 * MonitorPanel 增强测试
 * REQ-0001-004: 性能监控仪表盘
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import MonitorPanel from './MonitorPanel';

// Mock the store
const mockStoreState = {
  liveStatus: null,
  agentsStatusData: {
    ok: true,
    gateway: { alive: true, probe: true, status: 'running' },
    agents: [
      { id: 'taizi', label: '太子', emoji: '🤴', role: '太子', status: 'running', statusLabel: '运行中' },
      { id: 'zhongshu', label: '中书省', emoji: '📜', role: '中书令', status: 'idle', statusLabel: '待命' },
    ],
    checkedAt: '2026-03-14T10:00:00Z',
  },
  officialsData: { officials: [], totals: { tasks_done: 0, cost_cny: 0 }, top_official: '' },
  loadAgentsStatus: vi.fn(),
  setModalTaskId: vi.fn(),
  toast: vi.fn(),
  wsStatus: 'connected' as const,
};

vi.mock('../store', () => ({
  useStore: (selector: (s: typeof mockStoreState) => unknown) => selector(mockStoreState),
  DEPTS: [
    { id: 'taizi', label: '太子', emoji: '🤴', role: '太子', rank: '储君' },
  ],
  isEdict: (t: { id: string }) => /^JJC-/i.test(t.id || ''),
  stateLabel: (t: { state: string }) => t.state,
}));

// Mock the API
vi.mock('../api', () => ({
  api: {
    agentWake: vi.fn().mockResolvedValue({ message: 'OK' }),
  },
}));

describe('MonitorPanel (enhanced)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render agent status panel', async () => {
    render(<MonitorPanel />);

    expect(screen.getByText(/Agent 在线状态/i)).not.toBeNull();
  });

  it('should show running agent count', async () => {
    render(<MonitorPanel />);

    expect(screen.getByText(/1 运行中/i)).not.toBeNull();
    expect(screen.getByText(/1 待命/i)).not.toBeNull();
  });

  it('should display gateway status', async () => {
    render(<MonitorPanel />);

    expect(screen.getByText(/Gateway/i)).not.toBeNull();
  });

  it('should show connection status when wsStatus is connected', async () => {
    render(<MonitorPanel />);

    // The connection status should be visible somewhere
    const connectedElements = screen.getAllByText(/已连接/i);
    expect(connectedElements.length).toBeGreaterThanOrEqual(0);
  });

  it('should display checked timestamp', async () => {
    render(<MonitorPanel />);

    expect(screen.getByText(/检测于/i)).not.toBeNull();
  });
});
