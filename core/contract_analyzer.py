"""Contract Pattern Analyzer — identifies common contract patterns and migration paths."""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Common EVM contract patterns and their Solana equivalents
EVM_TO_SOLANA_PATTERNS = {
    "ERC-20": {
        "description": "Fungible token standard",
        "solana_equivalent": "SPL Token / Token-2022",
        "difficulty": 2,
        "notes": "Direct mapping exists. Token-2022 adds extensions (transfer fees, confidential transfers).",
        "key_differences": [
            "ERC-20 is per-contract; SPL Token is a single program for ALL tokens",
            "Balances stored in Associated Token Accounts (ATAs), not contract storage",
            "Mint authority replaces owner/admin pattern",
            "No approve/transferFrom — use delegate instead",
        ],
    },
    "ERC-721": {
        "description": "Non-fungible token (NFT)",
        "solana_equivalent": "Metaplex Token Standard / Token-2022 NFT",
        "difficulty": 3,
        "notes": "Metaplex provides NFT standards with metadata, collections, and programmable NFTs.",
        "key_differences": [
            "NFT = SPL token with supply of 1 and 0 decimals",
            "Metadata stored in separate Metaplex metadata account",
            "Collection verification via Metaplex Certified Collections",
            "Royalty enforcement via Programmable NFTs (pNFTs)",
        ],
    },
    "AMM/DEX": {
        "description": "Automated Market Maker / Decentralized Exchange",
        "solana_equivalent": "Raydium CLMM / Orca Whirlpool / Custom Anchor program",
        "difficulty": 8,
        "notes": "Major architectural differences. Solana AMMs use account-based pool state.",
        "key_differences": [
            "Pool state in PDAs, not contract storage slots",
            "Token reserves in SPL token accounts owned by pool PDA",
            "Swap instruction vs swap function — CPI to SPL Token for transfers",
            "No reentrancy risk (Solana is single-threaded per tx)",
            "Compute unit limits replace gas optimization",
        ],
    },
    "Lending/Borrowing": {
        "description": "Lending protocol (Aave/Compound-like)",
        "solana_equivalent": "Solend / MarginFi / Kamino / Custom",
        "difficulty": 9,
        "notes": "Complex state management. Interest rate models need careful reimplementation.",
        "key_differences": [
            "User positions stored in separate accounts (not mappings)",
            "Oracle integration via Pyth/Switchboard instead of Chainlink",
            "Liquidation bot architecture differs (Solana clock-based)",
            "Flash loans possible via CPI but different pattern",
        ],
    },
    "Staking": {
        "description": "Token staking / yield farming",
        "solana_equivalent": "SPL Stake Pool / Custom Anchor staking",
        "difficulty": 4,
        "notes": "Relatively straightforward. Solana has native staking infrastructure.",
        "key_differences": [
            "Stake accounts are first-class Solana objects for SOL staking",
            "SPL staking uses token accounts + PDA-based reward tracking",
            "No block.timestamp — use Clock sysvar",
            "Reward distribution via separate claim instruction",
        ],
    },
    "Governance/DAO": {
        "description": "On-chain governance (Governor/Timelock)",
        "solana_equivalent": "Realms (SPL Governance) / Squads",
        "difficulty": 5,
        "notes": "Realms is the standard Solana governance framework. Squads for multisig.",
        "key_differences": [
            "Proposals, votes, and execution are separate accounts",
            "Realm = community + council governance",
            "Token-weighted voting via voter weight plugins",
            "Squads v4 for multisig treasury management",
        ],
    },
    "Vault/Yield": {
        "description": "Yield vault (ERC-4626 / Yearn-like)",
        "solana_equivalent": "Kamino / Custom Anchor vault",
        "difficulty": 6,
        "notes": "No ERC-4626 standard on Solana. Custom implementation needed.",
        "key_differences": [
            "Vault shares as SPL tokens (mint/burn pattern)",
            "Strategy execution via CPI to DEX/lending programs",
            "No composable vault standard — each protocol is custom",
            "Rebalancing triggered by cranks (off-chain bots)",
        ],
    },
    "Bridge": {
        "description": "Cross-chain bridge contract",
        "solana_equivalent": "Wormhole NTT / Custom bridge program",
        "difficulty": 9,
        "notes": "Use Wormhole NTT SDK for standard bridge needs. Custom bridges are complex.",
        "key_differences": [
            "Wormhole Guardian network for message verification",
            "NTT Manager program handles burn-mint flow",
            "VAA (Verified Action Approval) instead of merkle proofs",
            "Rate limiting built into NTT framework",
        ],
    },
    "Oracle Consumer": {
        "description": "Contract consuming price feeds",
        "solana_equivalent": "Pyth / Switchboard",
        "difficulty": 2,
        "notes": "Pyth is the primary Solana oracle. Drop-in replacement for Chainlink.",
        "key_differences": [
            "Pyth accounts passed as instruction accounts (not getLatestRoundData)",
            "Pull oracle model — prices updated on-demand",
            "Confidence intervals included in Pyth prices",
            "Switchboard for custom data feeds / VRF",
        ],
    },
    "Multisig": {
        "description": "Multi-signature wallet",
        "solana_equivalent": "Squads v4",
        "difficulty": 2,
        "notes": "Squads is the standard Solana multisig. Well-audited and widely used.",
        "key_differences": [
            "Squads manages a vault PDA that holds assets",
            "Transaction proposals created as separate accounts",
            "Members approve by signing approve instruction",
            "Built-in spending limits and time locks",
        ],
    },
}

