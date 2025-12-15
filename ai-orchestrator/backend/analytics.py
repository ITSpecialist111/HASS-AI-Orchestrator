"""
Analytics Service for AI Orchestrator.
Aggregates decision logs and provides statistical insights.
"""
import os
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict, Counter

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stats", tags=["analytics"])

DECISION_DIR = Path("/data/decisions")

class AnalyticsService:
    """Service to aggregate and analyze agent decision logs"""
    
    def __init__(self, data_dir: Path = DECISION_DIR):
        self.data_dir = data_dir
        
    def _get_all_logs(self, days: int = 7) -> List[Dict]:
        """
        Get all decision logs from the last N days.
        Scans all agent subdirectories.
        """
        logs = []
        cutoff = datetime.now() - timedelta(days=days)
        
        if not self.data_dir.exists():
            return []
            
        # Walk through all directories (agents + orchestrator)
        for root, _, files in os.walk(self.data_dir):
            for file in files:
                if not file.endswith(".json"):
                    continue
                    
                path = Path(root) / file
                # Fast check on file modification time (avoid loading old files)
                mtime = datetime.fromtimestamp(path.stat().st_mtime)
                if mtime < cutoff:
                    continue
                    
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                        # Ensure timestamp exists and is recent
                        ts_str = data.get("timestamp")
                        if ts_str:
                            ts = datetime.fromisoformat(ts_str)
                            if ts >= cutoff:
                                logs.append(data)
                except Exception as e:
                    logger.warning(f"Failed to read log {path}: {e}")
                    
        return logs

    def get_daily_activity(self, days: int = 7) -> List[Dict]:
        """
        Get decision counts per day, broken down by agent.
        Returns: [ { date: "2023-01-01", heating: 5, cooling: 2, ... }, ... ]
        """
        logs = self._get_all_logs(days)
        
        # Structure: date -> agent -> count
        daily_counts = defaultdict(lambda: defaultdict(int))
        all_agents = set()
        
        for log in logs:
            ts = datetime.fromisoformat(log.get("timestamp"))
            date_str = ts.strftime("%Y-%m-%d")
            agent_id = log.get("agent_id", "unknown")
            
            daily_counts[date_str][agent_id] += 1
            all_agents.add(agent_id)
            
        # Format for Recharts (list of dicts)
        result = []
        # Sort dates
        start_date = datetime.now() - timedelta(days=days-1)
        for i in range(days):
            d = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
            entry = {"date": d}
            # Fill 0 for missing agents
            for agent in all_agents:
                entry[agent] = daily_counts[d][agent]
            result.append(entry)
            
        return result

    def get_agent_performance(self) -> Dict[str, Any]:
        """
        Calculates average execution metrics.
        Returns average decision counts and tool usage.
        """
        logs = self._get_all_logs(days=1) # Just last 24h for "current" performance
        
        agent_stats = defaultdict(lambda: {"count": 0, "errors": 0, "tools": Counter()})
        
        for log in logs:
            agent = log.get("agent_id", "unknown")
            agent_stats[agent]["count"] += 1
            
            # Check for errors in decision or execution
            # 'orchestrator' logs decisions differently than agents
            
            # Simple error check (if status is error or error field exists)
            if log.get("status") == "error" or "error" in log:
                agent_stats[agent]["errors"] += 1
                
            # Count tool usage
            # For logging: decision -> actions -> tool
            decision = log.get("decision", {})
            if isinstance(decision, dict):
                actions = decision.get("actions", [])
                for action in actions:
                    tool = action.get("tool")
                    if tool:
                        agent_stats[agent]["tools"][tool] += 1
                        
            # Backwards compatibility for MCP logs (direct tool execution)
            if "tool" in log:
                agent_stats[agent]["tools"][log["tool"]] += 1

        # Format
        result = {}
        for agent, stats in agent_stats.items():
            result[agent] = {
                "decisions_24h": stats["count"],
                "error_rate": round(stats["errors"] / stats["count"], 2) if stats["count"] > 0 else 0,
                "top_tool": stats["tools"].most_common(1)[0][0] if stats["tools"] else "none"
            }
            
        return result

    def get_approval_stats(self) -> Dict[str, int]:
        """
        Get stats on approvals (Manual check of DB would be better, but we can infer from logs if needed)
        For now, returns placeholder or connects to ApprovalQueue if passed.
        Using log directory scan for simplicity of this service class.
        """
        # TODO: Connect to SQLite for precise approval stats
        return {
            "pending": 0,
            "approved_24h": 0,
            "rejected_24h": 0
        }

# Initialize Service
analytics_service = AnalyticsService()

# API Routes
@router.get("/daily")
async def get_daily_stats():
    """Get daily activity charts"""
    return analytics_service.get_daily_activity()

@router.get("/performance")
async def get_performance_stats():
    """Get per-agent performance metrics"""
    return analytics_service.get_agent_performance()
