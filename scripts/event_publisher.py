#!/usr/bin/env python3
"""同步事件发布器 — 供同步脚本使用，发布事件到 Redis Pub/Sub。

使用方法：
    from event_publisher import publish_event

    # 发布任务状态变更
    publish_event('task.status', {
        'task_id': 'JJC-20260314-001',
        'state': 'Doing',
        'agent_id': 'zhongshu'
    })
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger('event_publisher')

# Redis 连接配置
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# 尝试导入 redis（同步版本）
_redis_client = None

def _get_redis():
    """获取 Redis 客户端（延迟初始化）。"""
    global _redis_client
    if _redis_client is None:
        try:
            import redis
            _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            # 测试连接
            _redis_client.ping()
            log.info(f'Event publisher connected to Redis: {REDIS_URL}')
        except ImportError:
            log.warning('redis package not installed, events will not be published')
        except Exception as e:
            log.warning(f'Failed to connect to Redis: {e}')
            _redis_client = None
    return _redis_client


def publish_event(topic: str, payload: dict[str, Any], producer: str = 'sync_script') -> bool:
    """发布事件到 Redis Pub/Sub。

    Args:
        topic: 事件主题 (如 'task.status', 'agent.heartbeat')
        payload: 事件数据
        producer: 生产者标识

    Returns:
        bool: 是否成功发布
    """
    redis_client = _get_redis()
    if redis_client is None:
        return False

    event = {
        'event_id': f'{datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")}-{os.urandom(4).hex()}',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'topic': topic,
        'event_type': topic.split('.')[-1] if '.' in topic else topic,
        'producer': producer,
        'payload': payload,
    }

    try:
        channel = f'edict:pubsub:{topic}'
        redis_client.publish(channel, json.dumps(event, ensure_ascii=False))
        log.debug(f'📤 Published {topic} to {channel}')
        return True
    except Exception as e:
        log.warning(f'Failed to publish event: {e}')
        return False


def publish_task_update(task_id: str, state: str = None, agent_id: str = None, **kwargs) -> bool:
    """发布任务更新事件的便捷方法。"""
    payload = {'task_id': task_id}
    if state:
        payload['state'] = state
    if agent_id:
        payload['agent_id'] = agent_id
    payload.update(kwargs)
    return publish_event('task.status', payload)


def publish_agent_heartbeat(agent_id: str, status: str = 'active', **kwargs) -> bool:
    """发布 Agent 心跳事件。"""
    payload = {'agent_id': agent_id, 'status': status}
    payload.update(kwargs)
    return publish_event('agent.heartbeat', payload)


def publish_sync_complete(record_count: int, duration_ms: int, **kwargs) -> bool:
    """发布同步完成事件。"""
    payload = {'record_count': record_count, 'duration_ms': duration_ms}
    payload.update(kwargs)
    return publish_event('sync.complete', payload)


if __name__ == '__main__':
    # 测试事件发布
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(name)s] %(message)s')
    print('Testing event publisher...')
    success = publish_event('test.event', {'message': 'Hello from event_publisher!'})
    print(f'Published: {success}')
