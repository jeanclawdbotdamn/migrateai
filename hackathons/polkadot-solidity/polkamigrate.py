#!/usr/bin/env python3
"""
PolkaMigrate: EVM → Polkadot Migration Analyzer
Polkadot Solidity Hackathon 2026

Analyzes existing Solidity/EVM contracts and evaluates migration
feasibility to Polkadot EVM parachains (Moonbeam, Astar, Acala).

Key Insight: Polkadot EVM parachains support Solidity natively,
so migration is MUCH simpler than EVM → non-EVM (like Solana).
The tool focuses on parachain selection, compatibility quirks,
XCM cross-chain messaging, and optimization opportunities.

Hackathon Tags: Solidity, DeFi, AI-powered dapps
"""

import json
import sys
import os
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from apis.defillama import get_all_chains, get_chain_health, compare_chains, get_protocols_by_chain
from core.chain_health import full_chain_comparison
from core.risk_scorer import compute_migration_risk
from core.token_analysis import get_available_bridges, get_dex_ecosystem


# ─────────────────────────────────────────────────────────────────────────────
# Polkadot Parachain Data
# ─────────────────────────────────────────────────────────────────────────────

PARACHAINS = {
    "moonbeam": {
        "name": "Moonbeam",
        "parachain_id": 2004,
        "evm_compatible": True,
        "solidity_support": "Full (EVM + Substrate precompiles)",
        "native_token": "GLMR",
        "tvl_key": "Moonbeam",  # DeFi Llama name
        "highlights": [
            "Full Ethereum API compatibility (ethers.js, web3.js, Hardhat)",
            "Substrate precompiles for XCM, staking, governance",
            "Connected to 49+ parachains via XCM",
            "Wormhole, Axelar, LayerZero bridges available",
            "Native Batch precompile for multicall",
        ],
        "dexes": ["Stellaswap", "Beamswap", "Zenlink"],
        "oracles": ["Chainlink (limited)", "DIA", "Band Protocol"],
        "quirks": [
            "Gas costs use GLMR (similar to ETH gas model)",
            "Different block time (12s vs Ethereum's 12s — similar)",
            "Existential deposit requirement for new accounts",
            "Custom precompiles may need adaptation for some use cases",
            "No EIP-1559 — legacy gas pricing",
        ],
        "difficulty": 2,  # 1-10 scale for EVM migration
    },
    "astar": {
        "name": "Astar",
        "parachain_id": 2006,
        "evm_compatible": True,
        "solidity_support": "Full (EVM) + Wasm (ink!)",
        "native_token": "ASTR",
        "tvl_key": "Astar",
        "highlights": [
            "Dual VM: EVM + Wasm (ink! smart contracts)",
            "dApp staking: developers earn ASTR from stakers",
            "Cross-VM composability (EVM ↔ Wasm)",
            "Connected via XCM and bridges",
            "Build2Earn incentive model",
        ],
        "dexes": ["ArthSwap", "AstridDAO", "Zenlink"],
        "oracles": ["DIA", "Band Protocol"],
        "quirks": [
            "dApp staking requires registration",
            "Two address formats: H160 (EVM) and SS58 (Substrate)",
            "Cross-VM calls need XVM adapter",
            "Lower block gas limit than Ethereum",
        ],
        "difficulty": 3,
    },
    "acala": {
        "name": "Acala",
        "parachain_id": 2000,
        "evm_compatible": True,
        "solidity_support": "EVM+ (extended Ethereum compatibility)",
        "native_token": "ACA",
        "tvl_key": "Acala",
        "highlights": [
            "EVM+ with Substrate-native DeFi primitives",
            "Built-in DEX (Acala Swap) and stablecoin (aUSD)",
            "Liquid staking (LDOT) built into runtime",
            "On-chain scheduler for recurring transactions",
            "Universal Asset Hub for cross-chain assets",
        ],
        "dexes": ["Acala Swap (built-in)", "Taiga Protocol"],
        "oracles": ["Acala Oracle (built-in)", "Band Protocol"],
        "quirks": [
            "EVM+ has minor differences from standard EVM",
            "Storage rent model differs from Ethereum",
            "Some Solidity patterns need minor adjustments",
            "aUSD stablecoin has faced depegging issues",
        ],
        "difficulty": 4,
    },
}

