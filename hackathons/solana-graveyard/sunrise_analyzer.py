#!/usr/bin/env python3
"""
Sunrise Migration Analyzer — Solana Graveyard Hack (Migrations/Sunrise Track)

Identifies dying chains and analyzes migration feasibility to Solana
via Wormhole Sunrise/NTT. Built on the MigrateAI core engine.

Features:
  1. Dying Chain Scanner — finds chains with declining TVL (migration candidates)
  2. Sunrise Feasibility Check — can this chain's assets onboard to Solana via NTT?
  3. Full Migration Report — chain comparison, bridge risk, contract analysis, playbook
  4. Anchor Code Generation — scaffold for migrated Solana programs
  5. Batch Analysis — scan and rank all declining chains by migration feasibility

Solana Graveyard Hack Context:
  The "Graveyard" = dead/dying blockchain projects
  "Sunrise" = Wormhole's canonical route for external assets to enter Solana
  with day-one liquidity via NTT (Native Token Transfer)
  Launched Nov 2025 with Monad's MON as first token.
"""

import json
import sys
import os
from datetime import datetime

# Add project root
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from apis.defillama import (
    get_all_chains, get_chain_health, compare_chains,
    get_all_protocols, get_protocols_by_chain,
)
from apis.wormhole import (
    get_scorecards, get_token_bridge_support, assess_bridge_risk,
    CHAIN_IDS,
)
from core.chain_health import full_chain_comparison, scan_dying_chains
from core.risk_scorer import compute_migration_risk, get_contract_complexity
from core.token_analysis import (
    analyze_token_migration, get_available_bridges, get_dex_ecosystem,
    BRIDGE_PROTOCOLS,
)
from core.contract_analyzer import (
    estimate_project_complexity, EVM_TO_SOLANA_PATTERNS,
)
from core.playbook import generate_playbook
from core.codegen import generate_anchor_project


# ─────────────────────────────────────────────────────────────────────────────
# Wormhole Sunrise / NTT specifics
# ─────────────────────────────────────────────────────────────────────────────

SUNRISE_INFO = {
    "description": (
        "Wormhole Sunrise is the canonical route for external assets to enter "
        "Solana with day-one liquidity. It uses NTT (Native Token Transfers) — "
        "a framework for burn-and-mint token bridging that preserves token "
        "fungibility across chains."
    ),
    "launched": "November 2025",
    "first_token": "MON (Monad)",
    "docs": "https://wormhole.com/docs/products/token-transfers/native-token-transfers/",
    "github": "https://github.com/wormhole-foundation/native-token-transfers",
    "benefits": [
        "Canonical (official) token representation on Solana",
        "Day-one liquidity via Wormhole's existing pools",
        "No wrapped token fragmentation",
        "Rate limiting built into the NTT framework",
        "Supported by major Solana DEXes (Jupiter, Raydium, Orca)",
    ],
    "requirements": [
        "Token must exist on a Wormhole-supported source chain",
        "Deploy NTT Manager program on both source and Solana",
        "Configure burn-and-mint or lock-and-mint mode",
        "Set up rate limits for bridge transfers",
        "Register token on Solana token registry",
    ],
}

# Chains known to be in the Wormhole "graveyard" (declining + Wormhole-supported)
GRAVEYARD_CANDIDATES = [
    "Fantom", "Harmony", "Klaytn", "Celo", "Cronos",
    "Moonbeam", "Moonriver", "Boba", "Metis", "Gnosis",
    "Aurora", "Fuse", "Velas", "Oasis", "IoTeX",
]


# ─────────────────────────────────────────────────────────────────────────────
# Sunrise-specific analysis
# ─────────────────────────────────────────────────────────────────────────────

def check_sunrise_eligibility(source_chain: str) -> dict:
    """
    Check if a chain's assets can use Wormhole Sunrise to migrate to Solana.
    """
    source_lower = source_chain.lower()

    # Check Wormhole support
    wormhole_supported = source_lower in [c.lower() for c in CHAIN_IDS.keys()]

    # Check if any bridge supports this → Solana
    bridges = get_available_bridges(source_chain, "Solana")
    has_wormhole = any(b["name"] == "Wormhole" for b in bridges)
    has_ntt = any(b.get("ntt_support") for b in bridges)
    has_sunrise = any(b.get("sunrise_support") for b in bridges)

    # Eligibility determination
    eligible = has_wormhole  # Basic requirement
    sunrise_ready = has_sunrise and has_ntt

    return {
        "source_chain": source_chain,
        "target_chain": "Solana",
        "wormhole_supported": wormhole_supported,
        "has_wormhole_bridge": has_wormhole,
        "has_ntt_support": has_ntt,
        "sunrise_ready": sunrise_ready,
        "eligible": eligible,
        "available_bridges": bridges,
        "bridge_count": len(bridges),
        "recommendation": (
            "✅ SUNRISE READY — Use Wormhole NTT for canonical asset onboarding"
            if sunrise_ready else
            "⚠️ WORMHOLE AVAILABLE — NTT deployment needed for Sunrise"
            if has_wormhole else
            "🟡 BRIDGE AVAILABLE — Use alternative bridge (not Sunrise)"
            if bridges else
            "❌ NO BRIDGE — Custom bridge or intermediary chain required"
        ),
        "sunrise_info": SUNRISE_INFO if sunrise_ready or has_wormhole else None,
    }


