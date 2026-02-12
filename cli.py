#!/usr/bin/env python3
"""MigrateAI CLI — AI-Powered Cross-Chain Migration Analyzer."""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.chain_health import full_chain_comparison, generate_chain_report, scan_dying_chains
from core.risk_scorer import compute_migration_risk, get_contract_complexity
from core.playbook import generate_playbook
from core.token_analysis import generate_token_report, analyze_token_migration
from core.contract_analyzer import generate_contract_report, estimate_project_complexity
from apis.defillama import get_all_chains, get_all_bridges
from apis.wormhole import get_scorecards


BANNER = """
╔══════════════════════════════════════════════╗
║  🦀 MigrateAI v0.1                          ║
║  AI-Powered Cross-Chain Migration Analyzer   ║
║  github.com/jeanclawdbotdamn/migrateai       ║
╚══════════════════════════════════════════════╝
"""


def cmd_analyze(source: str, target: str, project: str = "Your Project"):
    """Full migration analysis with playbook."""
    print(BANNER)
    print(f"Analyzing migration: {source} → {target}")
    print("Fetching chain data from DeFi Llama + WormholeScan...\n")

    playbook = generate_playbook(source, target, project)
    print(playbook)


def cmd_compare(source: str, target: str):
    """Quick chain comparison."""
    print(BANNER)
    print(f"Comparing: {source} vs {target}\n")
    report = generate_chain_report(source, target)
    print(report)


def cmd_risk(source: str, target: str):
    """Risk assessment only."""
    print(BANNER)
    print(f"Risk assessment: {source} → {target}\n")
    risk = compute_migration_risk(source, target)
    print(json.dumps(risk, indent=2))


def cmd_chains():
    """List top chains by TVL."""
    print(BANNER)
    chains = get_all_chains()
    if isinstance(chains, dict) and "error" in chains:
        print(f"Error: {chains['error']}")
        return

    print(f"Top 20 chains by TVL (of {len(chains)} tracked):\n")
    sorted_chains = sorted(chains, key=lambda x: x.get("tvl", 0), reverse=True)[:20]
    print(f"{'#':<4} {'Chain':<20} {'TVL':>15} {'Symbol':>8}")
    print("-" * 50)
    for i, c in enumerate(sorted_chains, 1):
        tvl = c.get("tvl", 0)
        tvl_str = f"${tvl/1e9:.2f}B" if tvl >= 1e9 else f"${tvl/1e6:.1f}M"
        print(f"{i:<4} {c.get('name', 'N/A'):<20} {tvl_str:>15} {(c.get('tokenSymbol') or ''):>8}")


def cmd_bridges():
    """List top bridges by volume."""
    print(BANNER)
    bridges = get_all_bridges()
    if isinstance(bridges, dict) and "error" in bridges:
        print(f"Error: {bridges['error']}")
        return

    print(f"Top 15 bridges by daily volume (of {len(bridges)} tracked):\n")
    sorted_bridges = sorted(bridges, key=lambda x: x.get("lastDailyVolume", 0), reverse=True)[:15]
    print(f"{'#':<4} {'Bridge':<25} {'Daily Volume':>15}")
    print("-" * 48)
    for i, b in enumerate(sorted_bridges, 1):
        vol = b.get("lastDailyVolume", 0)
        vol_str = f"${vol/1e6:.1f}M" if vol >= 1e6 else f"${vol/1e3:.0f}K"
        name = b.get("displayName", b.get("name", "N/A"))
        print(f"{i:<4} {name:<25} {vol_str:>15}")


def cmd_dying():
    """Find chains with declining TVL."""
    print(BANNER)
    print("Scanning for declining chains (>10% TVL drop in 30 days)...\n")
    print("⚠️  This takes ~60s due to API calls per chain.\n")
    dying = scan_dying_chains(-10.0)
    if not dying:
        print("No significantly declining chains found.")
        return

    print(f"Found {len(dying)} declining chains:\n")
    for c in dying[:15]:
        print(f"  📉 {c['chain']}: {c['tvl_formatted']} ({c['tvl_change_30d_pct']:.1f}% 30d)")


def cmd_tokens(source: str, target: str, token: str = "Project Token"):
    """Token migration analysis."""
    print(BANNER)
    print(f"Token analysis: {token} ({source} → {target})\n")
    report = generate_token_report(source, target, token)
    print(report)


def cmd_contracts(*contract_types):
    """Contract pattern analysis."""
    print(BANNER)
    print(f"Analyzing contract patterns: {', '.join(contract_types)}\n")
    report = generate_contract_report(list(contract_types))
    print(report)