# EVM → Polkadot compatibility matrix
COMPATIBILITY = {
    "ERC-20": {
        "compatible": True,
        "difficulty": 1,
        "notes": "Direct deploy. Works out of the box on Moonbeam/Astar.",
        "optimization": "Consider using XC-20 for cross-chain token transfers via XCM.",
    },
    "ERC-721": {
        "compatible": True,
        "difficulty": 1,
        "notes": "Direct deploy. NFT standards work natively.",
        "optimization": "Use Moonbeam's Batch precompile for bulk minting.",
    },
    "AMM/DEX": {
        "compatible": True,
        "difficulty": 2,
        "notes": "Uniswap V2/V3 forks deploy directly. Adjust gas optimization.",
        "optimization": "Integrate with parachain DEXes (Stellaswap, ArthSwap) for deeper liquidity.",
    },
    "Lending/Borrowing": {
        "compatible": True,
        "difficulty": 3,
        "notes": "Aave/Compound forks work. Oracle integration needs updating.",
        "optimization": "Use parachain-native oracles (DIA, Band) instead of Chainlink.",
    },
    "Staking": {
        "compatible": True,
        "difficulty": 2,
        "notes": "Standard staking contracts work. Consider using Substrate staking primitives.",
        "optimization": "On Astar: register for dApp staking to earn ASTR rewards.",
    },
    "Governance/DAO": {
        "compatible": True,
        "difficulty": 2,
        "notes": "Governor/Timelock patterns work. Can also use Substrate governance.",
        "optimization": "Moonbeam's governance precompile enables on-chain governance integration.",
    },
    "Oracle Consumer": {
        "compatible": True,
        "difficulty": 2,
        "notes": "Chainlink has limited Polkadot support. DIA and Band are alternatives.",
        "optimization": "DIA provides price feeds natively on most parachains.",
    },
    "Bridge": {
        "compatible": True,
        "difficulty": 3,
        "notes": "Wormhole and Axelar available on Moonbeam. XCM for inter-parachain.",
        "optimization": "XCM is the native cross-chain protocol — cheaper than external bridges.",
    },
}

# XCM (Cross-Consensus Messaging) info
XCM_INFO = {
    "description": (
        "XCM (Cross-Consensus Messaging) is Polkadot's native cross-chain "
        "communication protocol. Unlike external bridges, XCM is secured by "
        "Polkadot's shared security model — no additional trust assumptions."
    ),
    "benefits": [
        "Secured by Polkadot relay chain validators",
        "No external bridge risk (no wrapped tokens)",
        "Low cost (fraction of external bridge fees)",
        "Native asset transfers between parachains",
        "Composable cross-chain calls (not just token transfers)",
    ],
    "supported_chains": "49+ parachains connected via HRMP channels",
}


# ─────────────────────────────────────────────────────────────────────────────
# Analysis
# ─────────────────────────────────────────────────────────────────────────────

def analyze_parachain(source_chain: str, parachain: str = "moonbeam") -> dict:
    """Analyze migration feasibility from an EVM chain to a Polkadot parachain."""
    para = PARACHAINS.get(parachain.lower())
    if not para:
        return {"error": f"Unknown parachain: {parachain}", "available": list(PARACHAINS.keys())}

    result = {
        "source": source_chain,
        "target": para["name"],
        "target_parachain_id": para["parachain_id"],
        "analyzed_at": datetime.utcnow().isoformat() + "Z",
    }

    # Chain comparison
    comparison = full_chain_comparison(source_chain, para["tvl_key"])
    result["comparison"] = comparison

    # Risk (lower for EVM→EVM)
    risk = compute_migration_risk(source_chain, para["tvl_key"])
    result["risk"] = risk

    # Parachain details
    result["parachain"] = {
        "name": para["name"],
        "evm_compatible": para["evm_compatible"],
        "solidity_support": para["solidity_support"],
        "native_token": para["native_token"],
        "highlights": para["highlights"],
        "dexes": para["dexes"],
        "oracles": para["oracles"],
        "quirks": para["quirks"],
        "migration_difficulty": para["difficulty"],
    }

    # Bridge routes
    bridges = get_available_bridges(source_chain, para["tvl_key"])
    result["bridges"] = {"count": len(bridges), "available": bridges}

    # XCM advantage
    result["xcm"] = XCM_INFO

    # Overall score (EVM→Polkadot EVM is generally easier)
    feas = comparison.get("feasibility_score", 50) if "feasibility_score" in comparison else 50
    # Boost because it's EVM→EVM (no rewrite needed)
    evm_bonus = 20
    migration_score = min(100, feas + evm_bonus)
    result["migration_score"] = migration_score
    result["migration_grade"] = (
        "A" if migration_score >= 80 else
        "B" if migration_score >= 65 else
        "C" if migration_score >= 45 else "D"
    )

    return result


