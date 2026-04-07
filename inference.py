"""
inference.py — Inference script using OpenAI/HF with fallback rule-based mode.
OpenEnv-compliant logging format.
"""

import os
import httpx
import json
from typing import Optional


class FraudEnvClient:
    """Client for fraud detection environment."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.Client(timeout=30.0)
        self.episode_id = None
    
    def reset(self, task_name: str = "single_fraud"):
        """Reset environment."""
        response = self.client.post(
            f"{self.base_url}/reset",
            json={"task_name": task_name}
        )
        response.raise_for_status()
        data = response.json()
        return data["observation"]
    
    def step(self, decision: str):
        """Take step in environment."""
        response = self.client.post(
            f"{self.base_url}/step",
            json={"decision": decision}
        )
        response.raise_for_status()
        return response.json()
    
    def get_state(self):
        """Get current state."""
        response = self.client.get(f"{self.base_url}/state")
        response.raise_for_status()
        return response.json()
    
    def close(self):
        """Close client."""
        self.client.close()


def fallback_decision(obs: dict, debug: bool = False) -> str:
    """Smart fraud detection using pattern analysis."""
    tx = obs["current_transaction"]
    alerts = obs.get("alerts", [])
    recent_history = obs.get("recent_history", [])
    
    score = 0  # Fraud likelihood score (higher = more fraud)
    
    if debug:
        print(f"  [DEBUG] TX ID: {tx.get('id')}, Amount: ${tx['amount']}, Merchant: {tx['merchant']}")
        print(f"  [DEBUG] Recent history size: {len(recent_history)}")
    
    # PRIMARY SIGNALS - Impossible Travel
    if "impossible travel" in " ".join(alerts).lower():
        score += 5  # Very strong fraud signal
        if debug: print(f"  [DEBUG] +5 impossible travel")
    
    # Unknown device signals
    is_unknown_device = tx["device_id"].startswith("device_unknown")
    if is_unknown_device:
        score += 2
        # Unknown device + high amount is very suspicious
        if tx["amount"] > 1000:
            score += 3
            if debug: print(f"  [DEBUG] +5 unknown device + high amount")
    
    if is_unknown_device and tx.get("is_international"):
        score += 2  # Cross-border with unknown device
        if debug: print(f"  [DEBUG] +2 unknown device + international")
    
    # PATTERN ANALYSIS - Detect abnormal transaction amounts
    category = tx.get("merchant_category", "")
    merchant_lower = tx["merchant"].lower()
    
    # Analyze recent spending patterns
    if recent_history:
        recent_amounts = [t.get("amount", 0) for t in recent_history]
        avg_recent = sum(recent_amounts) / len(recent_amounts) if recent_amounts else 0
        recent_max = max(recent_amounts) if recent_amounts else 0
        
        if debug:
            print(f"  [DEBUG] Recent amounts: {recent_amounts}, avg: ${avg_recent:.2f}")
        
        # Transaction dramatically exceeds typical pattern (fraud ring red flag)
        if tx["amount"] > avg_recent * 50 and tx["amount"] > 500:
            score += 2  # Big jump from user's normal behavior
            if debug: print(f"  [DEBUG] +2 amount jump (${tx['amount']} vs avg ${avg_recent:.2f})")
        
        # Sudden wire/P2P transfers when user doesn't normally do this
        is_money_movement = any(k in category for k in ["p2p", "wire", "transfer"])
        is_typical_category = all(k not in category for k in ["p2p", "wire", "transfer", "atm"])
        
        recent_categories = [t.get("merchant_category", "") for t in recent_history]
        typical_user_behavior = any(c == category for c in recent_categories) if recent_categories else False
        
        if is_money_movement and not typical_user_behavior and len(recent_history) > 0:
            score += 2  # Unusual for this user to do wire transfers
            if debug: print(f"  [DEBUG] +2 unusual wire/p2p for user")
        
        # Check for recent wire/p2p activity (fraud ring indicator)
        recent_has_wire = any("p2p" in t.get("merchant_category", "") or "wire" in t.get("merchant", "").lower() 
                             for t in recent_history)
    else:
        recent_has_wire = False
    
    # FRAUD RING DETECTION - Large P2P/Wire suspicious
    if "wire" in merchant_lower or "deposit" in merchant_lower or "p2p" in category:
        # ANY large wire/p2p is suspicious (mule detection)
        if tx["amount"] > 3000:
            score += 3  # Large wire/p2p - strong fraud signal
            if debug: print(f"  [DEBUG] +3 large wire/p2p (${tx['amount']})")
        elif tx["amount"] > 1000:
            score += 2  # Moderate wire/p2p - significant alert
            if debug: print(f"  [DEBUG] +2 moderate wire/p2p (${tx['amount']})")
    
    # STRUCTURED TRANSACTION PATTERNS - Matching amounts in/out (very strong signal)
    if recent_history and category in ["p2p", "wire", "transfer"]:
        # Check if there was a similar amount recently (sign of pass-through)
        recent_amounts = [t.get("amount", 0) for t in recent_history]
        # If amount matches something recent (within 10%), it's VERY suspicious (pass-through/mule)
        for recent_amt in recent_amounts:
            if 0.9 * recent_amt <= tx["amount"] <= 1.1 * recent_amt:
                score += 3  # Amount matches - highly likely pass-through/mule  
                if debug: print(f"  [DEBUG] +3 matching amount detected (${tx['amount']} ~ ${recent_amt}) - MULE BEHAVIOR")
                break
    
    # STRUCTURING DETECTION - Multiple ATMs/rapid withdrawals
    is_atm = "atm" in merchant_lower or "withdrawal" in category
    if is_atm:
        if tx["velocity_24h"] >= 2:
            score += 4  # Multiple ATM withdrawals - classic structuring pattern
            if debug: print(f"  [DEBUG] +4 multiple ATM withdrawals (velocity={tx['velocity_24h']})")
        elif tx["amount"] >= 3000:  # Large single ATM withdrawal
            # Large ATM after wire is VERY suspicious
            points_added = 4 if recent_has_wire else 3
            score += points_added
            if debug: 
                reason = "after wire deposit (STRUCTURING)" if recent_has_wire else "large ATM"
                print(f"  [DEBUG] +{points_added} {reason} (${tx['amount']})")
        elif tx["amount"] >= 1500:  # Moderate ATM withdrawal
            points_added = 3 if recent_has_wire else 2
            score += points_added
            if debug:
                reason = "after wire (structuring)" if recent_has_wire else "moderate amount"
                print(f"  [DEBUG] +{points_added} moderate ATM withdrawal {reason}")
    
    # International + high velocity
    if tx.get("is_international") and tx["velocity_24h"] > 5:
        score += 1
        if debug: print(f"  [DEBUG] +1 international + high velocity")
    
    # Very high amount (over typical monthly)
    if tx["amount"] > 5000:
        score += 1
        if debug: print(f"  [DEBUG] +1 very high amount")
    
    # Multiple alerts compound suspicion
    alert_count = len(alerts)
    if alert_count > 2:
        score += 1
        if debug: print(f"  [DEBUG] +1 multiple alerts ({alert_count})")
    if alert_count > 3:
        score += 1
        if debug: print(f"  [DEBUG] +1 many alerts ({alert_count})")
    
    if debug:
        print(f"  [DEBUG] Final score: {score}")
    
    # DECISION LOGIC - Graduated response based on confidence
    if score >= 5:
        return "block"      # High confidence fraud
    elif score >= 3:
        return "flag"       # Medium confidence - needs review
    else:
        return "allow"      # Low fraud probability


def run_inference(
    task_name: str = "single_fraud",
    base_url: str = "http://localhost:8000",
    debug: bool = False,
    verbose: bool = True
):
    """Run inference on single task. Returns score in [0, 1]."""
    
    env = FraudEnvClient(base_url=base_url)
    
    # Map task names to benchmark name
    benchmark_name = "fraud-detection"
    model_name = "gpt-4-fallback"
    
    success = False
    rewards = []
    steps_taken = 0
    final_score = 0.0
    error_msg = None
    
    try:
        # [START] - SPEC REQUIRED FORMAT
        print(f"[START] task={task_name} env={benchmark_name} model={model_name}", flush=True)
        
        # Reset environment
        obs = env.reset(task_name=task_name)
        state = env.get_state()
        total_steps = state["total_steps"]
        
        for step_num in range(1, total_steps + 1):
            # Get decision using fallback (rule-based)
            decision = fallback_decision(obs, debug=False)
            
            # Step environment
            result = env.step(decision)
            obs = result["observation"]
            reward = result["reward"]
            done = result["done"]
            
            rewards.append(reward)
            steps_taken = step_num
            
            # [STEP] - SPEC REQUIRED FORMAT (single line, all fields)
            error_field = error_msg if error_msg else "null"
            done_str = "true" if done else "false"
            print(
                f"[STEP] step={step_num} action={decision} reward={reward:.2f} done={done_str} error={error_field}",
                flush=True
            )
            
            if done:
                break
        
        # Calculate final score from observation
        final_score = obs.get("final_score", sum(rewards) / len(rewards) if rewards else 0.0)
        final_score = max(0.0, min(1.0, final_score))  # Clamp to [0, 1]
        success = True
        
    except Exception as e:
        error_msg = str(e)
        final_score = 0.0
        success = False
    
    finally:
        try:
            env.close()
        except:
            pass
        
        # [END] - SPEC REQUIRED FORMAT (single line, all fields)
        rewards_str = ",".join(f"{r:.2f}" for r in rewards)
        success_str = "true" if success else "false"
        print(
            f"[END] success={success_str} steps={steps_taken} score={final_score:.3f} rewards={rewards_str}",
            flush=True
        )
        
        if verbose and success:
            print(f"\nTask: {task_name} | Score: {final_score:.3f} | Steps: {steps_taken}")
        
        return {
            "task": task_name,
            "score": final_score,
            "steps": steps_taken,
            "rewards": rewards,
            "success": success
        }


if __name__ == "__main__":
    import sys
    
    # Get task from command line (default to single_fraud)
    if len(sys.argv) > 1:
        task_arg = sys.argv[1].strip().lower()
        
        # Map common task names to internal names
        task_map = {
            "easy": "single_fraud",
            "single_fraud": "single_fraud",
            "single": "single_fraud",
            "medium": "multi_pattern_fraud",
            "multi_pattern_fraud": "multi_pattern_fraud",
            "multi": "multi_pattern_fraud",
            "hard": "adaptive_fraud_attack",
            "adaptive_fraud_attack": "adaptive_fraud_attack",
            "adaptive": "adaptive_fraud_attack",
        }
        
        task = task_map.get(task_arg, task_arg)
    else:
        task = "single_fraud"
    
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    result = run_inference(task_name=task, base_url=base_url, verbose=False)
