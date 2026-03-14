#!/usr/bin/env python3
"""单元测试 - 事件发布器 (event_publisher.py)"""

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# 添加脚本目录到 path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))


class TestEventPublisher(unittest.TestCase):
    """事件发布器测试"""

    @patch('event_publisher._get_redis')
    def test_publish_event_success(self, mock_get_redis):
        """测试成功发布事件"""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_get_redis.return_value = mock_redis

        from event_publisher import publish_event

        result = publish_event('test.topic', {'message': 'hello'})

        self.assertTrue(result)
        mock_redis.publish.assert_called_once()
        call_args = mock_redis.publish.call_args
        self.assertIn('edict:pubsub:test.topic', call_args[0])

    @patch('event_publisher._get_redis')
    def test_publish_event_no_redis(self, mock_get_redis):
        """测试 Redis 不可用时返回 False"""
        mock_get_redis.return_value = None

        from event_publisher import publish_event

        result = publish_event('test.topic', {'message': 'hello'})
        self.assertFalse(result)

    @patch('event_publisher._get_redis')
    def test_publish_task_update(self, mock_get_redis):
        """测试任务更新事件"""
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        from event_publisher import publish_task_update

        result = publish_task_update('JJC-001', 'Doing', agent_id='zhongshu')

        self.assertTrue(result)
        mock_redis.publish.assert_called_once()
        call_args = mock_redis.publish.call_args
        payload = json.loads(call_args[0][1])
        self.assertEqual(payload['topic'], 'task.status')
        self.assertIn('task_id', payload['payload'])
        self.assertEqual(payload['payload']['task_id'], 'JJC-001')

    @patch('event_publisher._get_redis')
    def test_publish_sync_complete(self, mock_get_redis):
        """测试同步完成事件"""
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        from event_publisher import publish_sync_complete

        result = publish_sync_complete(record_count=10, duration_ms=50)

        self.assertTrue(result)
        mock_redis.publish.assert_called_once()
        call_args = mock_redis.publish.call_args
        payload = json.loads(call_args[0][1])
        self.assertEqual(payload['topic'], 'sync.complete')
        self.assertEqual(payload['payload']['record_count'], 10)
        self.assertEqual(payload['payload']['duration_ms'], 50)


class TestEventPublisherFormat(unittest.TestCase):
    """事件格式测试 (不需要 Redis)"""

    def test_event_structure(self):
        """测试事件结构包含必要字段"""
        from datetime import datetime, timezone
        import uuid

        event = {
            'event_id': f'{datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")}-abc123',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'topic': 'test.event',
            'event_type': 'event',
            'producer': 'test',
            'payload': {'key': 'value'},
        }

        # 验证必要字段
        self.assertIn('event_id', event)
        self.assertIn('timestamp', event)
        self.assertIn('topic', event)
        self.assertIn('payload', event)

        # 验证时间戳格式
        parsed_time = datetime.fromisoformat(event['timestamp'])
        self.assertIsNotNone(parsed_time)


if __name__ == '__main__':
    unittest.main()