def analyze_graveyard_chain(chain_name: str) -> dict:
    """
    Full graveyard-to-Solana analysis for a single chain.
    Combines: chain health, Sunrise eligibility, migration risk, token analysis.
    """
    result = {
        "chain": chain_name,
        "target": "Solana",
        "analyzed_at": datetime.utcnow().isoformat() + "Z",
        "analyzer": "MigrateAI Sunrise Analyzer v0.1",
    }

    # 1. Chain health
    health = get_chain_health(chain_name)
    result["chain_health"] = health

    # 2. Chain comparison vs Solana
    comparison = full_chain_comparison(chain_name, "Solana")
    result["comparison"] = comparison

    # 3. Sunrise eligibility
    sunrise = check_sunrise_eligibility(chain_name)
    result["sunrise"] = sunrise

    # 4. Risk assessment
    risk = compute_migration_risk(chain_name, "Solana")
    result["risk"] = risk

    # 5. Token migration
    tokens = analyze_token_migration(chain_name, "Solana", f"{chain_name} Token")
    result["token_analysis"] = tokens

    # 6. Migration complexity
    complexity = get_contract_complexity(chain_name, "Solana")
    result["complexity"] = complexity

    # 7. Solana DEX ecosystem (what awaits on the other side)
    result["solana_ecosystem"] = get_dex_ecosystem("Solana")

    # Overall migration score (0-100)
    feas_score = comparison.get("feasibility_score", 50) if "feasibility_score" in comparison else 50
    risk_score = risk.get("overall_risk_score", 50)
    bridge_bonus = 10 if sunrise.get("sunrise_ready") else 5 if sunrise.get("has_wormhole_bridge") else -10

    migration_score = max(0, min(100, int(
        feas_score * 0.4 +
        (100 - risk_score) * 0.4 +
        bridge_bonus +
        (10 if health.get("tvl_trend") == "declining" else 0)
    )))

    result["migration_score"] = migration_score
    result["migration_grade"] = (
        "A" if migration_score >= 80 else
        "B" if migration_score >= 65 else
        "C" if migration_score >= 45 else
        "D" if migration_score >= 30 else "F"
    )
    result["migration_verdict"] = (
        "STRONG — Migrate via Sunrise" if migration_score >= 65 else
        "MODERATE — Migration viable but consider costs" if migration_score >= 45 else
        "WEAK — Migration challenging, evaluate carefully"
    )

    return result


def scan_graveyard(threshold_pct: float = -5.0, min_tvl: float = 500_000) -> list:
    """
    Scan for dying chains and rank by Solana migration feasibility.
    This is the core "Graveyard Scanner" feature.

    Args:
        threshold_pct: TVL decline threshold (default -5%)
        min_tvl: Minimum TVL to consider (default $500K)

    Returns:
        List of chains sorted by migration score (best candidates first)
    """
    print("🪦 Scanning the blockchain graveyard...")
    print(f"   Threshold: {threshold_pct}% TVL decline, min TVL: ${min_tvl/1000:.0f}K\n")

    # Get all chains
    chains = get_all_chains()
    if isinstance(chains, dict) and "error" in chains:
        return [{"error": "Failed to fetch chain data"}]

    # Filter by TVL
    candidates = [c for c in chains if (c.get("tvl", 0) or 0) >= min_tvl]
    print(f"   Found {len(candidates)} chains with TVL >= ${min_tvl/1000:.0f}K")

    # Check health for each candidate
    dying = []
    for i, chain in enumerate(candidates):
        name = chain.get("name", "Unknown")
        health = get_chain_health(name)
        if isinstance(health, dict) and health.get("tvl_change_30d_pct", 0) < threshold_pct:
            # Check Sunrise eligibility (fast — no API call)
            bridges = get_available_bridges(name, "Solana")
            has_wormhole = any(b["name"] == "Wormhole" for b in bridges)

            dying.append({
                "chain": name,
                "tvl": health.get("tvl", 0),
                "tvl_formatted": health.get("tvl_formatted", "?"),
                "tvl_change_30d": health.get("tvl_change_30d_pct", 0),
                "trend": health.get("tvl_trend", "unknown"),
                "protocol_count": health.get("protocol_count", 0),
                "wormhole_supported": has_wormhole,
                "bridge_count": len(bridges),
                "sunrise_eligible": has_wormhole,
            })

        # Progress
        if (i + 1) % 20 == 0:
            print(f"   Scanned {i+1}/{len(candidates)} chains...")

    # Sort by TVL decline (worst first)
    dying.sort(key=lambda x: x["tvl_change_30d"])

    print(f"\n🪦 Found {len(dying)} dying chains")
    print(f"☀️  {sum(1 for d in dying if d['sunrise_eligible'])} are Sunrise-eligible\n")

    return dying


