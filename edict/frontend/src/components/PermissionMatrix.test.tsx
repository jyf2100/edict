/**
 * PermissionMatrix 组件测试
 * REQ-0001-002: 权限管理前端界面
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { PermissionMatrix } from './PermissionMatrix';

// Mock the API
vi.mock('../api', () => ({
  api: {
    visualMatrix: vi.fn(),
    grantPermission: vi.fn(),
    revokePermission: vi.fn(),
    auditLog: vi.fn(),
  },
}));

import { api } from '../api';

const mockApi = api as unknown as {
  visualMatrix: ReturnType<typeof vi.fn>;
  grantPermission: ReturnType<typeof vi.fn>;
  revokePermission: ReturnType<typeof vi.fn>;
  auditLog: ReturnType<typeof vi.fn>;
};

describe('PermissionMatrix', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render loading state initially', () => {
    mockApi.visualMatrix.mockImplementation(() => new Promise(() => {})); // Never resolves
    mockApi.auditLog.mockResolvedValue({ count: 0, entries: [] });

    render(<PermissionMatrix />);
    // Check that loading text appears somewhere
    const loadingText = screen.queryByText(/加载中/i);
    expect(loadingText).not.toBeNull();
  });

  it('should render permission matrix after loading', async () => {
    mockApi.visualMatrix.mockResolvedValue({
      agents: [
        { id: 'taizi', name: '太子' },
        { id: 'zhongshu', name: '中书省' },
      ],
      matrix: [
        { from: 'taizi', from_name: '太子', zhongshu: '✅' },
        { from: 'zhongshu', from_name: '中书省', taizi: '❌' },
      ],
    });
    mockApi.auditLog.mockResolvedValue({ count: 0, entries: [] });

    render(<PermissionMatrix />);

    await waitFor(() => {
      // Use getAllByText since '太子' appears multiple times (header and row)
      const taiziElements = screen.getAllByText('太子');
      expect(taiziElements.length).toBeGreaterThan(0);
      const zhongshuElements = screen.getAllByText('中书省');
      expect(zhongshuElements.length).toBeGreaterThan(0);
    });
  });

  it('should call grant when clicking denied cell', async () => {
    mockApi.visualMatrix.mockResolvedValue({
      agents: [
        { id: 'taizi', name: '太子' },
        { id: 'zhongshu', name: '中书省' },
      ],
      matrix: [
        { from: 'taizi', from_name: '太子', taizi: '—', zhongshu: '❌' },
        { from: 'zhongshu', from_name: '中书省', taizi: '✅', zhongshu: '—' },
      ],
    });
    mockApi.grantPermission.mockResolvedValue({
      success: true,
      granted: true,
      message: 'Granted',
    });
    mockApi.auditLog.mockResolvedValue({ count: 0, entries: [] });

    render(<PermissionMatrix />);

    await waitFor(() => {
      expect(screen.getAllByText('太子').length).toBeGreaterThan(0);
    });

    // Find and click the denied cell (❌)
    const deniedCell = screen.getByText('❌');
    fireEvent.click(deniedCell);

    await waitFor(() => {
      expect(mockApi.grantPermission).toHaveBeenCalledWith('taizi', 'zhongshu');
    });
  });

  it('should call revoke when clicking granted cell', async () => {
    mockApi.visualMatrix.mockResolvedValue({
      agents: [
        { id: 'taizi', name: '太子' },
        { id: 'zhongshu', name: '中书省' },
      ],
      matrix: [
        { from: 'taizi', from_name: '太子', taizi: '—', zhongshu: '✅' },
        { from: 'zhongshu', from_name: '中书省', taizi: '❌', zhongshu: '—' },
      ],
    });
    mockApi.revokePermission.mockResolvedValue({
      success: true,
      revoked: true,
      message: 'Revoked',
    });
    mockApi.auditLog.mockResolvedValue({ count: 0, entries: [] });

    render(<PermissionMatrix />);

    await waitFor(() => {
      expect(screen.getAllByText('太子').length).toBeGreaterThan(0);
    });

    // Find and click the granted cell (✅)
    const grantedCell = screen.getByText('✅');
    fireEvent.click(grantedCell);

    await waitFor(() => {
      expect(mockApi.revokePermission).toHaveBeenCalledWith('taizi', 'zhongshu');
    });
  });

  it('should display audit log entries when tab clicked', async () => {
    mockApi.visualMatrix.mockResolvedValue({
      agents: [],
      matrix: [],
    });
    mockApi.auditLog.mockResolvedValue({
      count: 2,
      entries: [
        {
          timestamp: '2026-03-14T10:00:00Z',
          action: 'grant',
          from_agent: 'taizi',
          to_agent: 'zhongshu',
          reason: '测试授权',
        },
        {
          timestamp: '2026-03-14T09:00:00Z',
          action: 'revoke',
          from_agent: 'zhongshu',
          to_agent: 'taizi',
          reason: '测试撤销',
        },
      ],
    });

    render(<PermissionMatrix />);

    // Wait for data to load
    await waitFor(() => {
      expect(mockApi.auditLog).toHaveBeenCalled();
    });

    // Click the audit log tab
    const auditTab = screen.getByRole('button', { name: /审计日志/ });
    fireEvent.click(auditTab);

    await waitFor(() => {
      expect(screen.getByText('测试授权')).not.toBeNull();
      expect(screen.getByText('测试撤销')).not.toBeNull();
    });
  });
});
