"""分布式追踪服务 — 跨 Agent 调用链可追踪。

核心能力：
- 生成/解析 trace context (W3C traceparent 格式)
- 记录 span 到 Redis 或内存
- 查询追踪链路
- 与 EventBus 集成自动注入 trace_id
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from dataclasses import dataclass, field, asdict

log = logging.getLogger("edict.tracing")

# ── Trace Context ──

@dataclass
class TraceContext:
    """W3C Trace Context 格式。

    traceparent: 00-{trace_id}-{parent_id}-{flags}
    - version: 00 (1 byte hex)
    - trace_id: 32 hex chars (16 bytes)
    - parent_id: 16 hex chars (8 bytes)
    - flags: 2 hex chars (1 byte)
    """
    trace_id: str  # 32 hex chars
    parent_span_id: str  # 16 hex chars
    flags: int = 1  # 01 = sampled

    def to_traceparent(self) -> str:
        """序列化为 W3C traceparent 格式。"""
        return f"00-{self.trace_id}-{self.parent_span_id}-{self.flags:02x}"

    @classmethod
    def from_traceparent(cls, traceparent: str) -> Optional["TraceContext"]:
        """从 W3C traceparent 解析。"""
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
        """创建新的 trace context。"""
        trace_id = uuid.uuid4().hex  # 32 hex chars
        span_id = uuid.uuid4().hex[:16]  # 16 hex chars
        return cls(trace_id=trace_id, parent_span_id=span_id)

    def child(self) -> "TraceContext":
        """创建子 span（同一 trace_id，新 parent_span_id）。"""
        new_span_id = uuid.uuid4().hex[:16]
        return TraceContext(trace_id=self.trace_id, parent_span_id=new_span_id, flags=self.flags)


# ── Span 数据结构 ──

@dataclass
class Span:
    """追踪 Span。"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    name: str = ""
    kind: str = "INTERNAL"  # INTERNAL, CLIENT, SERVER, PRODUCER, CONSUMER
    start_time: str = ""
    end_time: Optional[str] = None
    status: str = "OK"  # OK, ERROR, CANCELLED
    attributes: dict = field(default_factory=dict)
    events: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Span":
        return cls(**data)


# ── 追踪服务 ──

