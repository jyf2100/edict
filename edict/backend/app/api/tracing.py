"""Tracing API — 分布式追踪查询。

端点：
- GET /api/traces — 列出最近的追踪
- GET /api/traces/{trace_id} — 获取追踪详情
- GET /api/traces/{trace_id}/tree — 获取追踪树结构
- GET /api/spans/{span_id} — 获取单个 span
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..services.tracing import (
    get_tracing_service,
    TraceContext,
    start_trace,
    continue_trace,
)

log = logging.getLogger("edict.api.tracing")
router = APIRouter()


# ── 请求/响应模型 ──

class StartTraceRequest(BaseModel):
    """开始追踪请求。"""
    name: str = Field(..., description="Span 名称")
    kind: str = Field("INTERNAL", description="Span 类型: INTERNAL, CLIENT, SERVER, PRODUCER, CONSUMER")
    attributes: Optional[dict] = Field(None, description="Span 属性")


class ContinueTraceRequest(BaseModel):
    """继续追踪请求。"""
    traceparent: str = Field(..., description="W3C traceparent 格式的追踪上下文")
    name: str = Field(..., description="Span 名称")
    attributes: Optional[dict] = Field(None, description="Span 属性")


class EndSpanRequest(BaseModel):
    """结束 Span 请求。"""
    span_id: str = Field(..., description="Span ID")
    status: str = Field("OK", description="状态: OK, ERROR, CANCELLED")
    attributes: Optional[dict] = Field(None, description="额外属性")


class AddEventRequest(BaseModel):
    """添加事件请求。"""
    span_id: str = Field(..., description="Span ID")
    name: str = Field(..., description="事件名称")
    attributes: Optional[dict] = Field(None, description="事件属性")


# ── API 端点 ──

@router.get("")
async def list_traces(limit: int = Query(100, ge=1, le=1000)) -> dict[str, Any]:
    """列出最近的追踪。

    返回追踪摘要列表。
    """
    service = get_tracing_service()
    traces = service.list_traces(limit=limit)

    return {
        "count": len(traces),
        "traces": traces,
    }


@router.get("/{trace_id}")
async def get_trace(trace_id: str) -> dict[str, Any]:
    """获取追踪详情。

    返回追踪中的所有 span。
    """
    service = get_tracing_service()
    spans = service.get_trace(trace_id)

    if not spans:
        raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found")

    return {
        "trace_id": trace_id,
        "span_count": len(spans),
        "spans": spans,
    }


@router.get("/{trace_id}/tree")
async def get_trace_tree(trace_id: str) -> dict[str, Any]:
    """获取追踪树结构。

    返回层次化的 span 结构，便于可视化。
    """
    service = get_tracing_service()
    tree = service.get_trace_tree(trace_id)

    if not tree["spans"]:
        raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found")

    return tree


@router.get("/spans/{span_id}")
async def get_span(span_id: str) -> dict[str, Any]:
    """获取单个 span 详情。"""
    service = get_tracing_service()
    span = service.get_span(span_id)

    if not span:
        raise HTTPException(status_code=404, detail=f"Span '{span_id}' not found")

    return span


@router.post("/start")
async def start_new_trace(request: StartTraceRequest) -> dict[str, Any]:
    """开始新的追踪。

    创建新的 trace context 和根 span。
    返回 span 信息和 traceparent 用于传递给下游。
    """
    service = get_tracing_service()
    span, ctx = service.start_span(
        name=request.name,
        kind=request.kind,
        attributes=request.attributes,
    )

    return {
        "span": span.to_dict(),
        "traceparent": ctx.to_traceparent(),
        "trace_id": ctx.trace_id,
        "span_id": span.span_id,
    }


@router.post("/continue")
async def continue_existing_trace(request: ContinueTraceRequest) -> dict[str, Any]:
    """继续已有追踪。

    从 traceparent 解析 trace context 并创建子 span。
    """
    service = get_tracing_service()
    span, ctx = service.continue_trace(
        traceparent=request.traceparent,
        name=request.name,
        attributes=request.attributes,
    )

    return {
        "span": span.to_dict(),
        "traceparent": ctx.to_traceparent(),
        "trace_id": ctx.trace_id,
        "span_id": span.span_id,
    }


@router.post("/end")
async def end_span(request: EndSpanRequest) -> dict[str, Any]:
    """结束 span。"""
    service = get_tracing_service()
    span = service.end_span(
        span_id=request.span_id,
        status=request.status,
        attributes=request.attributes,
    )

    if not span:
        raise HTTPException(status_code=404, detail=f"Span '{request.span_id}' not found")

    return {
        "success": True,
        "span": span.to_dict(),
    }


@router.post("/events")
async def add_event(request: AddEventRequest) -> dict[str, Any]:
    """向 span 添加事件。"""
    service = get_tracing_service()
    service.add_event(
        span_id=request.span_id,
        name=request.name,
        attributes=request.attributes,
    )

    return {
        "success": True,
        "message": f"Event '{request.name}' added to span {request.span_id}",
    }


@router.post("/clear")
async def clear_old_traces(max_traces: int = 1000) -> dict[str, Any]:
    """清理旧追踪（内存管理）。"""
    service = get_tracing_service()
    service.clear_old_traces(max_traces=max_traces)

    return {
        "success": True,
        "message": f"Cleaned up traces, keeping last {max_traces}",
    }
