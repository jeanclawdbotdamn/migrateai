"""Migration Risk Scoring Engine — composite risk from multiple signals."""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from apis.defillama import compare_chains, get_all_bridges
from apis.wormhole import assess_bridge_risk, CHAIN_IDS


# Known bridge exploits (for risk assessment)
BRIDGE_INCIDENTS = {
    "wormhole": {"date": "2022-02-02", "loss_usd": 320_000_000, "recovered": True,
                 "note": "Solana VAA signature bypass. Patched, funds recovered via Jump Crypto."},
    "ronin": {"date": "2022-03-23", "loss_usd": 625_000_000, "recovered": False,
              "note": "Axie Infinity bridge. Social engineering of validators."},
    "nomad": {"date": "2022-08-01", "loss_usd": 190_000_000, "recovered": False,
              "note": "Initialization bug allowed anyone to drain."},
    "harmony": {"date": "2022-06-23", "loss_usd": 100_000_000, "recovered": False,
                "note": "Horizon bridge. Compromised private keys."},
    "multichain": {"date": "2023-07-06", "loss_usd": 126_000_000, "recovered": False,
                   "note": "CEO arrested, funds drained from MPC addresses."},
}

# Chain-specific migration complexity
CHAIN_COMPATIBILITY = {
    # (source, target): difficulty score 0-100 (higher = harder)
    ("ethereum", "arbitrum"): 10,     # EVM → EVM L2, very easy
    ("ethereum", "optimism"): 10,     # EVM → EVM L2
    ("ethereum", "base"): 10,         # EVM → EVM L2
    ("ethereum", "polygon"): 15,      # EVM → EVM sidechain
    ("ethereum", "bsc"): 15,          # EVM → EVM
    ("ethereum", "avalanche"): 15,    # EVM → EVM
    ("ethereum", "solana"): 80,       # EVM → SVM, major rewrite
    ("ethereum", "sui"): 85,          # EVM → Move, major rewrite
    ("ethereum", "aptos"): 85,        # EVM → Move
    ("ethereum", "near"): 70,         # EVM → NEAR/Rust
    ("ethereum", "cosmos"): 60,       # EVM → Cosmos SDK
    ("solana", "ethereum"): 75,       # SVM → EVM, different paradigm
    ("bsc", "solana"): 80,            # EVM → SVM
    ("polygon", "solana"): 80,        # EVM → SVM
    ("arbitrum", "solana"): 80,       # EVM → SVM
    ("fantom", "solana"): 80,         # EVM → SVM
    ("avalanche", "solana"): 80,      # EVM → SVM
}

# EVM → Solana specific migration challenges
EVM_TO_SOLANA_CHALLENGES = [
    {"issue": "Account Model", "severity": "HIGH",
     "detail": "EVM uses contract storage; Solana uses separate accounts (PDAs). All state management must be redesigned."},
    {"issue": "Language Rewrite", "severity": "HIGH",
     "detail": "Solidity → Rust/Anchor rewrite required. No automated transpiler exists."},
    {"issue": "Token Standard", "severity": "MEDIUM",
     "detail": "ERC-20 → SPL Token / Token-2022. Different interfaces, approval patterns, metadata."},
    {"issue": "Gas Model", "severity": "MEDIUM",
     "detail": "EVM gas → Solana compute units + rent. Economic model differs significantly."},
    {"issue": "Reentrancy", "severity": "LOW",
     "detail": "Solana's single-threaded execution eliminates reentrancy. Remove guards, simplify logic."},
    {"issue": "Cross-Contract Calls", "severity": "MEDIUM",
     "detail": "Internal calls → Cross-Program Invocation (CPI). Requires explicit account passing."},
    {"issue": "Events/Logs", "severity": "LOW",
     "detail": "Solidity events → Anchor events or raw logs. Different indexing approach."},
    {"issue": "Upgradeability", "severity": "MEDIUM",
     "detail": "Proxy patterns → Solana's native program upgrade authority. Simpler but different."},
]


