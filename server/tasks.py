"""
tasks.py — Deterministic fraud scenarios for 3 difficulty levels.
"""

from typing import Dict, List, Tuple
from server.models import Transaction, UserProfile


def _ts(hour: int, minute: int = 0) -> str:
    """Create ISO timestamp."""
    return f"2024-01-15T{hour:02d}:{minute:02d}:00Z"


def task_single_fraud() -> Tuple[List[Transaction], Dict, Dict, str]:
    """
    EASY: One UNMISTAKABLE fraud with 5 clear red flags.
    5 transactions, 1 obvious fraud, 4 normal.
    Perfect score target: 1.0 (catch fraud + allow all legit)
    """
    user_id = "user_001"
    
    transactions = [
        # TX_001: Normal morning coffee
        Transaction(
            id="tx_001",
            user_id=user_id,
            amount=6.99,
            merchant="Starbucks",
            merchant_category="food",
            location="New York",
            country="US",
            timestamp=_ts(8, 0),
            device_id="device_001",
            is_international=False,
            velocity_1h=0,
            velocity_24h=0
        ),
        # TX_002: Normal groceries
        Transaction(
            id="tx_002",
            user_id=user_id,
            amount=42.35,
            merchant="Trader Joe's",
            merchant_category="groceries",
            location="New York",
            country="US",
            timestamp=_ts(9, 0),
            device_id="device_001",
            is_international=False,
            velocity_1h=1,
            velocity_24h=1
        ),
        # TX_003: THE FRAUD - $3000 ATM + new device + impossible travel + international
        Transaction(
            id="tx_003",
            user_id=user_id,
            amount=3000.00,
            merchant="HSBC ATM Hong Kong",
            merchant_category="atm_withdrawal",
            location="Hong Kong",
            country="HK",
            timestamp=_ts(14, 15),  # 2 hours after groceries (IMPOSSIBLE TRAVEL from NY)
            device_id="device_unknown_99",  # NEW DEVICE
            is_international=True,
            velocity_1h=0,
            velocity_24h=2
        ),
        # TX_004: Normal evening groceries (after lunch tx_002)
        Transaction(
            id="tx_004",
            user_id=user_id,
            amount=28.50,
            merchant="Whole Foods",
            merchant_category="groceries",
            location="New York",
            country="US",
            timestamp=_ts(18, 0),
            device_id="device_001",
            is_international=False,
            velocity_1h=0,
            velocity_24h=1
        ),
        # TX_005: Normal Netflix subscription
        Transaction(
            id="tx_005",
            user_id=user_id,
            amount=15.99,
            merchant="Netflix",
            merchant_category="entertainment",
            location="New York",
            country="US",
            timestamp=_ts(20, 0),
            device_id="device_001",
            is_international=False,
            velocity_1h=0,
            velocity_24h=2
        ),
    ]
    
    user_profiles = {
        user_id: UserProfile(
            user_id=user_id,
            home_country="US",
            home_city="New York",
            avg_monthly_spend=2500.0,
            typical_categories=["groceries", "dining", "transport", "utilities"],
            account_age_days=1250,
            risk_score=0.1
        )
    }
    
    ground_truth = {
        "tx_001": "legit",
        "tx_002": "legit",
        "tx_003": "fraud",  # $3000 ATM + new device + impossible travel + international
        "tx_004": "legit",
        "tx_005": "legit",
    }
    
    description = (
        "EASY: One unmistakable fraud with 5 crystal-clear red flags: "
        "$3000 ATM withdrawal, new device, 2 hours impossible travel from NY to HK, "
        "international flag, wrong location."
    )
    
    return transactions, user_profiles, ground_truth, description


