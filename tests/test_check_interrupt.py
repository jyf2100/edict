#!/usr/bin/env python3
"""单元测试 - 中断检查工具 (check_interrupt.py)"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# 添加脚本目录到 path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))


class TestCheckInterrupt(unittest.TestCase):
    """中断检查测试"""

    def setUp(self):
        """创建临时任务文件"""
        self.temp_dir = tempfile.mkdtemp()
        self.tasks_file = Path(self.temp_dir) / 'tasks_source.json'

        # 保存原始路径
        import check_interrupt
        self.original_tasks_file = check_interrupt.TASKS_FILE
        check_interrupt.TASKS_FILE = self.tasks_file

    def tearDown(self):
        """清理临时文件"""
        import shutil
        import check_interrupt
        check_interrupt.TASKS_FILE = self.original_tasks_file
        shutil.rmtree(self.temp_dir)

    def _write_tasks(self, tasks):
        """写入测试任务数据"""
        with open(self.tasks_file, 'w', encoding='utf-8') as f:
            json.dump(tasks, f)

    def test_continue_for_normal_task(self):
        """正常任务应返回 continue"""
        self._write_tasks([
            {'id': 'JJC-001', 'state': 'Doing', 'title': '测试任务'}
        ])

        from check_interrupt import check_interrupt
        result = check_interrupt('JJC-001')
        self.assertEqual(result, 'continue')

    def test_stop_for_blocked_task(self):
        """被叫停的任务应返回 stop"""
        self._write_tasks([
            {'id': 'JJC-002', 'state': 'Blocked', 'title': '被叫停的任务'}
        ])

        from check_interrupt import check_interrupt
        result = check_interrupt('JJC-002')
        self.assertEqual(result, 'stop')

    def test_cancel_for_cancelled_task(self):
        """被取消的任务应返回 cancel"""
        self._write_tasks([
            {'id': 'JJC-003', 'state': 'Cancelled', 'title': '被取消的任务'}
        ])

        from check_interrupt import check_interrupt
        result = check_interrupt('JJC-003')
        self.assertEqual(result, 'cancel')

    def test_continue_for_nonexistent_task(self):
        """不存在的任务应返回 continue（可能是新任务）"""
        self._write_tasks([
            {'id': 'JJC-001', 'state': 'Doing', 'title': '测试任务'}
        ])

        from check_interrupt import check_interrupt
        result = check_interrupt('JJC-999')
        self.assertEqual(result, 'continue')

    def test_continue_when_no_tasks_file(self):
        """任务文件不存在时应返回 continue"""
        # 确保任务文件不存在
        if self.tasks_file.exists():
            os.remove(self.tasks_file)

        from check_interrupt import check_interrupt
        result = check_interrupt('JJC-001')
        self.assertEqual(result, 'continue')

    def test_multiple_tasks(self):
        """多个任务时应正确匹配"""
        self._write_tasks([
            {'id': 'JJC-001', 'state': 'Done'},
            {'id': 'JJC-002', 'state': 'Blocked'},
            {'id': 'JJC-003', 'state': 'Doing'},
        ])

        from check_interrupt import check_interrupt

        self.assertEqual(check_interrupt('JJC-001'), 'continue')  # Done is not stop
        self.assertEqual(check_interrupt('JJC-002'), 'stop')      # Blocked
        self.assertEqual(check_interrupt('JJC-003'), 'continue')  # Doing

    def test_all_states(self):
        """测试所有可能的状态"""
        states = [
            ('Inbox', 'continue'),
            ('Taizi', 'continue'),
            ('Zhongshu', 'continue'),
            ('Menxia', 'continue'),
            ('Assigned', 'continue'),
            ('Doing', 'continue'),
            ('Review', 'continue'),
            ('Done', 'continue'),
            ('Blocked', 'stop'),
            ('Cancelled', 'cancel'),
            ('Next', 'continue'),
        ]

        from check_interrupt import check_interrupt

        for state, expected in states:
            self._write_tasks([{'id': 'JJC-TEST', 'state': state}])
            result = check_interrupt('JJC-TEST')
            self.assertEqual(result, expected, f"State {state} should return {expected}")


if __name__ == '__main__':
    unittest.main()