def get_contract_complexity(source_chain: str, target_chain: str) -> dict:
    """Estimate migration complexity between two chains."""
    key = (source_chain.lower(), target_chain.lower())
    reverse_key = (target_chain.lower(), source_chain.lower())

    difficulty = CHAIN_COMPATIBILITY.get(key, CHAIN_COMPATIBILITY.get(reverse_key, 50))

    # Determine if it's EVM → non-EVM
    evm_chains = {"ethereum", "bsc", "polygon", "arbitrum", "optimism", "base", "avalanche", "fantom"}
    source_is_evm = source_chain.lower() in evm_chains
    target_is_solana = target_chain.lower() == "solana"

    challenges = []
    if source_is_evm and target_is_solana:
        challenges = EVM_TO_SOLANA_CHALLENGES
    elif source_is_evm and target_chain.lower() in evm_chains:
        challenges = [
            {"issue": "Minimal Changes", "severity": "LOW",
             "detail": "EVM → EVM migration. Contracts are largely compatible with minor adjustments."},
        ]

    return {
        "source": source_chain,
        "target": target_chain,
        "difficulty_score": difficulty,
        "difficulty_level": (
            "TRIVIAL" if difficulty < 20 else
            "EASY" if difficulty < 40 else
            "MODERATE" if difficulty < 60 else
            "HARD" if difficulty < 80 else
            "VERY HARD"
        ),
        "requires_rewrite": difficulty >= 60,
        "estimated_weeks": (
            "1-2" if difficulty < 20 else
            "2-4" if difficulty < 40 else
            "4-8" if difficulty < 60 else
            "8-16" if difficulty < 80 else
            "16-32"
        ),
        "challenges": challenges,
    }


def compute_migration_risk(source: str, target: str) -> dict:
    """
    Compute comprehensive migration risk score.
    Combines: chain health, bridge risk, contract complexity, historical incidents.
    """
    # 1. Chain risk
    chain_data = compare_chains(source, target)
    chain_score = 0
    if isinstance(chain_data, dict) and "error" not in chain_data:
        # Invert migration signal — high signal = low risk
        chain_score = max(0, 100 - chain_data.get("migration_signal_score", 50))
    else:
        chain_score = 50  # Unknown = medium risk

    # 2. Bridge risk
    bridge_data = assess_bridge_risk()
    bridge_score = bridge_data.get("risk_score", 30) if isinstance(bridge_data, dict) else 30

    # 3. Contract complexity risk
    complexity = get_contract_complexity(source, target)
    code_score = complexity["difficulty_score"]

    # 4. Historical incident risk
    incident_score = 0
    for bridge_name, incident in BRIDGE_INCIDENTS.items():
        if not incident["recovered"]:
            incident_score += 5  # Each unrecovered major hack adds risk

    # Composite score (weighted)
    weights = {"chain": 0.25, "bridge": 0.25, "code": 0.35, "incident": 0.15}
    composite = (
        chain_score * weights["chain"] +
        bridge_score * weights["bridge"] +
        code_score * weights["code"] +
        incident_score * weights["incident"]
    )

    return {
        "overall_risk_score": round(composite),
        "risk_level": (
            "LOW" if composite < 25 else
            "MEDIUM" if composite < 50 else
            "HIGH" if composite < 75 else
            "CRITICAL"
        ),
        "breakdown": {
            "chain_risk": {"score": chain_score, "weight": weights["chain"],
                          "note": "Based on TVL trends and ecosystem health"},
            "bridge_risk": {"score": bridge_score, "weight": weights["bridge"],
                          "note": "Based on Wormhole TVL and activity"},
            "code_complexity": {"score": code_score, "weight": weights["code"],
                               "level": complexity["difficulty_level"],
                               "estimated_weeks": complexity["estimated_weeks"],
                               "requires_rewrite": complexity["requires_rewrite"]},
            "historical_risk": {"score": incident_score, "weight": weights["incident"],
                               "note": f"{len(BRIDGE_INCIDENTS)} major bridge incidents tracked"},
        },
        "challenges": complexity["challenges"],
        "recommendation": chain_data.get("recommendation", "Unable to assess") if isinstance(chain_data, dict) else "Unable to assess",
    }


if __name__ == "__main__":
    if len(sys.argv) > 2:
        result = compute_migration_risk(sys.argv[1], sys.argv[2])
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python risk_scorer.py <source_chain> <target_chain>")
        print("Example: python risk_scorer.py Fantom Solana")