class TracingService:
    """分布式追踪服务。

    存储方式：
    - 使用内存字典存储（单机）
    - 可扩展为 Redis 存储（分布式）
    """

    def __init__(self, storage_path: Optional[str] = None):
        self._storage_path = storage_path
        self._spans: dict[str, list[Span]] = {}  # trace_id -> [Span]
        self._span_index: dict[str, Span] = {}  # span_id -> Span

    def start_span(
        self,
        name: str,
        trace_context: Optional[TraceContext] = None,
        parent_span_id: Optional[str] = None,
        kind: str = "INTERNAL",
        attributes: Optional[dict] = None,
    ) -> tuple[Span, TraceContext]:
        """开始一个新的 span。

        Returns:
            (Span, TraceContext): 新 span 和对应的 trace context
        """
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

        # 存储
        self._spans.setdefault(trace_context.trace_id, []).append(span)
        self._span_index[span_id] = span

        # 更新 trace context 的 parent_span_id 为当前 span
        new_context = TraceContext(
            trace_id=trace_context.trace_id,
            parent_span_id=span_id,
            flags=trace_context.flags,
        )

        log.debug(f"📍 Started span: {name} [{span_id[:8]}] trace={trace_context.trace_id[:8]}")
        return span, new_context

    def end_span(
        self,
        span_id: str,
        status: str = "OK",
        attributes: Optional[dict] = None,
    ) -> Optional[Span]:
        """结束 span。"""
        span = self._span_index.get(span_id)
        if span is None:
            return None

        span.end_time = datetime.now(timezone.utc).isoformat()
        span.status = status
        if attributes:
            span.attributes.update(attributes)

        log.debug(f"✅ Ended span: {span.name} [{span_id[:8]}] status={status}")
        return span

    def add_event(self, span_id: str, name: str, attributes: Optional[dict] = None):
        """向 span 添加事件。"""
        span = self._span_index.get(span_id)
        if span is None:
            return

        event = {
            "name": name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "attributes": attributes or {},
        }
        span.events.append(event)

    def get_trace(self, trace_id: str) -> list[dict]:
        """获取完整追踪链路。"""
        spans = self._spans.get(trace_id, [])
        return [span.to_dict() for span in spans]

    def get_span(self, span_id: str) -> Optional[dict]:
        """获取单个 span。"""
        span = self._span_index.get(span_id)
        return span.to_dict() if span else None

    def get_trace_tree(self, trace_id: str) -> dict:
        """获取追踪树结构（用于可视化）。"""
        spans = self._spans.get(trace_id, [])
        if not spans:
            return {"trace_id": trace_id, "spans": [], "tree": None}

        # 构建 span 索引
        span_map = {s.span_id: s.to_dict() for s in spans}

        # 构建树结构
        def build_tree(span_id: str) -> dict:
            span = span_map[span_id]
            children = [
                build_tree(s.span_id)
                for s in spans
                if s.parent_span_id == span_id
            ]
            return {**span, "children": children}

        # 找到根 span
        root_spans = [s for s in spans if s.parent_span_id is None]
        trees = [build_tree(s.span_id) for s in root_spans]

        return {
            "trace_id": trace_id,
            "span_count": len(spans),
            "spans": [s.to_dict() for s in spans],
            "trees": trees,
        }

    def list_traces(self, limit: int = 100) -> list[dict]:
        """列出最近的追踪。"""
        traces = []
        for trace_id, spans in list(self._spans.items())[-limit:]:
            if spans:
                first_span = spans[0]
                last_span = spans[-1]
                traces.append({
                    "trace_id": trace_id,
                    "span_count": len(spans),
                    "start_time": first_span.start_time,
                    "end_time": last_span.end_time,
                    "status": "ERROR" if any(s.status == "ERROR" for s in spans) else "OK",
                    "root_name": first_span.name,
                })
        return traces

    def clear_old_traces(self, max_traces: int = 1000):
        """清理旧追踪（内存管理）。"""
        if len(self._spans) > max_traces:
            # 保留最近的 traces
            keys_to_remove = list(self._spans.keys())[:-max_traces]
            for key in keys_to_remove:
                for span in self._spans[key]:
                    self._span_index.pop(span.span_id, None)
                del self._spans[key]
            log.info(f"🧹 Cleared {len(keys_to_remove)} old traces")

    def continue_trace(
        self,
        traceparent: str,
        name: str,
        attributes: Optional[dict] = None,
    ) -> tuple[Span, TraceContext]:
        """从 traceparent 继续追踪。

        Args:
            traceparent: W3C traceparent 格式的追踪上下文
            name: Span 名称
            attributes: Span 属性

        Returns:
            (Span, TraceContext): 新 span 和更新后的 trace context
        """
        ctx = TraceContext.from_traceparent(traceparent)
        if ctx is None:
            # 无效的 traceparent，创建新 trace
            ctx = TraceContext.new()
        return self.start_span(name, trace_context=ctx, attributes=attributes)


# ── 全局单例 ──
_service: Optional[TracingService] = None


def get_tracing_service() -> TracingService:
    """获取追踪服务单例。"""
    global _service
    if _service is None:
        _service = TracingService()
    return _service


# ── 便捷函数 ──

def start_trace(name: str, **kwargs) -> tuple[Span, TraceContext]:
    """开始新的追踪。"""
    return get_tracing_service().start_span(name, **kwargs)


def continue_trace(traceparent: str, name: str, **kwargs) -> tuple[Span, TraceContext]:
    """从 traceparent 继续追踪。"""
    ctx = TraceContext.from_traceparent(traceparent)
    if ctx is None:
        ctx = TraceContext.new()
    return get_tracing_service().start_span(name, trace_context=ctx, **kwargs)