def generate_sunrise_report(source_chain: str, project_name: str = None) -> str:
    """
    Generate a comprehensive Sunrise migration report for a specific chain.
    Formatted for the Graveyard Hack submission.
    """
    if not project_name:
        project_name = f"{source_chain} Ecosystem"

    analysis = analyze_graveyard_chain(source_chain)
    health = analysis.get("chain_health", {})
    comparison = analysis.get("comparison", {})
    sunrise = analysis.get("sunrise", {})
    risk = analysis.get("risk", {})
    tokens = analysis.get("token_analysis", {})
    complexity = analysis.get("complexity", {})
    sol_eco = analysis.get("solana_ecosystem", {})

    src = comparison.get("source_chain", health)
    tgt = comparison.get("target_chain", {})

    report = f"""# ☀️ Sunrise Migration Report: {source_chain} → Solana
## {project_name}
*Generated by MigrateAI Sunrise Analyzer — Solana Graveyard Hack 2026*

---

## 📊 Executive Summary

| Metric | Value |
|--------|-------|
| **Migration Score** | **{analysis['migration_score']}/100 (Grade {analysis['migration_grade']})** |
| **Verdict** | {analysis['migration_verdict']} |
| **Feasibility** | {comparison.get('feasibility_grade', 'N/A')} ({comparison.get('feasibility_score', 'N/A')}/100) |
| **Risk Level** | {risk.get('risk_level', 'N/A')} ({risk.get('overall_risk_score', 'N/A')}/100) |
| **Complexity** | {complexity.get('difficulty_level', 'N/A')} ({complexity.get('estimated_weeks', 'N/A')} weeks) |
| **Sunrise Eligible** | {'✅ Yes' if sunrise.get('sunrise_ready') or sunrise.get('has_wormhole_bridge') else '❌ No'} |

---

## 🪦 Source Chain: {source_chain}

| Metric | Value |
|--------|-------|
| TVL | {src.get('tvl_formatted', 'N/A')} |
| Protocols | {src.get('protocol_count', 'N/A')} |
| 30-day TVL Change | {src.get('tvl_change_30d_pct', 0):.1f}% |
| Trend | **{src.get('tvl_trend', 'N/A').upper()}** |

### Why Migrate?
"""
    for reason in comparison.get("migration_reasons", []):
        report += f"- {reason}\n"

    report += f"""
---

## ☀️ Sunrise / Wormhole NTT Analysis

**Status**: {sunrise.get('recommendation', 'Unknown')}

### Available Bridges ({sunrise.get('bridge_count', 0)})
"""
    for bridge in sunrise.get("available_bridges", []):
        risk_emoji = "🟢" if bridge["risk_score"] < 20 else "🟡" if bridge["risk_score"] < 35 else "🔴"
        ntt_tag = " [NTT/Sunrise]" if bridge.get("sunrise_support") else ""
        report += f"- {risk_emoji} **{bridge['name']}** ({bridge['type']}){ntt_tag} — Risk: {bridge['risk_score']}\n"

    if sunrise.get("sunrise_ready") or sunrise.get("has_wormhole_bridge"):
        report += f"""
### What is Wormhole Sunrise?
{SUNRISE_INFO['description']}

**Launched**: {SUNRISE_INFO['launched']} (first token: {SUNRISE_INFO['first_token']})

#### Benefits
"""
        for b in SUNRISE_INFO["benefits"]:
            report += f"- {b}\n"

        report += "\n#### Requirements\n"
        for r in SUNRISE_INFO["requirements"]:
            report += f"- {r}\n"

    report += f"""
---

## ☀️ Target: Solana

| Metric | Value |
|--------|-------|
| TVL | {tgt.get('tvl_formatted', 'N/A')} |
| Protocols | {tgt.get('protocol_count', 'N/A')} |
| DEXes | {', '.join(sol_eco.get('known_dexes', [])[:5])} |
| Stablecoins | {', '.join(sol_eco.get('stablecoins', [])[:4])} |
| Liquidity | **{sol_eco.get('liquidity_rating', 'N/A')}** |

---

## ⚠️ Risk Assessment: {risk.get('risk_level', 'N/A')} ({risk.get('overall_risk_score', 'N/A')}/100)

### Risk Breakdown
"""
    for category, details in risk.get("breakdown", {}).items():
        report += f"- **{category.replace('_', ' ').title()}**: {details.get('score', 'N/A')}/100 — {details.get('note', '')}\n"

    report += "\n### Key Challenges\n"
    for ch in risk.get("challenges", []):
        sev_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(ch["severity"], "⚪")
        report += f"\n#### {sev_emoji} {ch['issue']} ({ch['severity']})\n{ch['detail']}\n"

    report += f"""
---

## 🪙 Token Migration Strategy

**Recommended**: {tokens.get('recommended_strategy', {}).get('strategy', 'N/A')}
**Bridge**: {tokens.get('recommended_strategy', {}).get('bridge', 'N/A')}
**Complexity**: {tokens.get('migration_complexity', 'N/A')}

### Liquidity Bootstrapping Plan
"""
    for i, step in enumerate(tokens.get("liquidity_plan", []), 1):
        report += f"{i}. {step}\n"

    # Playbook summary
    report += f"""
---

## 📋 Migration Phases

1. **Assessment** (Week 1-2): Audit contracts, research Solana account model, confirm NTT support
2. **Development** (Week 2-{complexity.get('estimated_weeks', '16').split('-')[-1]}): {'Rewrite Solidity → Anchor/Rust' if complexity.get('requires_rewrite') else 'Port contracts'}, implement CPI, test on devnet
3. **Token Bridge** (Week {complexity.get('estimated_weeks', '8-16').split('-')[-1]}+): Deploy NTT Manager, seed liquidity on Jupiter/Raydium, migrate users
4. **Launch**: Mainnet deployment, monitoring, source chain sunset

---

## 🔗 Resources

- [Wormhole NTT Docs]({SUNRISE_INFO['docs']})
- [Wormhole NTT GitHub]({SUNRISE_INFO['github']})
- [Solana Developer Docs](https://solana.com/developers)
- [Anchor Framework](https://www.anchor-lang.com/)
- [Jupiter Aggregator](https://jup.ag/) — Primary Solana DEX aggregator
- [DeFi Llama](https://defillama.com/) — Chain TVL data
- [WormholeScan](https://wormholescan.io/) — Bridge explorer

---

*Generated by MigrateAI Sunrise Analyzer v0.1*
*Built for the Solana Graveyard Hack 2026 — Migrations/Sunrise Track*
*https://github.com/jeanclawdbotdamn/migrateai*
"""
    return report


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

