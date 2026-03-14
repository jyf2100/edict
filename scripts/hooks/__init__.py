"""
自动上报钩子包

提供三个核心钩子:
- report_tool_call: 工具调用上报
- report_thinking: 思考过程上报
- report_state: 状态变更上报

使用方式:
1. 作为独立脚本调用:
   python3 scripts/hooks/report_tool_call.py JJC-xxx "Read" "/path/file.py" "success"

2. 作为 Python 模块导入:
   from hooks import report_tool_call, report_thinking, report_state

3. 通过环境变量设置 TASK_ID 后调用:
   export TASK_ID=JJC-xxx
   python3 scripts/hooks/report_thinking.py "正在分析..."

4. 配置到 OpenClaw (需要 OpenClaw 支持):
   在 ~/.openclaw/config.yaml 中配置 post_tool_use hook
"""

# 使用绝对导入避免模块路径问题
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from report_tool_call import report_tool_call  # noqa: E402
from report_thinking import report_thinking  # noqa: E402
from report_state import report_state_change, report_blocked  # noqa: E402

__all__ = [
    'report_tool_call',
    'report_thinking',
    'report_state_change',
    'report_blocked',
]