def task_multi_pattern_fraud() -> Tuple[List[Transaction], Dict, Dict, str]:
    """
    MEDIUM: Multiple weak signals. Fraud ring with multiple accounts.
    9 transactions, 3 fraud patterns requiring reasoning.
    """
    
    # Three accounts in fraud ring
    user_a = "user_a"  # Victim
    user_b = "user_b"  # Mule
    user_c = "user_c"  # Receiver
    
    transactions = [
        # User A: Normal activity
        Transaction(
            id="tx_001",
            user_id=user_a,
            amount=50.0,
            merchant="Amazon",
            merchant_category="shopping",
            location="Los Angeles",
            country="US",
            timestamp=_ts(9, 0),
            device_id="device_a_1",
            is_international=False,
            velocity_1h=0,
            velocity_24h=0
        ),
        # User A: FRAUD - Compromised, large transfer
        Transaction(
            id="tx_002",
            user_id=user_a,
            amount=5000.0,
            merchant="Wire Transfer",
            merchant_category="p2p",
            location="Los Angeles",
            country="US",
            timestamp=_ts(10, 15),
            device_id="device_unknown",  # Different device
            is_international=False,
            velocity_1h=1,
            velocity_24h=1
        ),
        # User A: Legit - Normal transaction
        Transaction(
            id="tx_003",
            user_id=user_a,
            amount=75.0,
            merchant="Target",
            merchant_category="shopping",
            location="Los Angeles",
            country="US",
            timestamp=_ts(14, 0),
            device_id="device_a_1",
            is_international=False,
            velocity_1h=0,
            velocity_24h=1
        ),
        # User B: Normal activity
        Transaction(
            id="tx_004",
            user_id=user_b,
            amount=60.0,
            merchant="Starbucks",
            merchant_category="dining",
            location="Chicago",
            country="US",
            timestamp=_ts(11, 0),
            device_id="device_b_1",
            is_international=False,
            velocity_1h=0,
            velocity_24h=0
        ),
        # User B: FRAUD - Receives wire from user_a (different device)
        Transaction(
            id="tx_005",
            user_id=user_b,
            amount=5000.0,
            merchant="Wire Deposit",
            merchant_category="p2p",
            location="Chicago",
            country="US",
            timestamp=_ts(10, 30),
            device_id="device_b_1",
            is_international=False,
            velocity_1h=1,
            velocity_24h=1
        ),
        # User B: FRAUD - Immediately transfers out
        Transaction(
            id="tx_006",
            user_id=user_b,
            amount=4950.0,
            merchant="Wire Transfer",
            merchant_category="p2p",
            location="Chicago",
            country="US",
            timestamp=_ts(10, 45),
            device_id="device_b_1",
            is_international=False,
            velocity_1h=2,
            velocity_24h=2
        ),
        # User C: Receives final wire
        Transaction(
            id="tx_007",
            user_id=user_c,
            amount=4950.0,
            merchant="Wire Deposit",
            merchant_category="p2p",
            location="Miami",
            country="US",
            timestamp=_ts(11, 15),
            device_id="device_c_1",
            is_international=False,
            velocity_1h=1,
            velocity_24h=1
        ),
        # User C: Cashes out (structuring)
        Transaction(
            id="tx_008",
            user_id=user_c,
            amount=3000.0,
            merchant="ATM Withdrawal",
            merchant_category="atm_withdrawal",
            location="Miami",
            country="US",
            timestamp=_ts(12, 0),
            device_id="device_c_1",
            is_international=False,
            velocity_1h=1,
            velocity_24h=1
        ),
        Transaction(
            id="tx_009",
            user_id=user_c,
            amount=1950.0,
            merchant="ATM Withdrawal",
            merchant_category="atm_withdrawal",
            location="Miami",
            country="US",
            timestamp=_ts(13, 0),
            device_id="device_c_2",  # Different device
            is_international=False,
            velocity_1h=1,
            velocity_24h=2
        ),
    ]
    
    user_profiles = {
        user_a: UserProfile(
            user_id=user_a,
            home_country="US",
            home_city="Los Angeles",
            avg_monthly_spend=1500.0,
            typical_categories=["shopping", "dining", "utilities"],
            account_age_days=800,
            risk_score=0.15
        ),
        user_b: UserProfile(
            user_id=user_b,
            home_country="US",
            home_city="Chicago",
            avg_monthly_spend=1200.0,
            typical_categories=["dining", "transport", "shopping"],
            account_age_days=600,
            risk_score=0.1
        ),
        user_c: UserProfile(
            user_id=user_c,
            home_country="US",
            home_city="Miami",
            avg_monthly_spend=800.0,
            typical_categories=["dining", "shopping"],
            account_age_days=300,
            risk_score=0.3
        ),
    }
    
    ground_truth = {
        "tx_001": "legit",
        "tx_002": "fraud",  # Large transfer from different device
        "tx_003": "legit",
        "tx_004": "legit",
        "tx_005": "fraud",  # Receives compromised funds
        "tx_006": "fraud",  # Immediate transfer out (mule behavior)
        "tx_007": "fraud",  # Receives from mule
        "tx_008": "fraud",  # Structuring: cash out in chunks
        "tx_009": "fraud",  # Structuring: second cashout
    }
    
    description = (
        "MEDIUM: Detect fraud ring. User A compromised, funds routed through mule account (B), "
        "then consolidated (C). Requires pattern detection across accounts: large transfer, "
        "high velocity, structuring behavior."
    )
    
    return transactions, user_profiles, ground_truth, description


