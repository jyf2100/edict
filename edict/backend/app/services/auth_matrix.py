"""动态权限矩阵服务 — 运行时调整 Agent 调用权限。

核心能力：
- 获取当前权限矩阵（从 openclaw.json 或缓存）
- 动态授权/撤销 Agent 调用权限
- 权限变更事件发布
- 权限审计日志
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel

log = logging.getLogger("edict.auth_matrix")

# ── 权限矩阵默认配置（三省六部架构） ──
DEFAULT_PERMISSIONS = {
    "taizi": {"allowAgents": ["zhongshu"], "denyAgents": []},
    "zhongshu": {"allowAgents": ["menxia", "shangshu"], "denyAgents": []},
    "menxia": {"allowAgents": ["shangshu", "zhongshu"], "denyAgents": []},
    "shangshu": {"allowAgents": ["zhongshu", "menxia", "hubu", "libu", "bingbu", "xingbu", "gongbu", "libu_hr"], "denyAgents": []},
    "hubu": {"allowAgents": ["shangshu"], "denyAgents": []},
    "libu": {"allowAgents": ["shangshu"], "denyAgents": []},
    "bingbu": {"allowAgents": ["shangshu"], "denyAgents": []},
    "xingbu": {"allowAgents": ["shangshu"], "denyAgents": []},
    "gongbu": {"allowAgents": ["shangshu"], "denyAgents": []},
    "libu_hr": {"allowAgents": ["shangshu"], "denyAgents": []},
    "zaochao": {"allowAgents": [], "denyAgents": []},
}

# Agent 元信息
AGENT_META = {
    "taizi": {"name": "太子", "role": "储君", "icon": "👑"},
    "zhongshu": {"name": "中书省", "role": "起草诏令", "icon": "✍️"},
    "menxia": {"name": "门下省", "role": "审核封驳", "icon": "🔍"},
    "shangshu": {"name": "尚书省", "role": "执行调度", "icon": "📜"},
    "hubu": {"name": "户部", "role": "财务资源", "icon": "💰"},
    "libu": {"name": "礼部", "role": "礼仪外交", "icon": "🎁"},
    "bingbu": {"name": "兵部", "role": "安全应急", "icon": "🛡️"},
    "xingbu": {"name": "刑部", "role": "规范审查", "icon": "⚖️"},
    "gongbu": {"name": "工部", "role": "工程实施", "icon": "🔧"},
    "libu_hr": {"name": "吏部", "role": "人事组织", "icon": "👤"},
    "zaochao": {"name": "早朝", "role": "朝会主持", "icon": "🏛️"},
}


class PermissionChange(BaseModel):
    """权限变更记录。"""
    timestamp: str
    action: str  # grant, revoke
    from_agent: str
    to_agent: str
    reason: str | None = None
    operator: str | None = None


class AuthMatrixService:
    """动态权限矩阵服务。"""

    def __init__(self, openclaw_config_path: Path | None = None, audit_path: Path | None = None):
        self._openclaw_config_path = openclaw_config_path or Path.home() / ".openclaw" / "openclaw.json"
        self._audit_path = audit_path or Path(__file__).parents[4] / "data" / "auth_audit.json"
        self._permissions: dict[str, dict[str, list[str]]] = {}
        self._audit_log: list[PermissionChange] = []
        self._loaded = False

    def _ensure_loaded(self):
        """确保权限已加载。"""
        if not self._loaded:
            self._load_permissions()
            self._loaded = True

    def _load_permissions(self):
        """从 OpenClaw 配置加载权限矩阵。"""
        if self._openclaw_config_path.exists():
            try:
                config = json.loads(self._openclaw_config_path.read_text(encoding="utf-8"))
                agents_list = config.get("agents", {}).get("list", [])
                for agent in agents_list:
                    agent_id = agent.get("id")
                    subagents = agent.get("subagents", {})
                    self._permissions[agent_id] = {
                        "allowAgents": subagents.get("allowAgents", []),
                        "denyAgents": subagents.get("denyAgents", []),
                    }
                log.info(f"Loaded permissions from OpenClaw config: {len(self._permissions)} agents")
            except (json.JSONDecodeError, IOError) as e:
                log.warning(f"Failed to load OpenClaw config: {e}, using defaults")
                self._permissions = DEFAULT_PERMISSIONS.copy()
        else:
            log.info("OpenClaw config not found, using default permissions")
            self._permissions = DEFAULT_PERMISSIONS.copy()

        # 加载审计日志
        self._load_audit_log()

    def _load_audit_log(self):
        """加载审计日志。"""
        if self._audit_path.exists():
            try:
                data = json.loads(self._audit_path.read_text(encoding="utf-8"))
                self._audit_log = [PermissionChange(**item) for item in data]
            except (json.JSONDecodeError, IOError):
                self._audit_log = []

    def _save_audit_log(self):
        """保存审计日志。"""
        self._audit_path.parent.mkdir(parents=True, exist_ok=True)
        data = [item.model_dump() for item in self._audit_log]
        self._audit_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_matrix(self) -> dict[str, Any]:
        """获取完整权限矩阵。"""
        self._ensure_loaded()
        return {
            "permissions": self._permissions,
            "meta": AGENT_META,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    def get_agent_permissions(self, agent_id: str) -> dict[str, list[str]]:
        """获取指定 Agent 的权限。"""
        self._ensure_loaded()
        return self._permissions.get(agent_id, {"allowAgents": [], "denyAgents": []})

    def can_call(self, from_agent: str, to_agent: str) -> bool:
        """检查 from_agent 是否可以调用 to_agent。"""
        self._ensure_loaded()
        perms = self._permissions.get(from_agent, {"allowAgents": [], "denyAgents": []})
        allowed = to_agent in perms.get("allowAgents", [])
        denied = to_agent in perms.get("denyAgents", [])
        # deny 优先于 allow
        return allowed and not denied

    def grant(
        self,
        from_agent: str,
        to_agent: str,
        reason: str | None = None,
        operator: str | None = None,
    ) -> bool:
        """授权 from_agent 调用 to_agent。

        Returns:
            True if permission was granted, False if already had permission
        """
        self._ensure_loaded()

        if from_agent not in self._permissions:
            self._permissions[from_agent] = {"allowAgents": [], "denyAgents": []}

        perms = self._permissions[from_agent]

        # 移除 deny
        if to_agent in perms.get("denyAgents", []):
            perms["denyAgents"].remove(to_agent)

        # 添加 allow
        if to_agent not in perms.get("allowAgents", []):
            perms.setdefault("allowAgents", []).append(to_agent)

            # 记录审计日志
            change = PermissionChange(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action="grant",
                from_agent=from_agent,
                to_agent=to_agent,
                reason=reason,
                operator=operator,
            )
            self._audit_log.append(change)
            self._save_audit_log()

            log.info(f"🔐 Granted: {from_agent} → {to_agent} ({reason or 'no reason'})")
            return True

        return False  # Already had permission

    def revoke(
        self,
        from_agent: str,
        to_agent: str,
        reason: str | None = None,
        operator: str | None = None,
    ) -> bool:
        """撤销 from_agent 调用 to_agent 的权限。

        Returns:
            True if permission was revoked, False if didn't have permission
        """
        self._ensure_loaded()

        if from_agent not in self._permissions:
            return False

        perms = self._permissions[from_agent]
        revoked = False

        # 从 allow 中移除
        if to_agent in perms.get("allowAgents", []):
            perms["allowAgents"].remove(to_agent)
            revoked = True

        # 添加到 deny（可选，用于显式禁止）
        if to_agent not in perms.get("denyAgents", []):
            perms.setdefault("denyAgents", []).append(to_agent)
            revoked = True

        if revoked:
            # 记录审计日志
            change = PermissionChange(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action="revoke",
                from_agent=from_agent,
                to_agent=to_agent,
                reason=reason,
                operator=operator,
            )
            self._audit_log.append(change)
            self._save_audit_log()

            log.info(f"🔒 Revoked: {from_agent} → {to_agent} ({reason or 'no reason'})")

        return revoked

    def get_audit_log(self, limit: int = 100) -> list[dict]:
        """获取审计日志。"""
        self._ensure_loaded()
        return [item.model_dump() for item in self._audit_log[-limit:]]


# ── 全局单例 ──
_service: AuthMatrixService | None = None


def get_auth_matrix_service() -> AuthMatrixService:
    """获取权限矩阵服务单例。"""
    global _service
    if _service is None:
        _service = AuthMatrixService()
    return _service