def check_compatibility(contract_types: list) -> dict:
    """Check EVM contract compatibility with Polkadot parachains."""
    results = []
    for ct in contract_types:
        compat = COMPATIBILITY.get(ct, {
            "compatible": True,
            "difficulty": 3,
            "notes": "Generic Solidity contract — should work on EVM parachains.",
            "optimization": "Test thoroughly on parachain testnet.",
        })
        results.append({"contract_type": ct, **compat})

    max_diff = max(r["difficulty"] for r in results) if results else 0
    all_compatible = all(r["compatible"] for r in results)

    return {
        "contract_types": contract_types,
        "all_compatible": all_compatible,
        "max_difficulty": max_diff,
        "overall": (
            "TRIVIAL — Direct deploy" if max_diff <= 1 else
            "EASY — Minor adjustments" if max_diff <= 2 else
            "MODERATE — Some changes needed" if max_diff <= 3 else
            "COMPLEX — Significant adaptation required"
        ),
        "estimated_time": (
            "1-2 days" if max_diff <= 1 else
            "1-2 weeks" if max_diff <= 2 else
            "2-4 weeks" if max_diff <= 3 else
            "4-8 weeks"
        ),
        "contracts": results,
    }


def compare_parachains(source_chain: str) -> dict:
    """Compare all Polkadot parachains for migration from a source chain."""
    results = []
    for key, para in PARACHAINS.items():
        health = get_chain_health(para["tvl_key"])
        bridges = get_available_bridges(source_chain, para["tvl_key"])

        results.append({
            "parachain": para["name"],
            "native_token": para["native_token"],
            "tvl": health.get("tvl_formatted", "N/A") if isinstance(health, dict) and "error" not in health else "N/A",
            "tvl_raw": health.get("tvl", 0) if isinstance(health, dict) else 0,
            "trend": health.get("tvl_trend", "unknown") if isinstance(health, dict) else "unknown",
            "difficulty": para["difficulty"],
            "bridge_count": len(bridges),
            "dex_count": len(para["dexes"]),
            "solidity_support": para["solidity_support"],
        })

    results.sort(key=lambda x: x["tvl_raw"], reverse=True)
    return {
        "source": source_chain,
        "parachains": results,
        "recommendation": results[0]["parachain"] if results else "Unknown",
    }


def generate_polkadot_report(source: str, parachain: str = "moonbeam",
                              contract_types: list = None) -> str:
    """Generate a Polkadot migration report."""
    analysis = analyze_parachain(source, parachain)
    para = analysis.get("parachain", {})
    comp = analysis.get("comparison", {})
    src = comp.get("source_chain", {})
    tgt = comp.get("target_chain", {})

    compat = check_compatibility(contract_types or []) if contract_types else None

    report = f"""# 🟣 Polkadot Migration Report: {source} → {para.get('name', parachain)}
*Generated by PolkaMigrate (MigrateAI) — Polkadot Solidity Hackathon 2026*

## 📊 Executive Summary

| Metric | Value |
|--------|-------|
| **Migration Score** | {analysis['migration_score']}/100 (Grade {analysis['migration_grade']}) |
| **EVM Compatible** | {'✅ Yes — Direct Solidity deploy' if para.get('evm_compatible') else '❌ No'} |
| **Migration Difficulty** | {para.get('migration_difficulty', '?')}/10 |
| **Solidity Support** | {para.get('solidity_support', 'N/A')} |

**Key Advantage**: Polkadot EVM parachains support Solidity natively. No contract rewrite needed — just deploy, adjust configs, and optimize.

## 🔗 Source: {source}
- TVL: {src.get('tvl_formatted', 'N/A')}
- 30d Change: {src.get('tvl_change_30d_pct', 0):.1f}%
- Trend: {src.get('tvl_trend', 'N/A').upper()}

## 🟣 Target: {para.get('name', parachain)}
- TVL: {tgt.get('tvl_formatted', 'N/A')}
- Native Token: {para.get('native_token', '?')}
- DEXes: {', '.join(para.get('dexes', []))}
- Oracles: {', '.join(para.get('oracles', []))}

### Highlights
"""
    for h in para.get("highlights", []):
        report += f"- {h}\n"

    report += "\n### Known Quirks\n"
    for q in para.get("quirks", []):
        report += f"- ⚠️ {q}\n"

    # Compatibility
    if compat:
        report += f"""
## 📝 Contract Compatibility

**Overall**: {compat['overall']}
**Estimated Time**: {compat['estimated_time']}

| Contract | Compatible | Difficulty | Notes |
|----------|-----------|-----------|-------|
"""
        for c in compat["contracts"]:
            emoji = "✅" if c["compatible"] else "❌"
            report += f"| {c['contract_type']} | {emoji} | {c['difficulty']}/10 | {c['notes']} |\n"

        report += "\n### Optimization Opportunities\n"
        for c in compat["contracts"]:
            if c.get("optimization"):
                report += f"- **{c['contract_type']}**: {c['optimization']}\n"

    # XCM
    report += f"""
## 🔗 Cross-Chain: XCM

{XCM_INFO['description']}

### Benefits over External Bridges
"""
    for b in XCM_INFO["benefits"]:
        report += f"- {b}\n"

    report += f"""
## 📋 Migration Steps

1. **Set up development environment**
   - Install Moonbeam/Astar development tools
   - Configure Hardhat/Foundry for the target parachain
   - Get testnet tokens from faucet

2. **Deploy contracts to testnet**
   - Deploy existing Solidity contracts as-is
   - Update RPC endpoints and chain IDs
   - Update oracle addresses (Chainlink → DIA/Band)
   - Adjust gas settings if needed

3. **Test and optimize**
   - Run full test suite on parachain testnet
   - Test XCM integration if cross-chain needed
   - Optimize for parachain-specific features

4. **Migrate frontend**
   - Update chain ID and RPC in frontend config
   - Add parachain wallet support (if needed)
   - Update token addresses and contracts

5. **Launch**
   - Deploy to mainnet
   - Seed liquidity on parachain DEXes
   - Announce migration to community

---
*Generated by PolkaMigrate (MigrateAI) — https://github.com/jeanclawdbotdamn/migrateai*
"""
    return report


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

