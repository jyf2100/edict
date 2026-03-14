#!/usr/bin/env python3
"""集成测试 - 自动上报钩子

这些测试验证钩子脚本能正确运行并调用 kanban_update.py。
由于实际任务可能不存在，我们主要验证：
1. 脚本能正常执行（不抛异常）
2. 命令行参数解析正确
3. 帮助信息正确显示
"""

import os
import sys
import subprocess
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent / 'scripts' / 'hooks'


class TestReportToolCallScript(unittest.TestCase):
    """工具调用上报脚本测试"""

    def test_help_output(self):
        """测试帮助信息输出"""
        result = subprocess.run(
            ['python3', str(SCRIPTS_DIR / 'report_tool_call.py')],
            capture_output=True,
            text=True
        )
        self.assertIn('工具调用上报钩子', result.stdout)
        self.assertIn('用法:', result.stdout)

    def test_missing_task_id_error(self):
        """测试缺少 TASK_ID 时报错"""
        result = subprocess.run(
            ['python3', str(SCRIPTS_DIR / 'report_tool_call.py'), 'Read', 'file.py'],
            capture_output=True,
            text=True,
            env={**os.environ, 'TASK_ID': ''}
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn('TASK_ID', result.stderr)

    def test_with_task_id_arg(self):
        """测试通过参数传入 TASK_ID"""
        result = subprocess.run(
            ['python3', str(SCRIPTS_DIR / 'report_tool_call.py'),
             'JJC-TEST-001', 'Read', '/path/to/file.py', 'success'],
            capture_output=True,
            text=True
        )
        # 即使任务不存在，脚本也应该运行完成
        self.assertIn('[Hook]', result.stdout)


class TestReportThinkingScript(unittest.TestCase):
    """思考过程上报脚本测试"""

    def test_help_output(self):
        """测试帮助信息输出"""
        result = subprocess.run(
            ['python3', str(SCRIPTS_DIR / 'report_thinking.py')],
            capture_output=True,
            text=True
        )
        self.assertIn('思考过程上报钩子', result.stdout)

    def test_with_metrics_args(self):
        """测试带指标的调用"""
        result = subprocess.run(
            ['python3', str(SCRIPTS_DIR / 'report_thinking.py'),
             'JJC-TEST-002', '分析完成', '--tokens', '1500', '--cost', '0.05', '--elapsed', '30'],
            capture_output=True,
            text=True
        )
        self.assertIn('[Hook]', result.stdout)


class TestReportStateScript(unittest.TestCase):
    """状态变更上报脚本测试"""

    def test_help_output(self):
        """测试帮助信息输出"""
        result = subprocess.run(
            ['python3', str(SCRIPTS_DIR / 'report_state.py')],
            capture_output=True,
            text=True
        )
        self.assertIn('状态变更上报钩子', result.stdout)
        self.assertIn('Doing', result.stdout)
        self.assertIn('Blocked', result.stdout)

    def test_state_change(self):
        """测试状态变更调用"""
        result = subprocess.run(
            ['python3', str(SCRIPTS_DIR / 'report_state.py'),
             'JJC-TEST-003', 'Doing', '开始执行'],
            capture_output=True,
            text=True
        )
        self.assertIn('[Hook]', result.stdout)


class TestHookConfig(unittest.TestCase):
    """钩子配置测试"""

    def test_hooks_config_exists(self):
        """测试钩子配置文件存在"""
        config_path = Path(__file__).parent.parent / 'data' / 'hooks_config.json'
        self.assertTrue(config_path.exists())

    def test_hooks_init_exists(self):
        """测试钩子包 __init__.py 存在"""
        init_path = SCRIPTS_DIR / '__init__.py'
        self.assertTrue(init_path.exists())


class TestHookFunctions(unittest.TestCase):
    """钩子函数单元测试（直接调用）"""

    def test_report_tool_call_function(self):
        """测试 report_tool_call 函数能正常调用"""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "report_tool_call", SCRIPTS_DIR / 'report_tool_call.py'
        )
        module = importlib.util.module_from_spec(spec)

        # Mock kanban_update 模块
        sys.modules['kanban_update'] = type(sys)('kanban_update')
        sys.modules['kanban_update'].cmd_progress = lambda *a, **k: None
        sys.modules['kanban_update']._infer_agent_id_from_runtime = lambda *a: 'test'

        spec.loader.exec_module(module)

        # 应该不抛异常
        module.report_tool_call('JJC-001', 'Read', 'file.py', 'success')

    def test_report_thinking_function(self):
        """测试 report_thinking 函数能正常调用"""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "report_thinking", SCRIPTS_DIR / 'report_thinking.py'
        )
        module = importlib.util.module_from_spec(spec)

        sys.modules['kanban_update'] = type(sys)('kanban_update')
        sys.modules['kanban_update'].cmd_progress = lambda *a, **k: None

        spec.loader.exec_module(module)

        module.report_thinking('JJC-001', '思考中...', tokens=1000)

    def test_report_state_function(self):
        """测试 report_state_change 函数能正常调用"""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "report_state", SCRIPTS_DIR / 'report_state.py'
        )
        module = importlib.util.module_from_spec(spec)

        # Mock kanban_update 模块，包含所有需要的符号
        mock_kanban = type(sys)('kanban_update')
        mock_kanban.cmd_state = lambda *a, **k: None
        mock_kanban.cmd_flow = lambda *a, **k: None
        mock_kanban.cmd_block = lambda *a, **k: None
        mock_kanban._AGENT_LABELS = {}
        mock_kanban._infer_agent_id_from_runtime = lambda *a: 'test'
        sys.modules['kanban_update'] = mock_kanban

        spec.loader.exec_module(module)

        module.report_state_change('JJC-001', 'Doing', '开始')
        module.report_blocked('JJC-001', '等待依赖')


if __name__ == '__main__':
    unittest.main()
