"""
Advanced Fraud Detection Policy for HARD Task
==============================================
Combines multiple weak signals into a risk score with adaptive thresholds.
Designed for masked fraud detection (behavioral anomalies).

Key Improvements Over Baseline:
- Behavioral profiling (deviation from user's normal patterns)
- Contextual velocity analysis (not just total velocity)
- Device trust scoring (known vs unknown vs suspicious)
- Sequence pattern detection (transaction flows)
- Adaptive risk thresholds
- Confidence-based decisions
"""

from typing import Dict, List, Tuple, Optional
import statistics


class FraudDetector:
    """Advanced fraud detection with adaptive risk scoring."""
    
    def __init__(self):
        """Initialize with tunable parameters."""
        # Risk score thresholds (adjust during episode based on performance)
        self.BLOCK_THRESHOLD = 6.0      # High confidence fraud
        self.FLAG_THRESHOLD = 3.5       # Medium confidence fraud
        
        # Signal weights (importance multipliers)
        self.WEIGHTS = {
            'impossible_travel': 3.0,      # Strongest signal
            'device_anomaly': 2.5,         # Very strong
            'behavioral_deviance': 2.0,    # Strong
            'velocity_spike': 1.8,         # Strong
            'amount_jump': 1.5,            # Moderate
            'category_switch': 1.2,        # Weak-moderate
            'location_anomaly': 1.3,       # Weak-moderate
            'sequence_pattern': 1.6,       # Moderate
        }
        
        # Episode tracking for adaptive thresholds
        self.episode_rewards = []
        self.step_count = 0
        self.false_positive_ratio = 0.0
    
    def score_impossible_travel(self, obs: Dict) -> Tuple[float, str]:
        """
        Detect if transaction violates physics (too fast travel).
        
        Fraud rings often exploit impossible travel to move money quickly.
        Score: 0-3.0
        """
        tx = obs['current_transaction']
        recent_history = obs.get('recent_history', [])
        
        if not recent_history:
            return 0.0, "No history available"
        
        # Get last transaction location and time
        last_tx = recent_history[-1]
        last_location = last_tx.get('location', '')
        current_location = tx.get('location', '')
        
        # If locations are same, no impossible travel
        if last_location == current_location:
            return 0.0, "Same location"
        
        # Check time difference (hours) - simplified
        # In real scenario, would calculate actual time delta
        time_between_hours = 2  # Assume 2 hours between transactions
        distance_miles = 5000  # Assume ~5000 miles between different countries
        
        # Minimum travel speed required: ~2500 mph (impossible for commercial flight)
        required_speed = distance_miles / time_between_hours if time_between_hours > 0 else float('inf')
        
        if required_speed > 900:  # Commercial flights ~900 mph max
            return 3.0, f"Impossible: {required_speed:.0f} mph required"
        
        return 0.0, "Feasible travel"
    
    def score_device_anomaly(self, obs: Dict) -> Tuple[float, str]:
        """
        Detect unknown or suspicious devices.
        
        Fraud often uses new devices. But high false positive risk.
        Score: 0-2.5
        """
        tx = obs['current_transaction']
        device_id = tx.get('device_id', '')
        recent_history = obs.get('recent_history', [])
        user_profile = obs.get('user_profile', {})
        
        # Unknown device flag
        is_unknown = device_id.startswith('device_unknown')
        
        if is_unknown:
            # Base score for unknown device
            score = 1.5
            
            # Aggravate if combined with other factors
            if tx.get('is_international'):
                score += 0.5
            
            # Aggravate if amount is high
            if tx.get('amount', 0) > user_profile.get('avg_monthly_spend', 2500) * 0.5:
                score += 0.5
            
            return min(score, 2.5), f"Unknown device: {device_id}"
        
        # Check if device matches user's known devices
        known_devices = [f"device_{i}" for i in range(1, 10)]  # Simplified
        if device_id not in known_devices:
            return 1.0, f"Unexpected device: {device_id}"
        
        return 0.0, "Known device"
    
    def score_behavioral_deviance(self, obs: Dict) -> Tuple[float, str]:
        """
        Compare current transaction against user's profile.
        
        Masked fraud often mimics legitimate patterns but with deviations.
        Score: 0-2.0
        """
        tx = obs['current_transaction']
        user_profile = obs.get('user_profile', {})
        recent_history = obs.get('recent_history', [])
        
        if not user_profile:
            return 0.0, "No profile available"
        
        score = 0.0
        reasons = []
        
        # 1. Amount deviation
        avg_spend = user_profile.get('avg_monthly_spend', 2500)
        typical_tx_amount = avg_spend / 30  # ~83 per day avg
        
        tx_amount = tx.get('amount', 0)
        if tx_amount > typical_tx_amount * 5:  # 5x user's typical
            deviation = (tx_amount / typical_tx_amount - 1) * 100
            amount_score = min(1.0, (tx_amount / typical_tx_amount) / 10)  # Cap at 1.0
            score += amount_score
            reasons.append(f"Amount {deviation:.0f}% above typical")
        
        # 2. Category deviation
        typical_categories = user_profile.get('typical_categories', [])
        current_category = tx.get('merchant_category', '')
        
        risky_categories = ['atm_withdrawal', 'p2p', 'wire', 'cryptocurrency']
        
        if current_category in risky_categories and current_category not in typical_categories:
            score += 0.7
            reasons.append(f"Unusual category: {current_category}")
        
        # 3. Location deviation
        home_country = user_profile.get('home_country', 'US')
        is_international = tx.get('is_international', False)
        
        if is_international and user_profile.get('account_age_days', 1000) < 180:
            # New account going international = risky
            score += 0.3
            reasons.append("New account + international")
        
        return min(score, 2.0), ", ".join(reasons) if reasons else "Normal behavior"
    
    def score_velocity_anomaly(self, obs: Dict) -> Tuple[float, str]:
        """
        Detect transaction frequency/velocity spikes.
        
        Fraud rings move money quickly. But legitimate users travel too.
        Score: 0-1.8
        """
        tx = obs['current_transaction']
        
        velocity_1h = tx.get('velocity_1h', 0)
        velocity_24h = tx.get('velocity_24h', 0)
        
        score = 0.0
        reasons = []
        
        # Spike in 1 hour
        if velocity_1h >= 3:
            score += 0.8
            reasons.append(f"3+ txns in 1hr")
        elif velocity_1h >= 2:
            score += 0.4
            reasons.append(f"2 txns in 1hr")
        
        # Spike in 24 hours relative to velocity_1h
        if velocity_24h >= 5 and velocity_1h == 0:
            # Many small transactions spread over day (structuring)
            score += 0.6
            reasons.append("Structuring pattern (many small txns)")
        elif velocity_24h >= 10:
            # Extremely high activity
            score += 0.4
            reasons.append(f"10+ txns in 24hrs")
        
        return min(score, 1.8), ", ".join(reasons) if reasons else "Normal velocity"
    
    def score_amount_jump(self, obs: Dict) -> Tuple[float, str]:
        """
        Detect sudden increases in transaction amounts.
        
        Score: 0-1.5
        """
        tx = obs['current_transaction']
        recent_history = obs.get('recent_history', [])
        
        if len(recent_history) < 2:
            return 0.0, "Insufficient history"
        
        # Get average of last few transactions
        recent_amounts = [t.get('amount', 0) for t in recent_history[-3:]]
        avg_recent = statistics.mean(recent_amounts) if recent_amounts else 100
        
        current_amount = tx.get('amount', 0)
        
        if avg_recent == 0:
            return 0.0, "No baseline"
        
        # Jump ratio
        jump_ratio = current_amount / avg_recent
        
        if jump_ratio > 10:  # 10x jump
            return 1.5, f"10x amount jump"
        elif jump_ratio > 5:  # 5x jump
            return 1.0, f"5x amount jump"
        elif jump_ratio > 2:  # 2x jump
            return 0.5, f"2x amount jump"
        
        return 0.0, "Normal amount progression"
    
    def score_category_switch(self, obs: Dict) -> Tuple[float, str]:
        """
        Detect unusual category changes (e.g., always groceries → suddenly wire transfer).
        
        Score: 0-1.2
        """
        tx = obs['current_transaction']
        recent_history = obs.get('recent_history', [])
        
        if not recent_history:
            return 0.0, "No history"
        
        current_category = tx.get('merchant_category', '')
        recent_categories = [t.get('merchant_category', '') for t in recent_history[-3:]]
        
        # Check for sudden category switch
        if recent_categories:
            dominant_category = max(set(recent_categories), key=recent_categories.count)
            
            if current_category != dominant_category:
                # Switching away from typical category
                switch_score = 0.8
                
                # Some switches are legitimate
                if current_category in ['groceries', 'dining', 'shopping']:
                    switch_score = 0.3  # Common categories, lower risk
                
                return switch_score, f"Switch: {dominant_category} → {current_category}"
        
        return 0.0, "Consistent category"
    
    def score_location_anomaly(self, obs: Dict) -> Tuple[float, str]:
        """
        Detect unusual location patterns.
        
        Score: 0-1.3
        """
        tx = obs['current_transaction']
        user_profile = obs.get('user_profile', {})
        
        home_city = user_profile.get('home_city', '')
        current_location = tx.get('location', '')
        
        if current_location != home_city:
            # Not in home location
            if tx.get('is_international'):
                return 1.3, f"International: {current_location}"
            else:
                return 0.5, f"Away from home: {current_location}"
        
        return 0.0, "Home location"
    
    def score_sequence_pattern(self, obs: Dict) -> Tuple[float, str]:
        """
        Detect suspicious transaction flows (e.g., wire in → wire out, ATM after transfer).
        
        Fraud rings often create recognizable patterns.
        Score: 0-1.6
        """
        tx = obs['current_transaction']
        recent_history = obs.get('recent_history', [])
        
        if len(recent_history) < 2:
            return 0.0, "Insufficient history"
        
        current_category = tx.get('merchant_category', '')
        prev_category = recent_history[-1].get('merchant_category', '') if recent_history else ''
        
        score = 0.0
        patterns = []
        
        # Pattern 1: Wire/P2P followed by ATM (moving stolen money)
        if prev_category in ['wire', 'p2p'] and current_category == 'atm_withdrawal':
            score += 1.0
            patterns.append("Wire→ATM (cash conversion)")
        
        # Pattern 2: Multiple wire/p2p in sequence (fraud ring)
        wire_p2p_count = sum(1 for t in recent_history[-3:] 
                            if t.get('merchant_category', '') in ['wire', 'p2p'])
        if wire_p2p_count >= 2 and current_category in ['wire', 'p2p']:
            score += 0.8
            patterns.append("Multiple wire/P2P sequence")
        
        # Pattern 3: ATM withdrawal after high amount (structuring)
        if prev_category == 'atm_withdrawal' and current_category == 'atm_withdrawal':
            if recent_history and recent_history[-1].get('amount', 0) > 2000:
                score += 0.6
                patterns.append("ATM structuring")
        
        return min(score, 1.6), ", ".join(patterns) if patterns else "Normal flow"
    
    def calculate_risk_score(self, obs: Dict) -> Tuple[float, Dict]:
        """
        Calculate total risk score by combining all signals with weights.
        
        Returns:
            (risk_score: float, details: dict with breakdown)
        """
        details = {}
        total_score = 0.0
        
        # Score each signal
        signal_scores = {
            'impossible_travel': self.score_impossible_travel(obs),
            'device_anomaly': self.score_device_anomaly(obs),
            'behavioral_deviance': self.score_behavioral_deviance(obs),
            'velocity_spike': self.score_velocity_anomaly(obs),
            'amount_jump': self.score_amount_jump(obs),
            'category_switch': self.score_category_switch(obs),
            'location_anomaly': self.score_location_anomaly(obs),
            'sequence_pattern': self.score_sequence_pattern(obs),
        }
        
        # Combine with weights
        for signal_name, (score, reason) in signal_scores.items():
            weight = self.WEIGHTS.get(signal_name, 1.0)
            weighted_score = score * weight
            total_score += weighted_score
            
            details[signal_name] = {
                'raw_score': score,
                'weight': weight,
                'weighted_score': weighted_score,
                'reason': reason,
            }
        
        return total_score, details
    
    def decide_action(self, obs: Dict, debug: bool = False) -> str:
        """
        Main decision function: Convert risk score to action.
        
        Args:
            obs: Observation dict from environment
            debug: Print reasoning if True
        
        Returns:
            'allow', 'flag', or 'block'
        """
        risk_score, details = self.calculate_risk_score(obs)
        
        if debug:
            print(f"\n[FRAUD DETECTOR] Risk Score: {risk_score:.2f}")
            for signal, info in details.items():
                if info['raw_score'] > 0:
                    print(f"  {signal}: {info['raw_score']:.2f} × {info['weight']:.1f}w = {info['weighted_score']:.2f} ({info['reason']})")
        
        # Decision logic with adaptive thresholds
        # Adapt thresholds based on false positive rate
        block_threshold = self.BLOCK_THRESHOLD
        flag_threshold = self.FLAG_THRESHOLD
        
        # If we're making too many false positives, raise thresholds
        if self.false_positive_ratio > 0.3:
            block_threshold *= 1.1  # 10% higher
            flag_threshold *= 1.1
        
        # Decision
        if risk_score >= block_threshold:
            action = 'block'
        elif risk_score >= flag_threshold:
            action = 'flag'
        else:
            action = 'allow'
        
        if debug:
            print(f"  Decision: {action.upper()} (thresholds: block≥{block_threshold:.1f}, flag≥{flag_threshold:.1f})")
        
        return action
    
    def update_performance(self, reward: float, action: str, ground_truth: Optional[str] = None):
        """
        Update performance metrics for adaptive threshold tuning.
        
        In real scenario, you'd track false positives vs true positives.
        """
        self.episode_rewards.append(reward)
        self.step_count += 1
        
        # Adaptive tuning example (simplified)
        if len(self.episode_rewards) >= 10:
            avg_reward = statistics.mean(self.episode_rewards[-10:])
            
            # If avg reward dropping, we're making bad decisions
            if avg_reward < 0.0:
                # Gradually lower thresholds (more conservative)
                self.FLAG_THRESHOLD *= 0.95
                self.BLOCK_THRESHOLD *= 0.95
            elif avg_reward > 0.5:
                # We're doing well, can afford to be slightly more aggressive
                self.FLAG_THRESHOLD *= 1.02
                self.BLOCK_THRESHOLD *= 1.02


# ============================================================================
# INTEGRATION: Drop this into your inference.py
# ============================================================================

def create_fraud_detector() -> FraudDetector:
    """Factory function for creating the detector."""
    return FraudDetector()


def smart_fraud_decision(obs: Dict, detector: Optional[FraudDetector] = None, debug: bool = False) -> str:
    """
    Wrapper function for inference.py integration.
    
    Usage in inference.py:
        detector = create_fraud_detector()
        decision = smart_fraud_decision(obs, detector, debug=True)
    """
    if detector is None:
        detector = create_fraud_detector()
    
    return detector.decide_action(obs, debug=debug)
