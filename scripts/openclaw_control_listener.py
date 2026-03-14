#!/usr/bin/env python3
"""OpenClaw 控制监听器 — 监听 Redis 控制指令并执行。

功能：
- 监听 Redis Pub/Sub 频道 `edict:control:*`
- 处理 stop/pause/resume 指令
- 更新 tasks_source.json 中的任务状态
- 发布执行结果事件

运行方式：
    python3 scripts/openclaw_control_listener.py

环境变量：
    REDIS_URL: Redis 连接 URL (默认: redis://localhost:6379/0)
"""

import json
import logging
import os
import signal
import sys
import threading
import time
import pathlib
from datetime import datetime, timezone
from typing import Optional

# 添加脚本目录到 path
SCRIPTS_DIR = pathlib.Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from file_lock import atomic_json_read, atomic_json_write

log = logging.getLogger('control_listener')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)

# 配置
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
DATA_DIR = SCRIPTS_DIR.parent / 'data'
CONTROL_CHANNEL = 'edict:control:*'
RESULT_CHANNEL = 'edict:control:result'

# 运行标志
_running = True


def handle_shutdown(signum, frame):
    """处理终止信号"""
    global _running
    log.info('收到终止信号，正在关闭...')
    _running = False


def now_iso():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def load_tasks():
    return atomic_json_read(DATA_DIR / 'tasks_source.json', [])


def save_tasks(tasks):
    atomic_json_write(DATA_DIR / 'tasks_source.json', tasks)


def find_task_by_session(tasks, agent_id: str, session_key: str) -> Optional[dict]:
    """通过 agent_id 和 session_key 查找任务"""
    for task in tasks:
        meta = task.get('sourceMeta', {})
        if meta.get('agentId') == agent_id and meta.get('sessionKey') == session_key:
            return task
    return None


def find_task_by_id(tasks, task_id: str) -> Optional[dict]:
    """通过 task_id 查找任务"""
    for task in tasks:
        if task.get('id') == task_id:
            return task
    return None


def execute_stop(task_id: str, reason: str = '') -> dict:
    """执行停止指令"""
    tasks = load_tasks()
    task = find_task_by_id(tasks, task_id)

    if not task:
        # 尝试解析 OC-{agent_id}-{session_id} 格式
        if task_id.startswith('OC-'):
            parts = task_id.split('-', 2)
            if len(parts) >= 3:
                agent_id = parts[1]
                session_id = parts[2]
                task = find_task_by_session(tasks, agent_id, f'agent:{agent_id}:{session_id}')

    if not task:
        return {'ok': False, 'error': f'任务 {task_id} 不存在'}

    old_state = task.get('state', '')
    task['state'] = 'Blocked'
    task['block'] = reason or '远程控制停止'
    task['now'] = f'⏸️ 已远程停止：{reason}'
    task['_prev_state'] = old_state
    task['updatedAt'] = now_iso()

    # 添加流程日志
    task.setdefault('flow_log', []).append({
        'at': now_iso(),
        'from': '控制台',
        'to': task.get('org', ''),
        'remark': f'⏸️ 远程停止：{reason or "无原因"}'
    })

    save_tasks(tasks)

    # 触发刷新
    trigger_refresh()

    return {
        'ok': True,
        'task_id': task_id,
        'new_state': 'Blocked',
        'message': f'任务 {task_id} 已停止'
    }


def execute_cancel(task_id: str, reason: str = '') -> dict:
    """执行取消指令"""
    tasks = load_tasks()
    task = find_task_by_id(tasks, task_id)

    if not task:
        return {'ok': False, 'error': f'任务 {task_id} 不存在'}

    old_state = task.get('state', '')
    task['state'] = 'Cancelled'
    task['block'] = reason or '远程控制取消'
    task['now'] = f'🚫 已远程取消：{reason}'
    task['_prev_state'] = old_state
    task['updatedAt'] = now_iso()

    task.setdefault('flow_log', []).append({
        'at': now_iso(),
        'from': '控制台',
        'to': task.get('org', ''),
        'remark': f'🚫 远程取消：{reason or "无原因"}'
    })

    save_tasks(tasks)
    trigger_refresh()

    return {
        'ok': True,
        'task_id': task_id,
        'new_state': 'Cancelled',
        'message': f'任务 {task_id} 已取消'
    }


