"""
models.py — Pydantic models for fraud detection environment.
OpenEnv-compliant action and observation schemas.
"""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class Transaction(BaseModel):
    """A single financial transaction."""
    id: str
    user_id: str
    amount: float
    merchant: str
    merchant_category: str
    location: str
    country: str
    timestamp: str
    device_id: str
    is_international: bool
    velocity_1h: int
    velocity_24h: int


class UserProfile(BaseModel):
    """Historical profile of account holder."""
    user_id: str
    home_country: str
    home_city: str
    avg_monthly_spend: float
    typical_categories: List[str]
    account_age_days: int
    risk_score: float


class FraudAction(BaseModel):
    """Agent action: decision on current transaction."""
    decision: str = Field(
        ..., 
        description="One of: 'allow', 'flag', 'block'"
    )


class FraudObservation(BaseModel):
    """Complete observation returned to agent."""
    current_transaction: Transaction
    user_profile: UserProfile
    recent_history: List[Transaction]
    alerts: List[str]
    step_num: int
    total_steps: int
    decisions_so_far: Dict[str, str]
    task_name: str
    task_description: str
    episode_complete: bool = False
    final_score: Optional[float] = None
    final_summary: Optional[str] = None