BANNER = """
╔══════════════════════════════════════════════════╗
║  ☀️  Sunrise Migration Analyzer v0.1              ║
║  MigrateAI × Solana Graveyard Hack 2026          ║
║  github.com/jeanclawdbotdamn/migrateai            ║
╚══════════════════════════════════════════════════╝
"""


def main():
    if len(sys.argv) < 2:
        print(BANNER)
        print("Usage:")
        print("  python sunrise_analyzer.py scan                        — Scan for dying chains")
        print("  python sunrise_analyzer.py scan --threshold -15        — Custom decline threshold")
        print("  python sunrise_analyzer.py check <chain>               — Check Sunrise eligibility")
        print("  python sunrise_analyzer.py analyze <chain> [project]   — Full migration analysis")
        print("  python sunrise_analyzer.py report <chain> [project]    — Generate Sunrise report")
        print("  python sunrise_analyzer.py codegen <name> <types...>   — Generate Anchor project")
        print("  python sunrise_analyzer.py batch                       — Analyze all graveyard candidates")
        print()
        print("Examples:")
        print("  python sunrise_analyzer.py scan")
        print("  python sunrise_analyzer.py check Fantom")
        print("  python sunrise_analyzer.py analyze Fantom SpookySwap")
        print("  python sunrise_analyzer.py report Fantom SpookySwap > report.md")
        print("  python sunrise_analyzer.py codegen spooky_swap AMM ERC-20 Staking")
        return

    cmd = sys.argv[1].lower()
    args = sys.argv[2:]

    if cmd == "scan":
        print(BANNER)
        threshold = -10.0
        for i, a in enumerate(args):
            if a == "--threshold" and i + 1 < len(args):
                threshold = float(args[i + 1])

        dying = scan_graveyard(threshold)
        if dying:
            print(f"{'#':<4} {'Chain':<20} {'TVL':>12} {'30d Change':>12} {'Bridges':>8} {'Sunrise':>8}")
            print("-" * 68)
            for i, d in enumerate(dying[:25], 1):
                sunrise = "✅" if d["sunrise_eligible"] else "❌"
                print(f"{i:<4} {d['chain']:<20} {d['tvl_formatted']:>12} {d['tvl_change_30d']:>+10.1f}% {d['bridge_count']:>8} {sunrise:>8}")

    elif cmd == "check":
        print(BANNER)
        if not args:
            print("Usage: sunrise_analyzer.py check <chain>")
            return
        result = check_sunrise_eligibility(args[0])
        print(json.dumps(result, indent=2, default=str))

    elif cmd == "analyze":
        print(BANNER)
        if not args:
            print("Usage: sunrise_analyzer.py analyze <chain> [project]")
            return
        chain = args[0]
        project = args[1] if len(args) > 1 else None
        print(f"🔬 Analyzing {chain} → Solana migration...\n")
        result = analyze_graveyard_chain(chain)
        print(f"Migration Score: {result['migration_score']}/100 (Grade {result['migration_grade']})")
        print(f"Verdict: {result['migration_verdict']}")
        print(f"\nFull JSON:")
        # Print select fields to keep output manageable
        summary = {
            "chain": result["chain"],
            "migration_score": result["migration_score"],
            "migration_grade": result["migration_grade"],
            "migration_verdict": result["migration_verdict"],
            "chain_tvl": result.get("chain_health", {}).get("tvl_formatted"),
            "chain_trend": result.get("chain_health", {}).get("tvl_trend"),
            "sunrise_eligible": result.get("sunrise", {}).get("eligible"),
            "risk_level": result.get("risk", {}).get("risk_level"),
            "complexity": result.get("complexity", {}).get("difficulty_level"),
            "bridges": result.get("sunrise", {}).get("bridge_count"),
        }
        print(json.dumps(summary, indent=2))

    elif cmd == "report":
        if not args:
            print("Usage: sunrise_analyzer.py report <chain> [project]", file=sys.stderr)
            return
        chain = args[0]
        project = args[1] if len(args) > 1 else None
        report = generate_sunrise_report(chain, project)
        print(report)

    elif cmd == "codegen":
        print(BANNER)
        if len(args) < 2:
            print("Usage: sunrise_analyzer.py codegen <name> <type1> [type2...]")
            return
        name = args[0]
        types = args[1:]
        files = generate_anchor_project(name, types, "EVM")
        print(f"Generated {len(files)} files for '{name}':")
        for path in sorted(files.keys()):
            lines = files[path].count('\n') + 1
            print(f"  📄 {path} ({lines} lines)")
        # Write files
        out_dir = os.path.join(ROOT, "generated", name)
        for path, content in files.items():
            full_path = os.path.join(out_dir, path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)
        print(f"\n✅ Written to {out_dir}/")

    elif cmd == "batch":
        print(BANNER)
        print("🔬 Batch analyzing known graveyard candidates...\n")
        results = []
        for chain in GRAVEYARD_CANDIDATES:
            try:
                r = analyze_graveyard_chain(chain)
                results.append(r)
                print(f"  {chain}: Score {r['migration_score']}/100 ({r['migration_grade']})")
            except Exception as e:
                print(f"  {chain}: ERROR — {e}")

        results.sort(key=lambda x: x.get("migration_score", 0), reverse=True)
        print(f"\n{'='*60}")
        print("RANKED BY MIGRATION FEASIBILITY TO SOLANA:")
        print(f"{'='*60}")
        for i, r in enumerate(results, 1):
            grade = r.get("migration_grade", "?")
            score = r.get("migration_score", 0)
            emoji = "🟢" if score >= 65 else "🟡" if score >= 45 else "🔴"
            print(f"  {i}. {emoji} {r['chain']}: {score}/100 (Grade {grade}) — {r.get('migration_verdict', '')}")

    else:
        print(f"Unknown command: {cmd}")
        print("Run without arguments for help.")


if __name__ == "__main__":
    main()
