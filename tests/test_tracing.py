#!/usr/bin/env python3
"""单元测试 - 分布式追踪服务"""

import unittest
from dataclasses import dataclass, field, asdict
from typing import Optional
import uuid
from datetime import datetime, timezone

# 复制核心逻辑进行测试（避免导入 Python 3.10+ 的后端代码）

@dataclass
class TraceContext:
    """W3C Trace Context 格式"""
    trace_id: str
    parent_span_id: str
    flags: int = 1

    def to_traceparent(self) -> str:
        return f"00-{self.trace_id}-{self.parent_span_id}-{self.flags:02x}"

    @classmethod
    def from_traceparent(cls, traceparent: str) -> Optional["TraceContext"]:
        try:
            parts = traceparent.split("-")
            if len(parts) != 4 or parts[0] != "00":
                return None
            trace_id = parts[1]
            parent_id = parts[2]
            flags = int(parts[3], 16)
            if len(trace_id) != 32 or len(parent_id) != 16:
                return None
            return cls(trace_id=trace_id, parent_span_id=parent_id, flags=flags)
        except (ValueError, IndexError):
            return None

    @classmethod
    def new(cls) -> "TraceContext":
        trace_id = uuid.uuid4().hex
        span_id = uuid.uuid4().hex[:16]
        return cls(trace_id=trace_id, parent_span_id=span_id)

    def child(self) -> "TraceContext":
        new_span_id = uuid.uuid4().hex[:16]
        return TraceContext(trace_id=self.trace_id, parent_span_id=new_span_id, flags=self.flags)


