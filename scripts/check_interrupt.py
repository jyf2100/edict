#!/usr/bin/env python3
"""中断检查工具 — 供 Agent 调用，检查是否应该停止当前任务。

使用方式：
    # 在 Agent SOUL.md 中添加定期检查
    python3 scripts/check_interrupt.py <task_id>

返回值：
    0 = 继续执行
    1 = 应该停止（任务已被叫停或取消）

输出：
    continue  - 继续执行
    stop      - 应该停止
    cancel    - 应该取消
    error     - 检查出错
"""

import json
import sys
import pathlib

# 路径配置
SCRIPTS_DIR = pathlib.Path(__file__).parent
DATA_DIR = SCRIPTS_DIR.parent / 'data'
TASKS_FILE = DATA_DIR / 'tasks_source.json'

# 停止状态
STOP_STATES = {'Blocked', 'Cancelled'}


def check_interrupt(task_id: str) -> str:
    """检查任务是否应该中断。

    Args:
        task_id: 任务ID（如 JJC-20260314-001 或 OC-zhongshu-abc12345）

    Returns:
        'continue' - 继续执行
        'stop'     - 应该停止（Blocked）
        'cancel'   - 应该取消（Cancelled）
        'error'    - 检查出错
    """
    try:
        if not TASKS_FILE.exists():
            return 'continue'

        with open(TASKS_FILE, 'r', encoding='utf-8') as f:
            tasks = json.load(f)

        # 查找任务
        for task in tasks:
            if task.get('id') == task_id:
                state = task.get('state', '')

                if state == 'Blocked':
                    return 'stop'
                elif state == 'Cancelled':
                    return 'cancel'
                else:
                    return 'continue'

        # 任务不存在，继续执行（可能是新任务）
        return 'continue'

    except Exception as e:
        print(f'Error checking interrupt: {e}', file=sys.stderr)
        return 'error'


def main():
    if len(sys.argv) < 2:
        print('Usage: python3 scripts/check_interrupt.py <task_id>', file=sys.stderr)
        sys.exit(2)

    task_id = sys.argv[1]
    result = check_interrupt(task_id)
    print(result)

    if result == 'continue':
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
