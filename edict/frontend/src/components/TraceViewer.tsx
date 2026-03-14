/**
 * TraceViewer — 追踪可视化组件
 * REQ-0001-003: 显示追踪列表和树形结构
 */

import { useState, useEffect, useCallback } from 'react';
import { api, type TraceSummary, type TraceTreeNode } from '../api';
import { clsx } from 'clsx';

export function TraceViewer() {
  const [traces, setTraces] = useState<TraceSummary[]>([]);
  const [selectedTrace, setSelectedTrace] = useState<string | null>(null);
  const [traceTree, setTraceTree] = useState<TraceTreeNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadTraces = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.listTraces(100);
      setTraces(data.traces || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTraces();
  }, [loadTraces]);

  const handleTraceClick = async (traceId: string) => {
    if (selectedTrace === traceId) {
      setSelectedTrace(null);
      setTraceTree([]);
      return;
    }

    try {
      setSelectedTrace(traceId);
      const tree = await api.getTraceTree(traceId);
      setTraceTree(tree.spans || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载追踪树失败');
    }
  };

  const formatDuration = (ms: number | null) => {
    if (ms === null) return '—';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const renderTreeNode = (node: TraceTreeNode, depth = 0) => {
    const { span, children } = node;
    const isError = span.status === 'ERROR';

    return (
      <div key={span.span_id} className="ml-4">
        <div
          className={clsx(
            'py-1 px-2 rounded border mb-1',
            isError
              ? 'bg-red-900/20 border-red-800'
              : 'bg-gray-800 border-gray-700'
          )}
          style={{ marginLeft: `${depth * 16}px` }}
        >
          <div className="flex items-center gap-2 text-sm">
            <span className={clsx('font-medium', isError ? 'text-red-400' : 'text-blue-400')}>
              {span.name}
            </span>
            <span className="text-gray-400 text-xs">
              {formatDuration(span.duration_ms)}
            </span>
            <span
              className={clsx(
                'px-1.5 py-0.5 rounded text-xs',
                isError
                  ? 'bg-red-700 text-red-100'
                  : 'bg-green-700 text-green-100'
              )}
            >
              {span.status}
            </span>
          </div>
          {span.attributes && Object.keys(span.attributes).length > 0 && (
            <div className="text-xs text-gray-500 mt-1">
              {Object.entries(span.attributes).slice(0, 3).map(([k, v]) => (
                <span key={k} className="mr-2">{k}: {String(v).slice(0, 20)}</span>
              ))}
            </div>
          )}
        </div>
        {children.map((child) => renderTreeNode(child, depth + 1))}
      </div>
    );
  };

  if (loading && traces.length === 0) {
    return (
      <div className="p-4 text-center text-gray-400">
        加载中...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-center text-red-400">
        错误: {error}
        <button onClick={loadTraces} className="ml-2 text-blue-400 underline">
          重试
        </button>
      </div>
    );
  }

  return (
    <div className="p-4">
      <h2 className="text-lg font-bold mb-4 text-gray-200">追踪列表 ({traces.length})</h2>

      {/* Trace List */}
      <div className="space-y-2 mb-6">
        {traces.length === 0 ? (
          <p className="text-gray-400 text-center py-4">暂无追踪数据</p>
        ) : (
          traces.map((trace) => {
            const isError = trace.status === 'ERROR';
            const isSelected = selectedTrace === trace.trace_id;

            return (
              <div key={trace.trace_id}>
                <div
                  className={clsx(
                    'p-3 rounded-lg border cursor-pointer transition-colors',
                    isSelected
                      ? 'bg-blue-900/30 border-blue-600'
                      : 'bg-gray-800 border-gray-700 hover:border-gray-600',
                    isError && 'border-l-4 border-l-red-500'
                  )}
                  onClick={() => handleTraceClick(trace.trace_id)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="font-medium text-gray-200">{trace.root_span_name}</span>
                      <span
                        className={clsx(
                          'px-2 py-0.5 rounded text-xs',
                          isError
                            ? 'bg-red-700 text-red-100'
                            : 'bg-green-700 text-green-100'
                        )}
                      >
                        {trace.status}
                      </span>
                      <span className="text-gray-400 text-sm">
                        {trace.span_count} spans
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-sm text-gray-400">
                      <span>{formatDuration(trace.duration_ms)}</span>
                      <span>{new Date(trace.start_time).toLocaleTimeString('zh-CN')}</span>
                    </div>
                  </div>
                </div>

                {/* Trace Tree (shown when selected) */}
                {isSelected && traceTree.length > 0 && (
                  <div className="mt-2 p-3 bg-gray-900 rounded-lg border border-gray-700">
                    <h3 className="text-sm font-medium text-gray-400 mb-2">调用树</h3>
                    {traceTree.map((node) => renderTreeNode(node))}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