@dataclass
class Span:
    """追踪 Span"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    name: str = ""
    kind: str = "INTERNAL"
    start_time: str = ""
    end_time: Optional[str] = None
    status: str = "OK"
    attributes: dict = field(default_factory=dict)
    events: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class TracingService:
    """分布式追踪服务（简化版用于测试）"""

    def __init__(self):
        self._spans = {}  # trace_id -> [Span]
        self._span_index = {}  # span_id -> Span

    def start_span(
        self,
        name: str,
        trace_context: Optional[TraceContext] = None,
        parent_span_id: Optional[str] = None,
        kind: str = "INTERNAL",
        attributes: Optional[dict] = None,
    ):
        is_new_trace = trace_context is None
        if is_new_trace:
            trace_context = TraceContext.new()

        span_id = uuid.uuid4().hex[:16]
        start_time = datetime.now(timezone.utc).isoformat()

        # 新 trace 的第一个 span 是根 span，parent_span_id 为 None
        # 继续已有 trace 时，使用传入的 parent_span_id 或 trace_context 的 parent_span_id
        if is_new_trace:
            actual_parent_id = None
        elif parent_span_id is not None:
            actual_parent_id = parent_span_id
        else:
            actual_parent_id = trace_context.parent_span_id

        span = Span(
            trace_id=trace_context.trace_id,
            span_id=span_id,
            parent_span_id=actual_parent_id,
            name=name,
            kind=kind,
            start_time=start_time,
            attributes=attributes or {},
        )

        self._spans.setdefault(trace_context.trace_id, []).append(span)
        self._span_index[span_id] = span

        new_context = TraceContext(
            trace_id=trace_context.trace_id,
            parent_span_id=span_id,
            flags=trace_context.flags,
        )

        return span, new_context

    def end_span(self, span_id: str, status: str = "OK", attributes: Optional[dict] = None):
        span = self._span_index.get(span_id)
        if span is None:
            return None

        span.end_time = datetime.now(timezone.utc).isoformat()
        span.status = status
        if attributes:
            span.attributes.update(attributes)

        return span

    def add_event(self, span_id: str, name: str, attributes: Optional[dict] = None):
        span = self._span_index.get(span_id)
        if span is None:
            return

        event = {
            "name": name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "attributes": attributes or {},
        }
        span.events.append(event)

    def get_trace(self, trace_id: str):
        spans = self._spans.get(trace_id, [])
        return [span.to_dict() for span in spans]

    def get_span(self, span_id: str):
        span = self._span_index.get(span_id)
        return span.to_dict() if span else None

    def get_trace_tree(self, trace_id: str):
        spans = self._spans.get(trace_id, [])
        if not spans:
            return {"trace_id": trace_id, "spans": [], "trees": []}

        span_map = {s.span_id: s.to_dict() for s in spans}

        def build_tree(span_id: str) -> dict:
            span = span_map[span_id]
            children = [
                build_tree(s.span_id)
                for s in spans
                if s.parent_span_id == span_id
            ]
            return {**span, "children": children}

        root_spans = [s for s in spans if s.parent_span_id is None]
        trees = [build_tree(s.span_id) for s in root_spans]

        return {
            "trace_id": trace_id,
            "span_count": len(spans),
            "spans": [s.to_dict() for s in spans],
            "trees": trees,
        }


# ── 测试用例 ──

class TestTraceContext(unittest.TestCase):
    """TraceContext 测试"""

    def test_new_trace_context(self):
        """测试创建新的 trace context"""
        ctx = TraceContext.new()

        self.assertEqual(len(ctx.trace_id), 32)
        self.assertEqual(len(ctx.parent_span_id), 16)
        self.assertEqual(ctx.flags, 1)

    def test_to_traceparent(self):
        """测试序列化为 traceparent"""
        ctx = TraceContext(trace_id="0" * 32, parent_span_id="1" * 16, flags=1)
        traceparent = ctx.to_traceparent()

        self.assertTrue(traceparent.startswith("00-"))
        self.assertIn("0" * 32, traceparent)
        self.assertIn("1" * 16, traceparent)
        self.assertTrue(traceparent.endswith("-01"))

    def test_from_traceparent_valid(self):
        """测试从有效的 traceparent 解析"""
        traceparent = "00-" + "a" * 32 + "-" + "b" * 16 + "-01"
        ctx = TraceContext.from_traceparent(traceparent)

        self.assertIsNotNone(ctx)
        self.assertEqual(ctx.trace_id, "a" * 32)
        self.assertEqual(ctx.parent_span_id, "b" * 16)
        self.assertEqual(ctx.flags, 1)

    def test_from_traceparent_invalid(self):
        """测试从无效的 traceparent 解析"""
        # 格式错误
        self.assertIsNone(TraceContext.from_traceparent("invalid"))
        # 版本错误
        self.assertIsNone(TraceContext.from_traceparent("01-" + "a" * 32 + "-" + "b" * 16 + "-01"))
        # 长度错误
        self.assertIsNone(TraceContext.from_traceparent("00-abc-" + "b" * 16 + "-01"))

    def test_child_context(self):
        """测试创建子 context"""
        parent = TraceContext.new()
        child = parent.child()

        # 同一 trace_id
        self.assertEqual(parent.trace_id, child.trace_id)
        # 不同的 span_id
        self.assertNotEqual(parent.parent_span_id, child.parent_span_id)


class TestTracingService(unittest.TestCase):
    """TracingService 测试"""

    def setUp(self):
        self.service = TracingService()

    def test_start_span(self):
        """测试开始 span"""
        span, ctx = self.service.start_span("test-operation")

        self.assertEqual(span.name, "test-operation")
        self.assertIsNotNone(span.start_time)
        self.assertIsNone(span.end_time)
        self.assertEqual(span.trace_id, ctx.trace_id)

    def test_end_span(self):
        """测试结束 span"""
        span, _ = self.service.start_span("test")
        ended_span = self.service.end_span(span.span_id, status="OK")

        self.assertIsNotNone(ended_span)
        self.assertEqual(ended_span.status, "OK")
        self.assertIsNotNone(ended_span.end_time)

    def test_end_nonexistent_span(self):
        """测试结束不存在的 span"""
        result = self.service.end_span("nonexistent")
        self.assertIsNone(result)

    def test_add_event(self):
        """测试添加事件"""
        span, _ = self.service.start_span("test")
        self.service.add_event(span.span_id, "checkpoint", {"key": "value"})

        retrieved = self.service.get_span(span.span_id)
        self.assertEqual(len(retrieved["events"]), 1)
        self.assertEqual(retrieved["events"][0]["name"], "checkpoint")

    def test_get_trace(self):
        """测试获取追踪"""
        span1, _ = self.service.start_span("op1")
        span2, _ = self.service.start_span("op2")

        trace1 = self.service.get_trace(span1.trace_id)
        trace2 = self.service.get_trace(span2.trace_id)

        self.assertEqual(len(trace1), 1)
        self.assertEqual(len(trace2), 1)

    def test_get_trace_tree(self):
        """测试获取追踪树"""
        # 创建根 span
        root_span, ctx = self.service.start_span("root")

        # 创建子 span
        child_span, _ = self.service.start_span("child", trace_context=ctx)

        tree = self.service.get_trace_tree(root_span.trace_id)

        self.assertEqual(tree["span_count"], 2)
        self.assertEqual(len(tree["trees"]), 1)
        self.assertEqual(tree["trees"][0]["name"], "root")

    def test_span_attributes(self):
        """测试 span 属性"""
        span, _ = self.service.start_span("test", attributes={"key1": "value1"})

        self.assertEqual(span.attributes["key1"], "value1")

        # 结束时添加属性
        self.service.end_span(span.span_id, attributes={"key2": "value2"})

        retrieved = self.service.get_span(span.span_id)
        self.assertEqual(retrieved["attributes"]["key2"], "value2")


class TestSpanRelationships(unittest.TestCase):
    """Span 关系测试"""

    def setUp(self):
        self.service = TracingService()

    def test_parent_child_relationship(self):
        """测试父子关系"""
        # 根 span
        root, ctx1 = self.service.start_span("root")

        # 子 span
        child1, ctx2 = self.service.start_span("child1", trace_context=ctx1)

        # 孙 span
        grandchild, _ = self.service.start_span("grandchild", trace_context=ctx2)

        # 验证关系
        self.assertIsNone(root.parent_span_id)
        self.assertEqual(child1.parent_span_id, root.span_id)
        self.assertEqual(grandchild.parent_span_id, child1.span_id)

        # 所有 span 共享同一 trace_id
        self.assertEqual(root.trace_id, child1.trace_id)
        self.assertEqual(root.trace_id, grandchild.trace_id)


if __name__ == '__main__':
    unittest.main()
