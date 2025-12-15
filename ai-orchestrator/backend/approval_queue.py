"""
Approval Queue for Human-in-the-Loop decision making.
Manages high-impact actions requiring manual approval.
"""
import asyncio
import logging
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Literal
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)


class ApprovalRequest:
    """Represents a single approval request"""
    
    def __init__(
        self,
        agent_id: str,
        action_type: str,
        action_data: Dict,
        impact_level: Literal["low", "medium", "high", "critical"],
        reason: str,
        timeout_seconds: int = 300
    ):
        self.id = str(uuid.uuid4())
        self.timestamp = datetime.now()
        self.agent_id = agent_id
        self.action_type = action_type
        self.action_data = action_data
        self.impact_level = impact_level
        self.reason = reason
        self.timeout_seconds = timeout_seconds
        self.status: Literal["pending", "approved", "rejected", "expired"] = "pending"
        self.approved_by: Optional[str] = None
        self.approved_at: Optional[datetime] = None


class ApprovalQueue:
    """
    Manages approval queue with SQLite persistence.
    Handles auto-approval rules, timeouts, and manual approvals.
    """
    
    def __init__(self, db_path: str = "/data/approvals.db", timeout_default: int = 300):
        """
        Initialize approval queue.
        
        Args:
            db_path: Path to SQLite database
            timeout_default: Default timeout in seconds (5 minutes)
        """
        self.db_path = db_path
        self.timeout_default = timeout_default
        self._init_database()
        
        # Auto-approval rules
        self.auto_approval_rules = self._load_auto_approval_rules()
        
        # Callbacks for dashboard notifications
        self.approval_callbacks: List = []
        
        logger.info(f"ApprovalQueue initialized: {db_path}")
    
    def _init_database(self):
        """Initialize SQLite database schema"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS approvals (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                action_data TEXT NOT NULL,
                impact_level TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL,
                approved_by TEXT,
                approved_at TEXT,
                timeout_seconds INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Index for active requests
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_status 
            ON approvals(status, timestamp)
        """)
        
        conn.commit()
        conn.close()
    
    def _load_auto_approval_rules(self) -> Dict:
        """Load rules for automatic approval"""
        return {
            # HVAC rules
            "heating": {
                "max_change_celsius": 2.0,  # Auto-approve if <2°C change
                "allowed_modes": ["heat", "auto"],
                "requires_approval": ["off"]  # Turning off requires approval
            },
            "cooling": {
                "max_change_celsius": 2.0,
                "allowed_modes": ["cool", "auto"],
                "requires_approval": ["off"]
            },
            
            # Lighting rules (all auto-approve)
            "lighting": {
                "all_auto": True
            },
            
            # Security rules (most require approval)
            "security": {
                "auto_approve": ["armed_home_to_armed_away"],
                "requires_approval": [
                    "disarm",
                    "unlock_door",
                    "disable_camera"
                ]
            }
        }
    
    async def add_request(
        self,
        agent_id: str,
        action_type: str,
        action_data: Dict,
        impact_level: Literal["low", "medium", "high", "critical"],
        reason: str,
        timeout_seconds: Optional[int] = None
    ) -> ApprovalRequest:
        """
        Add new approval request.
        
        Returns:
            ApprovalRequest object (may be auto-approved)
        """
        timeout = timeout_seconds or self.timeout_default
        
        request = ApprovalRequest(
            agent_id=agent_id,
            action_type=action_type,
            action_data=action_data,
            impact_level=impact_level,
            reason=reason,
            timeout_seconds=timeout
        )
        
        # Check auto-approval rules
        if self._should_auto_approve(request):
            request.status = "approved"
            request.approved_by = "system"
            request.approved_at = datetime.now()
            logger.info(f"Auto-approved request {request.id}: {action_type}")
        else:
            logger.info(f"Queued for approval {request.id}: {action_type} (impact: {impact_level})")
            
            # Notify dashboard
            await self._notify_approval_required(request)
            
            # Start timeout timer
            asyncio.create_task(self._handle_timeout(request))
        
        # Save to database
        self._save_request(request)
        
        return request
    
    def _should_auto_approve(self, request: ApprovalRequest) -> bool:
        """Check if request matches auto-approval rules"""
        agent_rules = self.auto_approval_rules.get(request.agent_id, {})
        
        # Lighting: auto-approve everything
        if request.agent_id == "lighting":
            return agent_rules.get("all_auto", False)
        
        # HVAC: check temperature change
        if request.agent_id in ["heating", "cooling"]:
            if "temperature" in request.action_data:
                change = abs(request.action_data.get("temperature_change", 0))
                max_change = agent_rules.get("max_change_celsius", 2.0)
                if change <= max_change:
                    return True
        
        # Security: check action type
        if request.agent_id == "security":
            auto_approve = agent_rules.get("auto_approve", [])
            if request.action_type in auto_approve:
                return True
        
        # High/critical impact always requires approval
        if request.impact_level in ["high", "critical"]:
            return False
        
        # Default for low/medium if not matched above
        return request.impact_level == "low"
    
    async def approve(self, request_id: str, approved_by: str = "user") -> bool:
        """Approve a pending request"""
        request = self.get_request(request_id)
        if not request or request.status != "pending":
            return False
        
        request.status = "approved"
        request.approved_by = approved_by
        request.approved_at = datetime.now()
        
        self._update_request(request)
        logger.info(f"Request {request_id} approved by {approved_by}")
        
        return True
    
    async def reject(self, request_id: str, rejected_by: str = "user") -> bool:
        """Reject a pending request"""
        request = self.get_request(request_id)
        if not request or request.status != "pending":
            return False
        
        request.status = "rejected"
        request.approved_by = rejected_by
        request.approved_at = datetime.now()
        
        self._update_request(request)
        logger.info(f"Request {request_id} rejected by {rejected_by}")
        
        return True
    
    def get_pending(self) -> List[ApprovalRequest]:
        """Get all pending approval requests"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM approvals 
            WHERE status = 'pending' 
            ORDER BY timestamp DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_request(row) for row in rows]
    
    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get specific approval request"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM approvals WHERE id = ?", (request_id,))
        row = cursor.fetchone()
        conn.close()
        
        return self._row_to_request(row) if row else None
    
    async def _handle_timeout(self, request: ApprovalRequest):
        """Handle request timeout - auto-reject after timeout period"""
        await asyncio.sleep(request.timeout_seconds)
        
        # Check if still pending
        current = self.get_request(request.id)
        if current and current.status == "pending":
            current.status = "expired"
            self._update_request(current)
            logger.warning(f"Request {request.id} expired after {request.timeout_seconds}s")
    
    async def _notify_approval_required(self, request: ApprovalRequest):
        """Notify dashboard of new approval request"""
        # Call registered callbacks (dashboard WebSocket broadcast)
        for callback in self.approval_callbacks:
            try:
                await callback({
                    "type": "approval_required",
                    "request_id": request.id,
                    "agent_id": request.agent_id,
                    "action_type": request.action_type,
                    "impact_level": request.impact_level,
                    "reason": request.reason,
                    "timeout_seconds": request.timeout_seconds
                })
            except Exception as e:
                logger.error(f"Error in approval callback: {e}")
    
    def register_callback(self, callback):
        """Register callback for approval notifications"""
        self.approval_callbacks.append(callback)
    
    def _save_request(self, request: ApprovalRequest):
        """Save request to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO approvals 
            (id, timestamp, agent_id, action_type, action_data, impact_level, 
             reason, status, approved_by, approved_at, timeout_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request.id,
            request.timestamp.isoformat(),
            request.agent_id,
            request.action_type,
            json.dumps(request.action_data),
            request.impact_level,
            request.reason,
            request.status,
            request.approved_by,
            request.approved_at.isoformat() if request.approved_at else None,
            request.timeout_seconds
        ))
        
        conn.commit()
        conn.close()
    
    def _update_request(self, request: ApprovalRequest):
        """Update existing request"""
        self._save_request(request)  # INSERT OR REPLACE handles updates
    
    def _row_to_request(self, row) -> ApprovalRequest:
        """Convert database row to ApprovalRequest"""
        request = ApprovalRequest(
            agent_id=row[2],
            action_type=row[3],
            action_data=json.loads(row[4]),
            impact_level=row[5],
            reason=row[6],
            timeout_seconds=row[10]
        )
        request.id = row[0]
        request.timestamp = datetime.fromisoformat(row[1])
        request.status = row[7]
        request.approved_by = row[8]
        request.approved_at = datetime.fromisoformat(row[9]) if row[9] else None
        
        return request
