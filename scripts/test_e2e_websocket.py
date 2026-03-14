#!/usr/bin/env python3
"""端到端 WebSocket 测试 — 验证实时推送完整流程。

测试流程:
1. 启动 WebSocket 服务器 (连接 Redis)
2. 启动 WebSocket 客户端
3. 触发数据刷新
4. 验证客户端收到事件
"""

import asyncio
import json
import logging
import sys
import time
import pathlib

# 添加脚本目录
sys.path.insert(0, str(pathlib.Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s')
log = logging.getLogger('e2e_test')

# WebSocket 服务器 (使用 websockets 库)
async def websocket_server():
    """简单的 WebSocket 服务器，订阅 Redis 并转发事件"""
    import websockets
    import redis.asyncio as aioredis

    redis_client = aioredis.from_url('redis://localhost:6379/0', decode_responses=True)
    pubsub = redis_client.pubsub()
    await pubsub.psubscribe('edict:pubsub:*')

    log.info('WebSocket 服务器启动在 ws://127.0.0.1:8765')

    async def handler(websocket):
        log.info(f'客户端连接: {websocket.remote_address}')
        try:
            async for message in pubsub.listen():
                if message['type'] == 'pmessage':
                    event = {
                        'type': 'event',
                        'topic': message['channel'].replace('edict:pubsub:', ''),
                        'data': json.loads(message['data']) if isinstance(message['data'], str) else message['data']
                    }
                    await websocket.send(json.dumps(event, ensure_ascii=False))
                    log.info(f'发送事件: {event["topic"]}')
        except Exception as e:
            log.info(f'连接关闭: {e}')

    async with websockets.serve(handler, '127.0.0.1', 8765):
        await asyncio.Future()  # 永远运行


async def websocket_client():
    """WebSocket 客户端，接收事件"""
    import websockets

    await asyncio.sleep(1)  # 等待服务器启动

    log.info('客户端连接到 ws://127.0.0.1:8765')
    events = []

    async with websockets.connect('ws://127.0.0.1:8765') as ws:
        # 触发刷新
        import subprocess
        log.info('触发数据刷新...')
        subprocess.run(['python3', 'scripts/refresh_live_data.py'], capture_output=True)

        # 等待接收事件
        try:
            for _ in range(10):  # 最多等待 10 次消息
                message = await asyncio.wait_for(ws.recv(), timeout=2.0)
                event = json.loads(message)
                events.append(event)
                log.info(f'收到事件: {event.get("topic", "unknown")}')

                # 收到 sync.complete 就算成功
                if event.get('topic') == 'sync.complete':
                    log.info('✅ 测试成功！收到 sync.complete 事件')
                    break
        except asyncio.TimeoutError:
            log.warning('等待超时')

    return events


async def main():
    log.info('=' * 50)
    log.info('端到端 WebSocket 测试')
    log.info('=' * 50)

    # 检查依赖
    try:
        import websockets
        import redis.asyncio
    except ImportError as e:
        log.error(f'缺少依赖: {e}')
        log.info('请运行: pip install websockets redis')
        return False

    # 启动服务器和客户端
    server_task = asyncio.create_task(websocket_server())

    # 等待服务器启动
    await asyncio.sleep(1)

    # 运行客户端测试
    events = await websocket_client()

    # 取消服务器
    server_task.cancel()

    # 报告结果
    log.info('=' * 50)
    log.info(f'测试完成，共收到 {len(events)} 个事件')

    success = any(e.get('topic') == 'sync.complete' for e in events)
    if success:
        log.info('✅ 端到端测试通过！')
    else:
        log.warning('❌ 未收到 sync.complete 事件')

    return success


if __name__ == '__main__':
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        log.info('测试中断')
        sys.exit(1)
