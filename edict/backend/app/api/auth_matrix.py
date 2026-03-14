"""Auth Matrix API — 动态权限矩阵管理。

端点：
- GET /api/auth-matrix — 获取完整权限矩阵
- GET /api/auth-matrix/{agent_id} — 获取指定 Agent 权限
- POST /api/auth-matrix/grant — 授权
- POST /api/auth-matrix/revoke — 撤销
- GET /api/auth-matrix/audit — 审计日志
- POST /api/auth-matrix/check — 检查权限
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..services.auth_matrix import get_auth_matrix_service

log = logging.getLogger("edict.api.auth_matrix")
router = APIRouter()


# ── 请求模型 ──

class GrantRequest(BaseModel):
    """授权请求。"""
    from_agent: str = Field(..., description="授权方 Agent ID")
    to_agent: str = Field(..., description="被授权调用的 Agent ID")
    reason: str | None = Field(None, description="授权原因")
    operator: str | None = Field(None, description="操作者（通常是用户或管理员 Agent）")


class RevokeRequest(BaseModel):
    """撤销请求。"""
    from_agent: str = Field(..., description="被撤销方 Agent ID")
    to_agent: str = Field(..., description="被撤销调用的 Agent ID")
    reason: str | None = Field(None, description="撤销原因")
    operator: str | None = Field(None, description="操作者")


class CheckRequest(BaseModel):
    """权限检查请求。"""
    from_agent: str = Field(..., description="调用方 Agent ID")
    to_agent: str = Field(..., description="被调用方 Agent ID")


# ── API 端点 ──

@router.get("")
async def get_matrix() -> dict[str, Any]:
    """获取完整权限矩阵。

    返回：
    - permissions: 每个 Agent 的 allow/deny 列表
    - meta: Agent 元信息（名称、角色、图标）
    - last_updated: 最后更新时间
    """
    service = get_auth_matrix_service()
    return service.get_matrix()


@router.get("/{agent_id}")
async def get_agent_permissions(agent_id: str) -> dict[str, Any]:
    """获取指定 Agent 的权限。"""
    service = get_auth_matrix_service()

    if agent_id not in service._permissions:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    perms = service.get_agent_permissions(agent_id)
    return {
        "agent_id": agent_id,
        "permissions": perms,
        "meta": service.get_matrix()["meta"].get(agent_id, {}),
    }


@router.post("/grant")
async def grant_permission(request: GrantRequest) -> dict[str, Any]:
    """授权 Agent 调用权限。

    允许 from_agent 调用 to_agent。
    如果已被 deny，会自动移除 deny。
    """
    service = get_auth_matrix_service()

    granted = service.grant(
        from_agent=request.from_agent,
        to_agent=request.to_agent,
        reason=request.reason,
        operator=request.operator,
    )

    return {
        "success": True,
        "granted": granted,
        "message": f"Granted: {request.from_agent} → {request.to_agent}" if granted
                   else f"Already had permission: {request.from_agent} → {request.to_agent}",
    }


@router.post("/revoke")
async def revoke_permission(request: RevokeRequest) -> dict[str, Any]:
    """撤销 Agent 调用权限。

    撤销 from_agent 调用 to_agent 的权限。
    会被添加到 deny 列表以显式禁止。
    """
    service = get_auth_matrix_service()

    revoked = service.revoke(
        from_agent=request.from_agent,
        to_agent=request.to_agent,
        reason=request.reason,
        operator=request.operator,
    )

    return {
        "success": True,
        "revoked": revoked,
        "message": f"Revoked: {request.from_agent} → {request.to_agent}" if revoked
                   else f"Did not have permission: {request.from_agent} → {request.to_agent}",
    }


@router.post("/check")
async def check_permission(request: CheckRequest) -> dict[str, Any]:
    """检查调用权限。

    返回 from_agent 是否可以调用 to_agent。
    """
    service = get_auth_matrix_service()

    can_call = service.can_call(
        from_agent=request.from_agent,
        to_agent=request.to_agent,
    )

    return {
        "from_agent": request.from_agent,
        "to_agent": request.to_agent,
        "can_call": can_call,
    }


@router.get("/audit")
async def get_audit_log(limit: int = 100) -> dict[str, Any]:
    """获取权限变更审计日志。

    返回最近的权限变更记录。
    """
    service = get_auth_matrix_service()
    log_entries = service.get_audit_log(limit=limit)

    return {
        "count": len(log_entries),
        "entries": log_entries,
    }


@router.get("/matrix/visual")
async def get_visual_matrix() -> dict[str, Any]:
    """获取可视化权限矩阵（用于前端渲染）。

    返回一个二维矩阵，显示所有 Agent 之间的调用权限。
    """
    service = get_auth_matrix_service()
    matrix_data = service.get_matrix()
    permissions = matrix_data["permissions"]
    meta = matrix_data["meta"]

    # 获取所有 Agent ID
    all_agents = list(set(permissions.keys()) | set(meta.keys()))
    all_agents.sort()

    # 构建可视化矩阵
    matrix = []
    for from_agent in all_agents:
        row = {"from": from_agent, "from_name": meta.get(from_agent, {}).get("name", from_agent)}
        for to_agent in all_agents:
            if from_agent == to_agent:
                row[to_agent] = "—"  # 自己不能调自己
            else:
                can_call = service.can_call(from_agent, to_agent)
                row[to_agent] = "✅" if can_call else "❌"
        matrix.append(row)

    return {
        "agents": [{"id": a, "name": meta.get(a, {}).get("name", a)} for a in all_agents],
        "matrix": matrix,
    }
