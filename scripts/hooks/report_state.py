#!/usr/bin/env python3
"""
状态变更上报钩子 - Agent 状态变化时自动上报

用法:
  # 手动调用
  python3 scripts/hooks/report_state.py JJC-xxx Doing "开始实现功能"
  python3 scripts/hooks/report_state.py JJC-xxx Review "代码已提交审核"
  python3 scripts/hooks/report_state.py JJC-xxx Blocked "等待外部依赖" --reason "API 文档未提供"

环境变量:
  TASK_ID: 当前任务 ID (可选)

状态映射:
  - Inbox     → 收件箱
  - Taizi     → 太子审批
  - Zhongshu  → 中书省审议
  - Menxia    → 门下省封驳
  - Assigned  → 尚书省派发
  - Doing     → 执行中
  - Review    → 审核中
  - Done      → 已完成
  - Blocked   → 阻塞
  - Cancelled → 已取消
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from kanban_update import cmd_state, cmd_flow, cmd_block, _AGENT_LABELS, _infer_agent_id_from_runtime

# 状态到组织的映射
STATE_ORG_MAP = {
    'Taizi': '太子', 'Zhongshu': '中书省', 'Menxia': '门下省', 'Assigned': '尚书省',
    'Doing': '执行中', 'Review': '尚书省', 'Done': '完成', 'Blocked': '阻塞',
    'Cancelled': '已取消', 'Inbox': '收件箱'
}

def report_state_change(task_id: str, new_state: str, remark: str = '', from_dept: str = ''):
    """
    上报状态变更到看板

    Args:
        task_id: 任务 ID
        new_state: 新状态 (Doing, Review, Done, Blocked, etc.)
        remark: 变更备注
        from_dept: 来源部门 (可选，用于流转记录)
    """
    try:
        # 更新状态
        cmd_state(task_id, new_state, remark)

        # 如果有来源部门，添加流转记录
        if from_dept:
            to_dept = STATE_ORG_MAP.get(new_state, new_state)
            cmd_flow(task_id, from_dept, to_dept, remark or f"状态变更为 {new_state}")

    except Exception as e:
        print(f'[Hook] 状态变更上报失败: {e}', file=sys.stderr)


def report_blocked(task_id: str, reason: str):
    """上报任务阻塞"""
    try:
        cmd_block(task_id, reason)
    except Exception as e:
        print(f'[Hook] 阻塞上报失败: {e}', file=sys.stderr)


def main():
    """命令行入口"""
    args = sys.argv[1:]

    # 从环境变量获取 task_id
    task_id = os.environ.get('TASK_ID', '')

    # 解析参数
    pos_args = []
    kw_args = {'reason': '', 'from_dept': ''}

    i = 0
    while i < len(args):
        if args[i] == '--reason' and i + 1 < len(args):
            kw_args['reason'] = args[i + 1]
            i += 2
        elif args[i] == '--from' and i + 1 < len(args):
            kw_args['from_dept'] = args[i + 1]
            i += 2
        else:
            pos_args.append(args[i])
            i += 1

    if len(pos_args) >= 3:
        task_id = pos_args[0]
        new_state = pos_args[1]
        remark = pos_args[2]
    elif len(pos_args) >= 2:
        task_id = pos_args[0]
        new_state = pos_args[1]
        remark = ''
    else:
        print(__doc__)
        print(f'当前 TASK_ID={task_id or "未设置"}')
        sys.exit(1)

    if not task_id:
        print('错误: 需要设置 TASK_ID 环境变量或作为第一个参数', file=sys.stderr)
        sys.exit(1)

    # 处理阻塞状态
    if new_state == 'Blocked' and kw_args['reason']:
        report_blocked(task_id, kw_args['reason'])
        print(f'[Hook] 阻塞已上报: {kw_args["reason"]}')
    else:
        report_state_change(task_id, new_state, remark or kw_args['reason'], kw_args['from_dept'])
        print(f'[Hook] 状态变更已上报: → {new_state}')


if __name__ == '__main__':
    main()
