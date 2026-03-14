/**
 * ConnectionStatus — WebSocket 连接状态指示器
 * REQ-0001-001: 显示连接状态，支持重连动画
 */

import { useStore, type ConnectionStatus } from '../store';
import { clsx } from 'clsx';

const STATUS_CONFIG: Record<ConnectionStatus, { icon: string; label: string; color: string }> = {
  connected: { icon: '🟢', label: '已连接', color: 'text-green-500' },
  connecting: { icon: '🟡', label: '连接中...', color: 'text-yellow-500 animate-pulse' },
  disconnected: { icon: '⚪', label: '未连接', color: 'text-gray-400' },
  reconnecting: { icon: '🟠', label: '重连中...', color: 'text-orange-500 animate-pulse' },
};

export function ConnectionStatusBar() {
  const wsStatus = useStore((s) => s.wsStatus);
  const config = STATUS_CONFIG[wsStatus];

  return (
    <div
      className={clsx(
        'inline-flex items-center gap-1.5 px-2 py-1 text-xs rounded-full',
        'bg-gray-800/50 border border-gray-700'
      )}
      title={`WebSocket 状态: ${config.label}`}
    >
      <span className="text-sm">{config.icon}</span>
      <span className={clsx('font-medium', config.color)}>{config.label}</span>
    </div>
  );
}

export function ConnectionStatusDot({ showLabel = false }: { showLabel?: boolean }) {
  const wsStatus = useStore((s) => s.wsStatus);
  const config = STATUS_CONFIG[wsStatus];

  return (
    <div
      className={clsx('inline-flex items-center gap-1', showLabel && 'text-xs')}
      title={`WebSocket 状态: ${config.label}`}
    >
      <span className={clsx('text-sm', config.color)}>{config.icon}</span>
      {showLabel && <span className={config.color}>{config.label}</span>}
    </div>
  );
}
