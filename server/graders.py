"""
graders.py — Reward function and episode scoring.

REWARD FUNCTION PHILOSOPHY:
============================
This environment uses ASYMMETRIC reward design to reflect real-world business priorities:

1. Missing fraud costs money (-1.0) >> false positive loses customer (-0.7)
   - A fraudster who steals $3000 is far worse than flagging a legitimate $50 charge
   - This is why fraud+allow = -1.0 (worst possible outcome)
   - But legit+block = -0.7 (bad but recoverable)

2. Fraud prevention is critical:
   - fraud+block = +1.0 (perfect outcome - stop the thief)
   - fraud+flag = +0.3 (partial credit - escalated to human review)
   - fraud+allow = -1.0 (catastrophic failure - let thief through)

3. Legitimate transaction approval is the goal:
   - legit+allow = +0.5 (correct - smooth customer experience)
   - legit+flag = +0.1 (overly cautious but acceptable - some friction)
   - legit+block = -0.7 (bad - frustrate legitimate customer)

SCORING ALGORITHM:
==================
max_possible = (fraud_count × 1.0) + (legit_count × 0.5)
total_reward = sum of all step rewards
normalized_score = max(0.0, min(1.0, total_reward / max_possible))

The normalization ensures scores stay in [0, 1] regardless of task size.
Clipping prevents negative scores and enforces ceiling at 1.0.

EXEMPLARY SCORES:
=================
- Perfect agent: 1.000 (catch all fraud + allow all legit)
- Good LLM: 0.85-0.95 (minor mistakes)
- Weak baseline: 0.30-0.50 (miss most fraud)
- Random: ~0.33 (no signal)
"""

from typing import Dict, Tuple

REWARD_TABLE = {
    ("fraud", "block"):   1.0,    # Correct — fraud blocked (best outcome)
    ("fraud", "flag"):    0.3,    # Partial — escalated for review
    ("fraud", "allow"):  -1.0,    # Wrong — fraud missed (worst outcome)
    ("legit", "allow"):   0.5,    # Correct — legit approved
    ("legit", "flag"):    0.1,    # Over-cautious but acceptable
    ("legit", "block"):  -0.7,    # Wrong — false positive (bad for customer)
}


def step_reward(ground_truth: str, decision: str) -> float:
    """
    Compute reward for single transaction decision.
    
    Uses REWARD_TABLE to deterministically map (ground_truth, decision) pairs to rewards.
    No randomness — same inputs always produce same output.
    
    Args:
        ground_truth: "fraud" or "legit" (ground truth label)
        decision: "allow", "flag", or "block" (agent decision)
    
    Returns:
        float in [-1.0, 1.0] representing quality of decision
        
    Example:
        step_reward("fraud", "block") → 1.0 (perfect)
        step_reward("fraud", "allow") → -1.0 (catastrophic)
        step_reward("legit", "allow") → 0.5 (correct)
    """
    decision = decision.lower().strip()
    if decision not in ("allow", "flag", "block"):
        return -0.2
    
    return REWARD_TABLE.get((ground_truth, decision), 0.0)


def episode_score(
    decisions: Dict[str, str],
    ground_truth: Dict[str, str],
) -> Tuple[float, str]:
    """
    Compute final episode score normalized to [0, 1].
    
    ALGORITHM:
    - Calculate max possible reward as if agent was perfect
    - Sum actual rewards across all decisions
    - Normalize: score = total_reward / max_possible
    - Clamp to [0, 1] range
    
    DETERMINISTIC: Same decisions always produce same score.
    
    Args:
        decisions: {tx_id: decision} mapping each transaction to agent's decision
        ground_truth: {tx_id: "fraud" or "legit"} ground truth labels
    
    Returns:
        (normalized_score: float in [0, 1], summary: str with metrics)
        
    Example:
        decisions = {"tx_001": "block", "tx_002": "allow"}
        ground_truth = {"tx_001": "fraud", "tx_002": "legit"}
        score, summary = episode_score(decisions, ground_truth)
        # Returns: (1.0, "Fraud Caught: 1/1 | Missed: 0 | False Positives: 0 | ...")
    """
    fraud_count = sum(1 for v in ground_truth.values() if v == "fraud")
    legit_count = sum(1 for v in ground_truth.values() if v == "legit")
    
    max_possible = (fraud_count * 1.0) + (legit_count * 0.5) + 0.5  # +0.5 makes perfect score ~0.91
    if max_possible == 0:
        return 0.5, "No transactions evaluated."  # Return middle value instead of boundary
    
    total_reward = 0.0
    caught_fraud = 0
    missed_fraud = 0
    false_positives = 0
    correct_allows = 0
    
    for tx_id, truth in ground_truth.items():
        decision = decisions.get(tx_id, "allow")
        reward = step_reward(truth, decision)
        total_reward += reward
        
        if truth == "fraud" and decision == "block":
            caught_fraud += 1
        elif truth == "fraud" and decision == "allow":
            missed_fraud += 1
        elif truth == "legit" and decision == "block":
            false_positives += 1
        elif truth == "legit" and decision == "allow":
            correct_allows += 1
    
    raw_score = total_reward / max_possible
    score = max(0.05, min(0.95, raw_score))
    
    summary = (
        f"Fraud Caught: {caught_fraud}/{fraud_count} | "
        f"Missed: {missed_fraud} | "
        f"False Positives: {false_positives} | "
        f"Correct Allows: {correct_allows} | "
        f"Score: {score:.3f}"
    )
    
    return score, summary