BANNER = """
╔══════════════════════════════════════════════════╗
║  🟣 PolkaMigrate: EVM → Polkadot Analyzer v0.1   ║
║  MigrateAI × Polkadot Solidity Hackathon 2026    ║
╚══════════════════════════════════════════════════╝
"""


def main():
    if len(sys.argv) < 2:
        print(BANNER)
        print("Usage:")
        print("  python polkamigrate.py analyze <source> [parachain]    — Migration analysis")
        print("  python polkamigrate.py compare <source>                — Compare all parachains")
        print("  python polkamigrate.py compat <type1> [type2...]       — Check contract compatibility")
        print("  python polkamigrate.py report <source> [parachain]     — Full migration report")
        print("  python polkamigrate.py parachains                      — List supported parachains")
        print()
        print("Parachains: Moonbeam (default), Astar, Acala")
        print()
        print("Examples:")
        print("  python polkamigrate.py analyze Ethereum Moonbeam")
        print("  python polkamigrate.py compare Fantom")
        print("  python polkamigrate.py compat AMM/DEX ERC-20 Staking")
        print("  python polkamigrate.py report Ethereum Astar > report.md")
        return

    cmd = sys.argv[1].lower()
    args = sys.argv[2:]

    if cmd == "analyze":
        print(BANNER)
        source = args[0] if args else "Ethereum"
        para = args[1] if len(args) > 1 else "moonbeam"
        result = analyze_parachain(source, para)
        print(f"Migration Score: {result['migration_score']}/100 (Grade {result['migration_grade']})")
        print(json.dumps(result, indent=2, default=str))

    elif cmd == "compare":
        print(BANNER)
        source = args[0] if args else "Ethereum"
        print(f"Comparing parachains for migration from {source}:\n")
        result = compare_parachains(source)
        for p in result["parachains"]:
            emoji = "🟢" if p["difficulty"] <= 2 else "🟡"
            print(f"  {emoji} {p['parachain']:<12} TVL: {p['tvl']:>12}  "
                  f"Difficulty: {p['difficulty']}/10  Bridges: {p['bridge_count']}  "
                  f"DEXes: {p['dex_count']}")
        print(f"\nRecommended: {result['recommendation']}")

    elif cmd == "compat":
        print(BANNER)
        if not args:
            print("Usage: polkamigrate.py compat <type1> [type2...]")
            return
        result = check_compatibility(args)
        print(f"Overall: {result['overall']}")
        print(f"Time estimate: {result['estimated_time']}\n")
        for c in result["contracts"]:
            emoji = "✅" if c["compatible"] else "❌"
            print(f"  {emoji} {c['contract_type']:<20} Difficulty: {c['difficulty']}/10")
            print(f"     {c['notes']}")
            if c.get("optimization"):
                print(f"     💡 {c['optimization']}")
            print()

    elif cmd == "report":
        source = args[0] if args else "Ethereum"
        para = args[1] if len(args) > 1 else "moonbeam"
        # Check for --contracts flag
        contracts = None
        for i, a in enumerate(args):
            if a == "--contracts" and i + 1 < len(args):
                contracts = args[i + 1].split(",")
        report = generate_polkadot_report(source, para, contracts)
        print(report)

    elif cmd == "parachains":
        print(BANNER)
        print("Supported Polkadot Parachains:\n")
        for key, p in PARACHAINS.items():
            print(f"  🟣 {p['name']} (ID: {p['parachain_id']})")
            print(f"     Token: {p['native_token']} | EVM: {'✅' if p['evm_compatible'] else '❌'} | "
                  f"Difficulty: {p['difficulty']}/10")
            print(f"     {p['solidity_support']}")
            print()

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
