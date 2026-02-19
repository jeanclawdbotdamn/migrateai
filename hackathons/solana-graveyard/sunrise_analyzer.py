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

import argparse
import json
import sys
import os
import urllib.request
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

def check_ntt_registry(source_chain: str) -> dict:
    """
    Query the real Wormhole NTT registry on GitHub to check deployment status.
    """
    url = (
        "https://raw.githubusercontent.com/wormhole-foundation/"
        "native-token-transfers/main/deployment/deployments.json"
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"ntt_deployed": False, "error": str(e)}

    source_lower = source_chain.lower()
    ntt_managers = []
    mode = None

    try:
        deployments = data if isinstance(data, list) else (
            [{"chain": k, **v} for k, v in data.items()]
            if isinstance(data, dict) else []
        )
        for entry in deployments:
            if source_lower in json.dumps(entry).lower():
                for key in ("nttManager", "ntt_manager", "manager", "managerAddress"):
                    val = entry.get(key)
                    if isinstance(val, str):
                        ntt_managers.append(val)
                    elif isinstance(val, list):
                        ntt_managers.extend(val)
                raw_mode = entry.get("mode", entry.get("transferMode", ""))
                if isinstance(raw_mode, str):
                    if "burn" in raw_mode.lower():
                        mode = "burn-and-mint"
                    elif "lock" in raw_mode.lower():
                        mode = "lock-and-mint"
                    else:
                        mode = raw_mode or None
                return {"ntt_deployed": True, "ntt_managers": ntt_managers, "mode": mode}
    except Exception as e:
        return {"ntt_deployed": False, "error": str(e)}

    return {"ntt_deployed": False, "ntt_managers": [], "mode": None}