def task_adaptive_fraud_attack() -> Tuple[List[Transaction], Dict, Dict, str]:
    """
    HARD: Adaptive fraud mimicking normal behavior. Slow, low-amounts, legitimate patterns.
    20 transactions with gradual escalation (hard to spot without behavioral profiling).
    """
    user_id = "user_vip"
    
    transactions = [
        # Days 1-3: Account takeover, mimics normal behavior
        Transaction(
            id="tx_001",
            user_id=user_id,
            amount=85.0,
            merchant="Target",
            merchant_category="shopping",
            location="San Francisco",
            country="US",
            timestamp=_ts(8, 0),
            device_id="device_legit",
            is_international=False,
            velocity_1h=0,
            velocity_24h=0
        ),
        Transaction(
            id="tx_002",
            user_id=user_id,
            amount=45.0,
            merchant="Chipotle",
            merchant_category="dining",
            location="San Francisco",
            country="US",
            timestamp=_ts(12, 30),
            device_id="device_legit",
            is_international=False,
            velocity_1h=0,
            velocity_24h=1
        ),
        Transaction(
            id="tx_003",
            user_id=user_id,
            amount=120.0,
            merchant="Uber",
            merchant_category="transport",
            location="San Francisco",
            country="US",
            timestamp=_ts(18, 0),
            device_id="device_legit",
            is_international=False,
            velocity_1h=0,
            velocity_24h=2
        ),
        Transaction(
            id="tx_004",
            user_id=user_id,
            amount=50.0,
            merchant="Whole Foods",
            merchant_category="groceries",
            location="San Francisco",
            country="US",
            timestamp=_ts(9, 0),
            device_id="device_legit",
            is_international=False,
            velocity_1h=0,
            velocity_24h=0
        ),
        Transaction(
            id="tx_005",
            user_id=user_id,
            amount=200.0,
            merchant="Apple Store",
            merchant_category="shopping",
            location="San Francisco",
            country="US",
            timestamp=_ts(11, 0),
            device_id="device_legit",
            is_international=False,
            velocity_1h=1,
            velocity_24h=1
        ),
        # FRAUD starts: Small transfers to new account (mimicking bill payments)
        Transaction(
            id="tx_006",
            user_id=user_id,
            amount=250.0,
            merchant="Venmo Transfer",
            merchant_category="p2p",
            location="San Francisco",
            country="US",
            timestamp=_ts(15, 0),
            device_id="device_legit",
            is_international=False,
            velocity_1h=0,
            velocity_24h=2
        ),
        Transaction(
            id="tx_007",
            user_id=user_id,
            amount=300.0,
            merchant="PayPal Transfer",
            merchant_category="p2p",
            location="San Francisco",
            country="US",
            timestamp=_ts(16, 30),
            device_id="device_legit",
            is_international=False,
            velocity_1h=1,
            velocity_24h=3
        ),
        Transaction(
            id="tx_008",
            user_id=user_id,
            amount=75.0,
            merchant="Starbucks",
            merchant_category="dining",
            location="San Francisco",
            country="US",
            timestamp=_ts(9, 30),
            device_id="device_legit",
            is_international=False,
            velocity_1h=0,
            velocity_24h=0
        ),
        Transaction(
            id="tx_009",
            user_id=user_id,
            amount=500.0,
            merchant="Wire Transfer",
            merchant_category="p2p",
            location="San Francisco",
            country="US",
            timestamp=_ts(10, 0),
            device_id="device_legit",
            is_international=False,
            velocity_1h=1,
            velocity_24h=1
        ),
        Transaction(
            id="tx_010",
            user_id=user_id,
            amount=100.0,
            merchant="AWS Payment",
            merchant_category="shopping",
            location="San Francisco",
            country="US",
            timestamp=_ts(14, 0),
            device_id="device_legit",
            is_international=False,
            velocity_1h=0,
            velocity_24h=2
        ),
        # Acceleration: Larger transfers, still within normal patterns
        Transaction(
            id="tx_011",
            user_id=user_id,
            amount=750.0,
            merchant="Stripe Payment",
            merchant_category="p2p",
            location="San Francisco",
            country="US",
            timestamp=_ts(11, 30),
            device_id="device_legit",
            is_international=False,
            velocity_1h=1,
            velocity_24h=3
        ),
        Transaction(
            id="tx_012",
            user_id=user_id,
            amount=60.0,
            merchant="Netflix",
            merchant_category="shopping",
            location="San Francisco",
            country="US",
            timestamp=_ts(8, 0),
            device_id="device_legit",
            is_international=False,
            velocity_1h=0,
            velocity_24h=0
        ),
        Transaction(
            id="tx_013",
            user_id=user_id,
            amount=1000.0,
            merchant="Crypto Exchange",
            merchant_category="shopping",
            location="San Francisco",
            country="US",
            timestamp=_ts(13, 0),
            device_id="device_legit",
            is_international=False,
            velocity_1h=1,
            velocity_24h=2
        ),
        Transaction(
            id="tx_014",
            user_id=user_id,
            amount=90.0,
            merchant="Trader Joe's",
            merchant_category="groceries",
            location="San Francisco",
            country="US",
            timestamp=_ts(17, 0),
            device_id="device_legit",
            is_international=False,
            velocity_1h=0,
            velocity_24h=1
        ),
        Transaction(
            id="tx_015",
            user_id=user_id,
            amount=2000.0,
            merchant="Wire Transfer",
            merchant_category="p2p",
            location="San Francisco",
            country="US",
            timestamp=_ts(9, 45),
            device_id="device_legit",
            is_international=False,
            velocity_1h=1,
            velocity_24h=2
        ),
        # Final push: Large amounts (cumulative impact critical)
        Transaction(
            id="tx_016",
            user_id=user_id,
            amount=80.0,
            merchant="Lyft",
            merchant_category="transport",
            location="San Francisco",
            country="US",
            timestamp=_ts(7, 0),
            device_id="device_legit",
            is_international=False,
            velocity_1h=0,
            velocity_24h=0
        ),
        Transaction(
            id="tx_017",
            user_id=user_id,
            amount=3000.0,
            merchant="Bank Wire Out",
            merchant_category="p2p",
            location="San Francisco",
            country="US",
            timestamp=_ts(12, 0),
            device_id="device_legit",
            is_international=False,
            velocity_1h=1,
            velocity_24h=2
        ),
        Transaction(
            id="tx_018",
            user_id=user_id,
            amount=55.0,
            merchant="Dunkin Donuts",
            merchant_category="dining",
            location="San Francisco",
            country="US",
            timestamp=_ts(8, 30),
            device_id="device_legit",
            is_international=False,
            velocity_1h=0,
            velocity_24h=1
        ),
        Transaction(
            id="tx_019",
            user_id=user_id,
            amount=5000.0,
            merchant="Cash Advance",
            merchant_category="atm_withdrawal",
            location="San Francisco",
            country="US",
            timestamp=_ts(15, 30),
            device_id="device_legit",
            is_international=False,
            velocity_1h=1,
            velocity_24h=2
        ),
        Transaction(
            id="tx_020",
            user_id=user_id,
            amount=110.0,
            merchant="Movie Tickets",
            merchant_category="entertainment",
            location="San Francisco",
            country="US",
            timestamp=_ts(19, 0),
            device_id="device_legit",
            is_international=False,
            velocity_1h=0,
            velocity_24h=1
        ),
    ]
    
    user_profiles = {
        user_id: UserProfile(
            user_id=user_id,
            home_country="US",
            home_city="San Francisco",
            avg_monthly_spend=5000.0,
            typical_categories=["shopping", "dining", "transport", "entertainment", "groceries"],
            account_age_days=2000,
            risk_score=0.05  # VIP: Low historical risk
        )
    }
    
    # Gradual fraud escalation
    ground_truth = {
        "tx_001": "legit",
        "tx_002": "legit",
        "tx_003": "legit",
        "tx_004": "legit",
        "tx_005": "legit",
        "tx_006": "fraud",  # Small P2P transfer starts
        "tx_007": "fraud",
        "tx_008": "legit",
        "tx_009": "fraud",  # Wire transfer (escalation)
        "tx_010": "legit",
        "tx_011": "fraud",  # Larger P2P
        "tx_012": "legit",
        "tx_013": "fraud",  # Cryptocurrency (risky category)
        "tx_014": "legit",
        "tx_015": "fraud",  # $2K wire transfer
        "tx_016": "legit",
        "tx_017": "fraud",  # $3K wire transfer
        "tx_018": "legit",
        "tx_019": "fraud",  # $5K cash advance (top-up before account freeze)
        "tx_020": "legit",
    }
    
    description = (
        "HARD: Adaptive fraud. Attacker gradually siphons funds using legitimate-looking "
        "P2P transfers mixed with normal spending. No obvious red flags — requires behavioral "
        "baseline analysis (cumulative P2P volume, pattern changes, amount escalation)."
    )
    
    return transactions, user_profiles, ground_truth, description


TASK_REGISTRY = {
    "single_fraud": {
        "loader": task_single_fraud,
        "description": "EASY: Detect obvious fraud with impossible travel anomaly.",
        "difficulty": 1,
    },
    "multi_pattern_fraud": {
        "loader": task_multi_pattern_fraud,
        "description": "MEDIUM: Detect fraud ring across multiple accounts.",
        "difficulty": 2,
    },
    "adaptive_fraud_attack": {
        "loader": task_adaptive_fraud_attack,
        "description": "HARD: Detect adaptive fraud mimicking normal behavior.",
        "difficulty": 3,
    },
}