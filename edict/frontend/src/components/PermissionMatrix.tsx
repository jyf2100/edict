/**
 * PermissionMatrix — 权限矩阵管理组件
 * REQ-0001-002: 显示权限矩阵，支持授权/撤销操作
 */

import { useState, useEffect, useCallback } from 'react';
import { api, type VisualMatrixData, type AuditLogEntry } from '../api';
import { clsx } from 'clsx';

export function PermissionMatrix() {
  const [matrixData, setMatrixData] = useState<VisualMatrixData | null>(null);
  const [auditLog, setAuditLog] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'matrix' | 'audit'>('matrix');

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [matrix, audit] = await Promise.all([
        api.visualMatrix(),
        api.auditLog(100),
      ]);
      setMatrixData(matrix);
      setAuditLog(audit.entries || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCellClick = async (fromAgent: string, toAgent: string, currentValue: string) => {
    try {
      if (currentValue === '❌') {
        // Grant permission
        await api.grantPermission(fromAgent, toAgent);
      } else if (currentValue === '✅') {
        // Revoke permission
        await api.revokePermission(fromAgent, toAgent);
      }
      // Reload data after change
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : '操作失败');
    }
  };

  if (loading && !matrixData) {
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
        <button onClick={loadData} className="ml-2 text-blue-400 underline">
          重试
        </button>
      </div>
    );
  }

  return (
    <div className="p-4">
      {/* Tab Switcher */}
      <div className="flex gap-2 mb-4">
        <button
          className={clsx(
            'px-4 py-2 rounded-lg',
            activeTab === 'matrix' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300'
          )}
          onClick={() => setActiveTab('matrix')}
        >
          权限矩阵
        </button>
        <button
          className={clsx(
            'px-4 py-2 rounded-lg',
            activeTab === 'audit' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300'
          )}
          onClick={() => setActiveTab('audit')}
        >
          审计日志 ({auditLog.length})
        </button>
      </div>

      {/* Permission Matrix */}
      {activeTab === 'matrix' && matrixData && (
        <div className="overflow-x-auto">
          <table className="min-w-full border-collapse">
            <thead>
              <tr>
                <th className="p-2 text-left text-gray-400 border border-gray-700">
                  授权方 ↓ / 被调用 →
                </th>
                {matrixData.agents.map((agent) => (
                  <th
                    key={agent.id}
                    className="p-2 text-center text-gray-300 border border-gray-700 min-w-[80px]"
                  >
                    {agent.name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {matrixData.matrix.map((row) => (
                <tr key={row.from}>
                  <td className="p-2 text-gray-300 border border-gray-700 font-medium">
                    {row.from_name}
                  </td>
                  {matrixData.agents.map((agent) => {
                    const cellValue = row[agent.id];
                    const isSelf = row.from === agent.id;
                    return (
                      <td
                        key={agent.id}
                        className={clsx(
                          'p-2 text-center border border-gray-700 cursor-pointer transition-colors',
                          isSelf
                            ? 'bg-gray-800 text-gray-500 cursor-not-allowed'
                            : 'hover:bg-gray-600'
                        )}
                        onClick={() => {
                          if (!isSelf && cellValue) {
                            handleCellClick(row.from, agent.id, cellValue);
                          }
                        }}
                        title={
                          isSelf
                            ? '不能授权给自己'
                            : cellValue === '✅'
                            ? '点击撤销权限'
                            : '点击授予权限'
                        }
                      >
                        {cellValue}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Audit Log */}
      {activeTab === 'audit' && (
        <div className="space-y-2">
          {auditLog.length === 0 ? (
            <p className="text-gray-400 text-center py-4">暂无审计日志</p>
          ) : (
            auditLog.map((entry, index) => (
              <div
                key={index}
                className={clsx(
                  'p-3 rounded-lg border',
                  entry.action === 'grant'
                    ? 'bg-green-900/20 border-green-800'
                    : 'bg-red-900/20 border-red-800'
                )}
              >
                <div className="flex items-center gap-2 text-sm">
                  <span
                    className={clsx(
                      'px-2 py-0.5 rounded text-xs font-medium',
                      entry.action === 'grant'
                        ? 'bg-green-700 text-white'
                        : 'bg-red-700 text-white'
                    )}
                  >
                    {entry.action === 'grant' ? '授权' : '撤销'}
                  </span>
                  <span className="text-gray-300">
                    {entry.from_agent} → {entry.to_agent}
                  </span>
                  <span className="text-gray-500 text-xs ml-auto">
                    {new Date(entry.timestamp).toLocaleString('zh-CN')}
                  </span>
                </div>
                {entry.reason && (
                  <p className="text-gray-400 text-sm mt-1">{entry.reason}</p>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