def check_sunrise_eligibility(source_chain: str) -> dict:
    """
    Check if a chain's assets can use Wormhole Sunrise to migrate to Solana.
    Now queries the real NTT registry for deployment status.
    """
    source_lower = source_chain.lower()

    # Check Wormhole support
    wormhole_supported = source_lower in [c.lower() for c in CHAIN_IDS.keys()]

    # Check if any bridge supports this → Solana
    bridges = get_available_bridges(source_chain, "Solana")
    has_wormhole = any(b["name"] == "Wormhole" for b in bridges)

    # Real NTT registry check
    ntt_status = check_ntt_registry(source_chain)
    has_ntt = ntt_status.get("ntt_deployed", False)
    sunrise_ready = has_wormhole and has_ntt

    # Eligibility determination
    eligible = has_wormhole  # Basic requirement

    return {
        "source_chain": source_chain,
        "target_chain": "Solana",
        "wormhole_supported": wormhole_supported,
        "has_wormhole_bridge": has_wormhole,
        "has_ntt_support": has_ntt,
        "sunrise_ready": sunrise_ready,
        "eligible": eligible,
        "ntt_registry": ntt_status,
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


def compute_migration_score(feas_score: float, risk_score: float, complexity: float, sunrise: dict) -> int:
    """
    Compute migration score using weighted formula.
    Formula: feas_score*0.3 + (100-risk_score)*0.3 + (100-complexity)*0.2 + bridge_bonus
    Bridge bonus: +15 sunrise, +8 wormhole, +2 any bridge, -10 none.
    """
    if sunrise.get("sunrise_ready"):
        bridge_bonus = 15
    elif sunrise.get("has_wormhole_bridge"):
        bridge_bonus = 8
    elif sunrise.get("bridge_count", 0) > 0:
        bridge_bonus = 2
    else:
        bridge_bonus = -10

    score = (
        feas_score * 0.3 +
        (100 - risk_score) * 0.3 +
        (100 - complexity) * 0.2 +
        bridge_bonus
    )
    return max(0, min(100, int(score)))


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
    complexity_val = complexity.get("complexity_score", 50) if isinstance(complexity, dict) else 50

    migration_score = compute_migration_score(feas_score, risk_score, complexity_val, sunrise)

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


def analyze_with_codegen(chain_name: str, contract_types=None) -> dict:
    """
    Wraps analyze_graveyard_chain and generates Anchor scaffold preview
    for high-scoring chains (grade A or B, score >= 65).
    """
    result = analyze_graveyard_chain(chain_name)
    score = result.get("migration_score", 0)

    if score >= 65:
        project_name = chain_name.lower().replace(" ", "_") + "_migration"
        types = contract_types or ["ERC-20", "Staking"]
        try:
            files = generate_anchor_project(project_name, types, chain_name)
            lib_rs = next((c for p, c in files.items() if p.endswith("lib.rs")), None)
            result["anchor_scaffold_preview"] = "\n".join(
                (lib_rs or "").splitlines()[:50]
            )
            result["codegen_available"] = True
        except Exception as e:
            result["anchor_scaffold_preview"] = f"# Error: {e}"
            result["codegen_available"] = True
    else:
        result["codegen_available"] = False

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


def batch_rank_graveyard(output: str = "markdown") -> list:
    """
    Iterate GRAVEYARD_CANDIDATES, analyze each, sort by migration_score desc,
    return ranked list. Print markdown table or JSON based on output param.
    """
    results = []
    for chain in GRAVEYARD_CANDIDATES:
        try:
            r = analyze_graveyard_chain(chain)
            results.append(r)
        except Exception as e:
            results.append({
                "chain": chain,
                "migration_score": 0,
                "migration_grade": "F",
                "migration_verdict": f"ERROR — {e}",
                "error": str(e),
            })

    results.sort(key=lambda x: x.get("migration_score", 0), reverse=True)

    if output == "json":
        ranked = []
        for i, r in enumerate(results, 1):
            ranked.append({
                "rank": i,
                "chain": r.get("chain"),
                "migration_score": r.get("migration_score", 0),
                "migration_grade": r.get("migration_grade", "?"),
                "migration_verdict": r.get("migration_verdict", ""),
                "sunrise_ready": r.get("sunrise", {}).get("sunrise_ready", False),
                "risk_level": r.get("risk", {}).get("risk_level", "N/A"),
            })
        print(json.dumps(ranked, indent=2))
    else:
        print("# Graveyard Migration Rankings: → Solana\n")
        print("| Rank | Chain | Score | Grade | Sunrise | Verdict |")
        print("|------|-------|-------|-------|---------|---------|")
        for i, r in enumerate(results, 1):
            score = r.get("migration_score", 0)
            grade = r.get("migration_grade", "?")
            verdict = r.get("migration_verdict", "")
            sunrise_ready = r.get("sunrise", {}).get("sunrise_ready", False)
            sunrise_cell = "✅" if sunrise_ready else "❌"
            emoji = "🟢" if score >= 65 else "🟡" if score >= 45 else "🔴"
            print(f"| {i} | {emoji} {r.get('chain', '?')} | {score}/100 | {grade} | {sunrise_cell} | {verdict} |")

    return results


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
    print(BANNER)

    parser = argparse.ArgumentParser(
        prog="sunrise_analyzer.py",
        description="Sunrise Migration Analyzer — MigrateAI × Solana Graveyard Hack 2026",
    )
    parser.add_argument(
        "--output", choices=["json", "markdown"], default="markdown",
        help="Output format (default: markdown)",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="<command>")

    # scan
    scan_parser = subparsers.add_parser("scan", help="Scan for dying chains")
    scan_parser.add_argument(
        "--threshold", type=float, default=-10.0,
        help="TVL decline threshold in percent (default: -10.0)",
    )
    scan_parser.add_argument(
        "--min-tvl", type=float, default=500_000,
        help="Minimum TVL in USD (default: 500000)",
    )

    # analyze
    analyze_parser = subparsers.add_parser("analyze", help="Full migration analysis for a chain")
    analyze_parser.add_argument("chain", help="Source chain name")
    analyze_parser.add_argument("project", nargs="?", default=None, help="Project name (optional)")

    # batch
    subparsers.add_parser("batch", help="Analyze all graveyard candidates and rank them")

    # codegen
    codegen_parser = subparsers.add_parser("codegen", help="Generate Anchor project scaffold")
    codegen_parser.add_argument("name", help="Project name")
    codegen_parser.add_argument("types", nargs="+", help="Contract types (e.g. AMM ERC-20 Staking)")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    output_fmt = args.output

    if args.command == "scan":
        dying = scan_graveyard(args.threshold, args.min_tvl)
        if output_fmt == "json":
            print(json.dumps(dying, indent=2, default=str))
        else:
            if dying:
                print(f"{'#':<4} {'Chain':<20} {'TVL':>12} {'30d Change':>12} {'Bridges':>8} {'Sunrise':>8}")
                print("-" * 68)
                for i, d in enumerate(dying[:25], 1):
                    sunrise_cell = "✅" if d["sunrise_eligible"] else "❌"
                    print(f"{i:<4} {d['chain']:<20} {d['tvl_formatted']:>12} {d['tvl_change_30d']:>+10.1f}% {d['bridge_count']:>8} {sunrise_cell:>8}")

    elif args.command == "analyze":
        chain = args.chain
        print(f"🔬 Analyzing {chain} → Solana migration...\n")
        result = analyze_graveyard_chain(chain)
        if output_fmt == "json":
            print(json.dumps(result, indent=2, default=str))
        else:
            print(f"Migration Score: {result['migration_score']}/100 (Grade {result['migration_grade']})")
            print(f"Verdict: {result['migration_verdict']}")
            print()
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

    elif args.command == "batch":
        batch_rank_graveyard(output=output_fmt)

    elif args.command == "codegen":
        name = args.name
        types = args.types
        files = generate_anchor_project(name, types, "EVM")
        print(f"Generated {len(files)} files for '{name}':")
        for path in sorted(files.keys()):
            lines = files[path].count('\n') + 1
            print(f"  📄 {path} ({lines} lines)")
        out_dir = os.path.join(ROOT, "generated", name)
        for path, content in files.items():
            full_path = os.path.join(out_dir, path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)
        print(f"\n✅ Written to {out_dir}/")


if __name__ == "__main__":
    main()