def cmd_full(source: str, target: str, project: str = "Your Project", contracts: list = None):
    """Full analysis: chain comparison + risk + tokens + contracts + playbook."""
    print(BANNER)
    print(f"🔬 FULL MIGRATION ANALYSIS: {project}")
    print(f"   {source} → {target}")
    print("=" * 60)

    print("\n📊 CHAIN COMPARISON\n")
    report = generate_chain_report(source, target)
    print(report)

    print("\n⚠️  RISK ASSESSMENT\n")
    risk = compute_migration_risk(source, target)
    print(f"Overall Risk: {risk.get('risk_level', 'N/A')} ({risk.get('overall_risk_score', 'N/A')}/100)")
    for c in risk.get("challenges", []):
        print(f"  {'🔴' if c['severity'] == 'HIGH' else '🟡'} [{c['severity']}] {c['issue']}")

    print("\n🪙 TOKEN MIGRATION\n")
    token_report = generate_token_report(source, target, project)
    print(token_report)

    if contracts:
        print("\n📝 CONTRACT ANALYSIS\n")
        contract_report = generate_contract_report(contracts, source, target)
        print(contract_report)

    print("\n📋 MIGRATION PLAYBOOK\n")
    playbook = generate_playbook(source, target, project)
    print(playbook)


def cmd_network():
    """Wormhole network status."""
    print(BANNER)
    print("Wormhole Network Status:\n")
    sc = get_scorecards()
    if isinstance(sc, dict) and "error" not in sc:
        print(f"  Total Volume:    ${float(sc.get('total_volume', 0))/1e9:.1f}B")
        print(f"  TVL Locked:      ${float(sc.get('tvl', 0))/1e9:.2f}B")
        print(f"  24h Volume:      ${float(sc.get('24h_volume', 0))/1e6:.1f}M")
        print(f"  24h Messages:    {int(sc.get('24h_messages', 0)):,}")
        print(f"  Total Messages:  {int(sc.get('total_messages', 0)):,}")
        print(f"  Total TX Count:  {int(sc.get('total_tx_count', 0)):,}")
    else:
        print(f"Error fetching data: {sc}")


def main():
    if len(sys.argv) < 2:
        print(BANNER)
        print("Usage:")
        print("  python cli.py analyze <source> <target> [project_name]  — Full migration playbook")
        print("  python cli.py compare <source> <target>                 — Quick chain comparison")
        print("  python cli.py risk <source> <target>                    — Risk assessment")
        print("  python cli.py tokens <source> <target> [token_name]     — Token migration analysis")
        print("  python cli.py contracts <type1> [type2] ...             — Contract pattern analysis")
        print("  python cli.py full <source> <target> [project] [--contracts type1,type2]")
        print("                                                          — Complete analysis")
        print("  python cli.py chains                                    — List top chains by TVL")
        print("  python cli.py bridges                                   — List top bridges")
        print("  python cli.py dying                                     — Find declining chains")
        print("  python cli.py network                                   — Wormhole network status")
        print()
        print("Examples:")
        print("  python cli.py analyze Fantom Solana 'SpookySwap'")
        print("  python cli.py compare Ethereum Solana")
        print("  python cli.py tokens Fantom Solana FTM")
        print("  python cli.py contracts AMM ERC-20 Staking Oracle")
        print("  python cli.py full Fantom Solana SpookySwap --contracts AMM,ERC-20,Staking")
        return

    cmd = sys.argv[1].lower()
    args = sys.argv[2:]

    if cmd == "analyze" and len(args) >= 2:
        cmd_analyze(args[0], args[1], args[2] if len(args) > 2 else "Your Project")
    elif cmd == "compare" and len(args) >= 2:
        cmd_compare(args[0], args[1])
    elif cmd == "risk" and len(args) >= 2:
        cmd_risk(args[0], args[1])
    elif cmd == "tokens" and len(args) >= 2:
        cmd_tokens(args[0], args[1], args[2] if len(args) > 2 else "Project Token")
    elif cmd == "contracts" and len(args) >= 1:
        cmd_contracts(*args)
    elif cmd == "full" and len(args) >= 2:
        project = args[2] if len(args) > 2 and not args[2].startswith("--") else "Your Project"
        contracts = None
        for a in args:
            if a.startswith("--contracts"):
                idx = args.index(a)
                if "=" in a:
                    contracts = a.split("=")[1].split(",")
                elif idx + 1 < len(args):
                    contracts = args[idx + 1].split(",")
        cmd_full(args[0], args[1], project, contracts)
    elif cmd == "chains":
        cmd_chains()
    elif cmd == "bridges":
        cmd_bridges()
    elif cmd == "dying":
        cmd_dying()
    elif cmd == "network":
        cmd_network()
    else:
        print(f"Unknown command or missing arguments: {cmd}")
        print("Run without arguments for help.")


if __name__ == "__main__":
    main()