# Contract complexity categories
COMPLEXITY_LEVELS = {
    (1, 3): {"level": "Simple", "emoji": "🟢", "timeline": "2-4 weeks"},
    (4, 6): {"level": "Moderate", "emoji": "🟡", "timeline": "4-8 weeks"},
    (7, 8): {"level": "Complex", "emoji": "🟠", "timeline": "8-16 weeks"},
    (9, 10): {"level": "Very Complex", "emoji": "🔴", "timeline": "16-24+ weeks"},
}


def identify_patterns(contract_types: list) -> list:
    """Identify migration patterns for given contract types."""
    results = []
    for ct in contract_types:
        ct_upper = ct.upper().replace(" ", "").replace("-", "").replace("/", "")
        for pattern_name, info in EVM_TO_SOLANA_PATTERNS.items():
            pattern_key = pattern_name.upper().replace(" ", "").replace("-", "").replace("/", "")
            if pattern_key in ct_upper or ct_upper in pattern_key:
                results.append({"pattern": pattern_name, **info})
                break
        else:
            # Try partial match
            for pattern_name, info in EVM_TO_SOLANA_PATTERNS.items():
                if any(word.lower() in ct.lower() for word in pattern_name.split("/")):
                    results.append({"pattern": pattern_name, **info})
                    break
            else:
                results.append({
                    "pattern": ct,
                    "description": "Custom contract",
                    "solana_equivalent": "Custom Anchor program",
                    "difficulty": 7,
                    "notes": "No standard equivalent. Requires custom architecture design.",
                    "key_differences": ["Full reimplementation required"],
                })
    return results


def estimate_project_complexity(contract_types: list) -> dict:
    """Estimate overall project migration complexity."""
    patterns = identify_patterns(contract_types)

    if not patterns:
        return {
            "overall_difficulty": 5,
            "level": "Unknown",
            "timeline": "TBD",
            "patterns": [],
        }

    max_difficulty = max(p["difficulty"] for p in patterns)
    avg_difficulty = sum(p["difficulty"] for p in patterns) / len(patterns)
    # Overall is weighted toward max (hardest piece bottlenecks everything)
    overall = int(avg_difficulty * 0.3 + max_difficulty * 0.7)

    level_info = {"level": "Unknown", "emoji": "⚪", "timeline": "TBD"}
    for (lo, hi), info in COMPLEXITY_LEVELS.items():
        if lo <= overall <= hi:
            level_info = info
            break

    return {
        "overall_difficulty": overall,
        "level": level_info["level"],
        "emoji": level_info["emoji"],
        "timeline": level_info["timeline"],
        "max_difficulty": max_difficulty,
        "bottleneck": max(patterns, key=lambda p: p["difficulty"])["pattern"],
        "contract_count": len(patterns),
        "patterns": patterns,
    }


def generate_contract_report(contract_types: list, source: str = "EVM", target: str = "Solana") -> str:
    """Generate human-readable contract analysis report."""
    complexity = estimate_project_complexity(contract_types)
    patterns = complexity["patterns"]

    report = f"""# 📝 Contract Migration Analysis
## {source} → {target}

### Overall Complexity: {complexity['emoji']} {complexity['level']} (Difficulty: {complexity['overall_difficulty']}/10)
- Estimated Timeline: **{complexity['timeline']}**
- Contract Types: **{complexity['contract_count']}**
- Bottleneck: **{complexity['bottleneck']}** (difficulty {complexity['max_difficulty']}/10)

---
"""
    for p in patterns:
        diff = p["difficulty"]
        emoji = "🟢" if diff <= 3 else ("🟡" if diff <= 6 else ("🟠" if diff <= 8 else "🔴"))
        report += f"""
### {emoji} {p['pattern']} → {p['solana_equivalent']}
- **Description:** {p['description']}
- **Difficulty:** {diff}/10
- **Notes:** {p['notes']}

**Key Differences:**
"""
        for kd in p["key_differences"]:
            report += f"- {kd}\n"

    report += f"""
---

### Migration Approach Summary

| Source Pattern | Target Equivalent | Difficulty |
|---|---|---|
"""
    for p in patterns:
        report += f"| {p['pattern']} | {p['solana_equivalent']} | {p['difficulty']}/10 |\n"

    report += f"""
### Recommendations

1. **Start with the simplest contracts** ({min(patterns, key=lambda p: p['difficulty'])['pattern']}) to build familiarity
2. **Tackle the bottleneck** ({complexity['bottleneck']}) early — it determines the timeline
3. **Use existing Solana SDKs** where possible (Anchor, SPL, Metaplex) instead of from-scratch
4. **Test incrementally** — deploy each component to devnet before combining
5. **Budget for a security audit** — especially for {complexity['bottleneck']}
"""

    return report


if __name__ == "__main__":
    # Example: analyze a DeFi protocol with multiple contract types
    if len(sys.argv) > 1:
        types = sys.argv[1:]
        print(generate_contract_report(types))
    else:
        print("Usage: python contract_analyzer.py <contract_type1> [contract_type2] ...")
        print("Example: python contract_analyzer.py AMM ERC-20 Staking Oracle")
        print()
        print("Supported patterns:", ", ".join(EVM_TO_SOLANA_PATTERNS.keys()))
        print()
        # Demo
        print("=== Demo: SpookySwap-like DEX ===\n")
        print(generate_contract_report(["AMM/DEX", "ERC-20", "Staking", "Governance/DAO"]))
