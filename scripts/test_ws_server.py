#!/usr/bin/env python3
"""简化的 WebSocket 测试服务器 - 用于测试前端 WebSocket 连接。

运行方式:
    python3 scripts/test_ws_server.py

然后在浏览器打开前端，WebSocket 应该能连接到 ws://127.0.0.1:8000/ws
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import struct

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s')
log = logging.getLogger('ws_test')

# WebSocket magic string for Sec-WebSocket-Accept
WS_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

import hashlib
import base64

class WebSocketHandler:
    """简单的 WebSocket 处理器"""

    def __init__(self, client_socket):
        self.socket = client_socket
        self.connected = True

    def send_frame(self, data: str):
        """发送 WebSocket 文本帧"""
        payload = data.encode('utf-8')
        length = len(payload)

        # FIN + Text frame (opcode 0x01)
        frame = bytearray([0x81])

        if length <= 125:
            frame.append(length)
        elif length <= 65535:
            frame.append(126)
            frame.extend(struct.pack('!H', length))
        else:
            frame.append(127)
            frame.extend(struct.pack('!Q', length))

        frame.extend(payload)
        self.socket.sendall(bytes(frame))

    def recv_frame(self):
        """接收 WebSocket 帧"""
        header = self.socket.recv(2)
        if len(header) < 2:
            return None

        opcode = header[0] & 0x0F
        masked = (header[1] & 0x80) != 0
        length = header[1] & 0x7F

        if length == 126:
            length = struct.unpack('!H', self.socket.recv(2))[0]
        elif length == 127:
            length = struct.unpack('!Q', self.socket.recv(8))[0]

        mask_key = None
        if masked:
            mask_key = self.socket.recv(4)

        payload = self.socket.recv(length)

        if mask_key:
            decoded = bytearray()
            for i, byte in enumerate(payload):
                decoded.append(byte ^ mask_key[i % 4])
            payload = bytes(decoded)

        return payload.decode('utf-8') if opcode == 0x01 else None

    def handle(self):
        """处理 WebSocket 连接"""
        log.info("WebSocket client connected")

        # 发送欢迎消息
        self.send_json({
            "type": "event",
            "topic": "system.connected",
            "data": {"message": "WebSocket connected successfully!", "timestamp": datetime.now(timezone.utc).isoformat()}
        })

        # 定期发送心跳
        counter = 0
        while self.connected:
            try:
                # 非阻塞接收
                self.socket.settimeout(0.1)
                try:
                    msg = self.recv_frame()
                    if msg:
                        data = json.loads(msg)
                        log.info(f"Received: {data}")
                        if data.get('type') == 'ping':
                            self.send_json({"type": "pong"})
                        elif data.get('type') == 'subscribe':
                            self.send_json({"type": "subscribed", "topics": data.get('topics', [])})
                except socket.timeout:
                    pass
                except BlockingIOError:
                    pass

                # 每 5 秒发送一个心跳事件
                counter += 1
                if counter % 50 == 0:  # ~5 seconds (50 * 0.1s)
                    self.send_json({
                        "type": "event",
                        "topic": "sync.complete",
                        "data": {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "record_count": 5,
                            "message": "Heartbeat from test server"
                        }
                    })

            except Exception as e:
                log.info(f"WebSocket disconnected: {e}")
                self.connected = False
                break

    def send_json(self, data: dict):
        self.send_frame(json.dumps(data, ensure_ascii=False))


class HTTPRequestHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器 - 处理 WebSocket 升级和健康检查"""

    def log_message(self, format, *args):
        log.info(f"HTTP: {args[0]}")

    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "version": "test"}).encode())

        elif self.path == '/ws':
            # WebSocket 升级
            ws_key = self.headers.get('Sec-WebSocket-Key')
            if not ws_key:
                self.send_response(400)
                self.end_headers()
                return

            # 计算接受密钥
            accept_key = base64.b64encode(
                hashlib.sha1((ws_key + WS_MAGIC).encode()).digest()
            ).decode()

            self.send_response(101)
            self.send_header('Upgrade', 'websocket')
            self.send_header('Connection', 'Upgrade')
            self.send_header('Sec-WebSocket-Accept', accept_key)
            self.end_headers()

            # 切换到 WebSocket 协议
            ws = WebSocketHandler(self.connection)
            ws.handle()

        else:
            self.send_response(404)
            self.end_headers()


def main():
    import socket

    server_address = ('127.0.0.1', 8000)
    httpd = HTTPServer(server_address, HTTPRequestHandler)

    log.info(f"🚀 Test WebSocket server running at http://127.0.0.1:8000")
    log.info(f"   WebSocket endpoint: ws://127.0.0.1:8000/ws")
    log.info(f"   Health check: http://127.0.0.1:8000/health")
    log.info(f"")
    log.info(f"   Open the frontend and check browser console for WebSocket messages")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        log.info("\nShutting down...")
        httpd.shutdown()


if __name__ == '__main__':
    main()
