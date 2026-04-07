"""
env_logic.py — Core environment logic for fraud detection.
Implements reset/step for OpenEnv API.
"""

import os
from uuid import uuid4
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from server.models import FraudAction, FraudObservation, Transaction, UserProfile
from server.tasks import TASK_REGISTRY
from server.graders import step_reward, episode_score


@dataclass
class State:
    """Episode state tracking."""
    episode_id: str
    step_count: int = 0


@dataclass
class StepResult:
    """Step result containing observation, reward, done flag."""
    observation: FraudObservation
    reward: float
    done: bool
    info: dict = field(default_factory=dict)


class FraudEnvironment:
    """Core fraud detection environment."""
    
    def __init__(self):
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._task_name: str = "single_fraud"
        self._transactions: list = []
        self._user_profiles: dict = {}
        self._ground_truth: dict = {}
        self._alerts_map: dict = {}
        self._decisions: dict = {}
        self._rewards: list = []
        self._step_idx: int = 0
    
    async def reset(self, options: Optional[dict] = None) -> FraudObservation:
        """
        Reset environment and return initial observation.
        
        Args:
            options: Dict with 'task' key specifying task name
        
        Returns:
            FraudObservation for first transaction
        """
        options = options or {}
        task_name = options.get("task", "single_fraud")
        
        if task_name not in TASK_REGISTRY:
            task_name = "single_fraud"
        
        task_meta = TASK_REGISTRY[task_name]
        
        # Load task
        (
            self._transactions,
            self._user_profiles,
            self._ground_truth,
            description_text,
        ) = task_meta["loader"]()
        
        # Reset state
        self._task_name = task_name
        self._decisions = {}
        self._rewards = []
        self._step_idx = 0
        self._state = State(episode_id=str(uuid4()), step_count=0)
        
        # Generate alerts
        self._generate_alerts()
        
        return self._build_observation()
    
    def _generate_alerts(self):
        """Generate anomaly alerts for all transactions."""
        self._alerts_map = {}
        
        for tx in self._transactions:
            alerts = []
            user_profile = self._user_profiles.get(tx.user_id)
            
            if not user_profile:
                continue
            
            # Alert: International transaction for domestic user
            if tx.is_international and user_profile.home_country != tx.country:
                alerts.append(f"⚠️ International transaction: {tx.location}, {tx.country}")
            
            # Alert: High transaction amount
            if tx.amount > user_profile.avg_monthly_spend * 0.2:
                alerts.append(f"💰 High amount: ${tx.amount:.2f}")
            
            # Alert: Unusual merchant category
            if tx.merchant_category not in user_profile.typical_categories:
                if tx.merchant_category in ["atm_withdrawal", "p2p", "crypto"]:
                    alerts.append(f"🔴 Unusual category: {tx.merchant_category}")
            
            # Alert: High velocity
            if tx.velocity_24h > 5:
                alerts.append(f"⚡ High velocity: {tx.velocity_24h} transactions in 24h")
            
            self._alerts_map[tx.id] = alerts
    
    async def step(self, action: FraudAction) -> StepResult:
        """
        Process agent decision and return reward + observation.
        
        Args:
            action: FraudAction with decision
        
        Returns:
            StepResult with observation, reward, done flag
        """
        self._state.step_count += 1
        
        current_tx = self._transactions[self._step_idx]
        tx_id = current_tx.id
        
        decision = action.decision.lower().strip()
        truth = self._ground_truth.get(tx_id, "legit")
        
        reward = step_reward(truth, decision)
        self._decisions[tx_id] = decision
        self._rewards.append(reward)
        self._step_idx += 1
        
        done = self._step_idx >= len(self._transactions)
        obs = self._build_observation(final=done)
        
        return StepResult(
            observation=obs,
            reward=reward,
            done=done,
            info={"step": self._state.step_count, "task": self._task_name}
        )
    
    def _build_observation(self, final: bool = False) -> FraudObservation:
        """Build observation for agent."""
        task_meta = TASK_REGISTRY[self._task_name]
        
        if final:
            score, summary = episode_score(self._decisions, self._ground_truth)
            current_tx = self._transactions[-1]
            
            return FraudObservation(
                current_transaction=current_tx,
                user_profile=self._user_profiles.get(current_tx.user_id),
                recent_history=self._get_recent_history(
                    current_tx.user_id, current_tx.id
                ),
                alerts=self._alerts_map.get(current_tx.id, []),
                step_num=len(self._transactions),
                total_steps=len(self._transactions),
                decisions_so_far=dict(self._decisions),
                task_name=self._task_name,
                task_description=task_meta["description"],
                episode_complete=True,
                final_score=round(score, 4),
                final_summary=summary,
            )
        
        current_tx = self._transactions[self._step_idx]
        current_user = current_tx.user_id
        
        return FraudObservation(
            current_transaction=current_tx,
            user_profile=self._user_profiles.get(current_user),
            recent_history=self._get_recent_history(current_user, current_tx.id),
            alerts=self._alerts_map.get(current_tx.id, []),
            step_num=self._step_idx + 1,
            total_steps=len(self._transactions),
            decisions_so_far=dict(self._decisions),
            task_name=self._task_name,
            task_description=task_meta["description"],
            episode_complete=False,
        )
    
    def _get_recent_history(self, user_id: str, exclude_id: str) -> list:
        """Return last 4 transactions by user (excluding current)."""
        history = [
            tx for tx in self._transactions
            if tx.user_id == user_id and tx.id != exclude_id
        ]
        return history[-4:]