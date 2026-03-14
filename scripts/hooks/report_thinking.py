#!/usr/bin/env python3
"""
思考过程上报钩子 - Agent 思考/分析时上报进展

用法:
  # 手动调用
  python3 scripts/hooks/report_thinking.py JJC-xxx "正在分析需求，拟定3个方案..."
  python3 scripts/hooks/report_thinking.py JJC-xxx "代码审查中，发现2个问题" --tokens 1500

环境变量:
  TASK_ID: 当前任务 ID (可选)
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from kanban_update import cmd_progress

def report_thinking(task_id: str, thinking: str, tokens: int = 0, cost: float = 0.0, elapsed: int = 0):
    """
    上报思考过程到看板进展日志

    Args:
        task_id: 任务 ID
        thinking: 思考内容描述
        tokens: 消耗的 token 数 (可选)
        cost: 成本 (可选)
        elapsed: 耗时秒数 (可选)
    """
    # 构建进度消息
    now_text = f"💭 {thinking}"

    # 调用 kanban_update progress 命令
    try:
        cmd_progress(task_id, now_text, tokens=tokens, cost=cost, elapsed=elapsed)
    except Exception as e:
        print(f'[Hook] 上报失败: {e}', file=sys.stderr)


def main():
    """命令行入口"""
    args = sys.argv[1:]

    # 从环境变量获取 task_id
    task_id = os.environ.get('TASK_ID', '')

    # 解析参数
    pos_args = []
    kw_args = {'tokens': 0, 'cost': 0.0, 'elapsed': 0}

    i = 0
    while i < len(args):
        if args[i] == '--tokens' and i + 1 < len(args):
            kw_args['tokens'] = int(args[i + 1])
            i += 2
        elif args[i] == '--cost' and i + 1 < len(args):
            kw_args['cost'] = float(args[i + 1])
            i += 2
        elif args[i] == '--elapsed' and i + 1 < len(args):
            kw_args['elapsed'] = int(args[i + 1])
            i += 2
        else:
            pos_args.append(args[i])
            i += 1

    if len(pos_args) >= 2:
        task_id = pos_args[0]
        thinking = pos_args[1]
    elif len(pos_args) >= 1:
        thinking = pos_args[0]
    else:
        print(__doc__)
        print(f'当前 TASK_ID={task_id or "未设置"}')
        sys.exit(1)

    if not task_id:
        print('错误: 需要设置 TASK_ID 环境变量或作为第一个参数', file=sys.stderr)
        sys.exit(1)

    report_thinking(task_id, thinking, **kw_args)
    res_info = ''
    if kw_args['tokens'] or kw_args['cost'] or kw_args['elapsed']:
        res_info = f" [res: {kw_args['tokens']}tok/${kw_args['cost']:.4f}/{kw_args['elapsed']}s]"
    print(f'[Hook] 思考过程已上报{res_info}')


if __name__ == '__main__':
    main()