def execute_resume(task_id: str, reason: str = '') -> dict:
    """执行恢复指令"""
    tasks = load_tasks()
    task = find_task_by_id(tasks, task_id)

    if not task:
        return {'ok': False, 'error': f'任务 {task_id} 不存在'}

    old_state = task.get('state', '')
    new_state = task.get('_prev_state', 'Doing')
    task['state'] = new_state
    task['block'] = '无'
    task['now'] = f'▶️ 已远程恢复'
    task['updatedAt'] = now_iso()

    task.setdefault('flow_log', []).append({
        'at': now_iso(),
        'from': '控制台',
        'to': task.get('org', ''),
        'remark': f'▶️ 远程恢复：{reason or "无原因"} (从 {old_state} → {new_state})'
    })

    save_tasks(tasks)
    trigger_refresh()

    return {
        'ok': True,
        'task_id': task_id,
        'new_state': new_state,
        'message': f'任务 {task_id} 已恢复到 {new_state}'
    }


def trigger_refresh():
    """触发数据刷新"""
    import subprocess
    try:
        subprocess.run(
            ['python3', str(SCRIPTS_DIR / 'refresh_live_data.py')],
            timeout=30,
            capture_output=True
        )
    except Exception as e:
        log.warning(f'刷新数据失败: {e}')


def handle_control_command(command: dict) -> dict:
    """处理控制指令"""
    action = command.get('action', '')
    task_id = command.get('task_id', '')
    reason = command.get('reason', '')
    request_id = command.get('request_id', '')

    log.info(f'收到控制指令: action={action}, task_id={task_id}, reason={reason}')

    if not task_id:
        return {'ok': False, 'error': '缺少 task_id'}

    if action == 'stop':
        result = execute_stop(task_id, reason)
    elif action == 'cancel':
        result = execute_cancel(task_id, reason)
    elif action == 'resume':
        result = execute_resume(task_id, reason)
    else:
        result = {'ok': False, 'error': f'未知操作: {action}'}

    result['request_id'] = request_id
    result['timestamp'] = now_iso()

    return result


def publish_result(redis_client, result: dict):
    """发布执行结果"""
    try:
        redis_client.publish(RESULT_CHANNEL, json.dumps(result, ensure_ascii=False))
        log.debug(f'发布结果: {result}')
    except Exception as e:
        log.warning(f'发布结果失败: {e}')


def get_redis_client():
    """获取 Redis 客户端"""
    try:
        import redis
        client = redis.from_url(REDIS_URL, decode_responses=True)
        client.ping()
        log.info(f'已连接到 Redis: {REDIS_URL}')
        return client
    except ImportError:
        log.error('redis 包未安装，请运行: pip install redis')
        return None
    except Exception as e:
        log.error(f'连接 Redis 失败: {e}')
        return None


def main():
    global _running

    # 注册信号处理
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    log.info('🦞 OpenClaw 控制监听器启动')
    log.info(f'   Redis URL: {REDIS_URL}')
    log.info(f'   监听频道: {CONTROL_CHANNEL}')

    # 连接 Redis
    redis_client = get_redis_client()
    if not redis_client:
        log.error('无法连接到 Redis，退出')
        sys.exit(1)

    # 订阅控制频道
    pubsub = redis_client.pubsub()
    pubsub.psubscribe(CONTROL_CHANNEL)

    log.info('开始监听控制指令... (Ctrl+C 停止)')

    try:
        while _running:
            # 非阻塞获取消息
            message = pubsub.get_message(timeout=1)
            if message and message['type'] == 'pmessage':
                channel = message['channel']
                data = message['data']

                try:
                    if isinstance(data, str):
                        command = json.loads(data)
                    else:
                        command = data

                    # 处理命令
                    result = handle_control_command(command)

                    # 发布结果
                    publish_result(redis_client, result)

                    log.info(f'指令执行结果: {result.get("ok")} - {result.get("message", result.get("error"))}')

                except json.JSONDecodeError as e:
                    log.warning(f'无效的 JSON 数据: {e}')
                except Exception as e:
                    log.error(f'处理指令失败: {e}')

            # 短暂休眠
            time.sleep(0.1)

    except Exception as e:
        log.error(f'监听循环异常: {e}')
    finally:
        pubsub.punsubscribe(CONTROL_CHANNEL)
        pubsub.close()
        redis_client.close()
        log.info('控制监听器已停止')


if __name__ == '__main__':
    main()
