#!/usr/bin/env python3
"""
工具调用上报钩子 - Agent 调用工具时自动上报进展

用法:
  # 在 Agent SOUL.md 中配置为 Hook，或手动调用
  python3 scripts/hooks/report_tool_call.py JJC-xxx "Read" "/path/to/file.py" "success"
  python3 scripts/hooks/report_tool_call.py JJC-xxx "Bash" "npm test" "error"

环境变量:
  TASK_ID: 当前任务 ID (可选，如果未传参)
  AGENT_ID: 当前 Agent ID (可选)

作为 OpenClaw Hook 调用:
  在 ~/.openclaw/config.yaml 中配置:
  hooks:
    post_tool_use:
      - python3 /path/to/report_tool_call.py
"""
import json
import os
import sys
import datetime
from pathlib import Path

# 添加父目录到 path 以导入 kanban_update
sys.path.insert(0, str(Path(__file__).parent.parent))
from kanban_update import cmd_progress, _infer_agent_id_from_runtime

def report_tool_call(task_id: str, tool_name: str, tool_input: str, status: str = 'success'):
    """
    上报工具调用到看板进展日志

    Args:
        task_id: 任务 ID
        tool_name: 工具名称 (Read, Write, Bash, etc.)
        tool_input: 工具输入 (文件路径、命令等)
        status: 调用状态 (success, error, timeout)
    """
    # 截断过长的输入
    if len(tool_input) > 60:
        tool_input = tool_input[:57] + '...'

    # 构建进度消息
    status_emoji = {'success': '✅', 'error': '❌', 'timeout': '⏱️'}.get(status, '▶️')
    now_text = f"{status_emoji} [{tool_name}] {tool_input}"

    # 获取 Agent ID
    agent_id = os.environ.get('AGENT_ID') or os.environ.get('OPENCLAW_AGENT_ID')

    # 调用 kanban_update progress 命令
    try:
        cmd_progress(task_id, now_text)
    except Exception as e:
        print(f'[Hook] 上报失败: {e}', file=sys.stderr)


def main():
    """命令行入口"""
    args = sys.argv[1:]

    # 从环境变量获取 task_id
    task_id = os.environ.get('TASK_ID', '')

    # 解析参数
    if len(args) >= 4:
        task_id = args[0]
        tool_name = args[1]
        tool_input = args[2]
        status = args[3]
    elif len(args) >= 3:
        tool_name = args[0]
        tool_input = args[1]
        status = args[2]
    elif len(args) >= 2:
        tool_name = args[0]
        tool_input = args[1]
        status = 'success'
    else:
        print(__doc__)
        print(f'当前 TASK_ID={task_id or "未设置"}')
        sys.exit(1)

    if not task_id:
        print('错误: 需要设置 TASK_ID 环境变量或作为第一个参数', file=sys.stderr)
        sys.exit(1)

    report_tool_call(task_id, tool_name, tool_input, status)
    print(f'[Hook] 工具调用已上报: {tool_name} -> {status}')


if __name__ == '__main__':
    main()
