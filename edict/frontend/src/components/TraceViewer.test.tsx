/**
 * TraceViewer 组件测试
 * REQ-0001-003: 追踪可视化组件
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { TraceViewer } from './TraceViewer';

// Mock the API
vi.mock('../api', () => ({
  api: {
    listTraces: vi.fn(),
    getTraceTree: vi.fn(),
  },
}));

import { api } from '../api';

const mockApi = api as unknown as {
  listTraces: ReturnType<typeof vi.fn>;
  getTraceTree: ReturnType<typeof vi.fn>;
};

describe('TraceViewer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render loading state initially', () => {
    mockApi.listTraces.mockImplementation(() => new Promise(() => {}));
    render(<TraceViewer />);
    expect(screen.queryByText(/加载中/i)).not.toBeNull();
  });

  it('should render trace list after loading', async () => {
    mockApi.listTraces.mockResolvedValue({
      count: 2,
      traces: [
        {
          trace_id: 'trace-001',
          root_span_name: 'process_task',
          span_count: 5,
          duration_ms: 1500,
          status: 'OK',
          start_time: '2026-03-14T10:00:00Z',
        },
        {
          trace_id: 'trace-002',
          root_span_name: 'agent_call',
          span_count: 3,
          duration_ms: 800,
          status: 'ERROR',
          start_time: '2026-03-14T09:00:00Z',
        },
      ],
    });

    render(<TraceViewer />);

    await waitFor(() => {
      expect(screen.getByText('process_task')).not.toBeNull();
      expect(screen.getByText('agent_call')).not.toBeNull();
    });
  });

  it('should show trace tree when clicking a trace', async () => {
    mockApi.listTraces.mockResolvedValue({
      count: 1,
      traces: [
        {
          trace_id: 'trace-001',
          root_span_name: 'process_task',
          span_count: 2,
          duration_ms: 1500,
          status: 'OK',
          start_time: '2026-03-14T10:00:00Z',
        },
      ],
    });

    mockApi.getTraceTree.mockResolvedValue({
      trace_id: 'trace-001',
      spans: [
        {
          span: {
            span_id: 'span-001',
            trace_id: 'trace-001',
            parent_span_id: null,
            name: 'process_task',
            kind: 'INTERNAL',
            start_time: '2026-03-14T10:00:00Z',
            end_time: '2026-03-14T10:00:01Z',
            duration_ms: 1500,
            status: 'OK',
            attributes: {},
            events: [],
          },
          children: [
            {
              span: {
                span_id: 'span-002',
                trace_id: 'trace-001',
                parent_span_id: 'span-001',
                name: 'sub_task',
                kind: 'INTERNAL',
                start_time: '2026-03-14T10:00:00Z',
                end_time: '2026-03-14T10:00:00.5Z',
                duration_ms: 500,
                status: 'OK',
                attributes: {},
                events: [],
              },
              children: [],
            },
          ],
        },
      ],
    });

    render(<TraceViewer />);

    await waitFor(() => {
      expect(screen.getByText('process_task')).not.toBeNull();
    });

    // Click on the trace to show tree
    fireEvent.click(screen.getByText('process_task'));

    await waitFor(() => {
      expect(mockApi.getTraceTree).toHaveBeenCalledWith('trace-001');
      expect(screen.getByText('sub_task')).not.toBeNull();
    });
  });

  it('should show error status in red', async () => {
    mockApi.listTraces.mockResolvedValue({
      count: 1,
      traces: [
        {
          trace_id: 'trace-002',
          root_span_name: 'failed_task',
          span_count: 1,
          duration_ms: 100,
          status: 'ERROR',
          start_time: '2026-03-14T09:00:00Z',
        },
      ],
    });

    render(<TraceViewer />);

    await waitFor(() => {
      const errorElement = screen.getByText('ERROR');
      expect(errorElement).not.toBeNull();
      // Check parent has error styling class
      expect(errorElement.className).toContain('text-red');
    });
  });

  it('should display duration in milliseconds', async () => {
    mockApi.listTraces.mockResolvedValue({
      count: 1,
      traces: [
        {
          trace_id: 'trace-001',
          root_span_name: 'process_task',
          span_count: 5,
          duration_ms: 500,  // Less than 1000ms to show in ms
          status: 'OK',
          start_time: '2026-03-14T10:00:00Z',
        },
      ],
    });

    render(<TraceViewer />);

    await waitFor(() => {
      expect(screen.getByText(/500/)).not.toBeNull();
      expect(screen.getByText(/ms/)).not.toBeNull();
    });
  });
});
