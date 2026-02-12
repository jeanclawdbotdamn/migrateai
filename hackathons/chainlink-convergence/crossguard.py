#!/usr/bin/env python3
"""
CrossGuard: AI Migration Monitor — Chainlink Convergence (CRE & AI Track)

A Chainlink Runtime Environment (CRE) workflow concept that monitors
cross-chain bridge activity and assesses migration risk in real-time.

Chainlink Convergence Context:
  CRE (Chainlink Runtime Environment) = orchestration layer for
  blockchain + external API workflows. TypeScript-based.
  Track: "CRE & AI" ($17K) — "AI agents consuming CRE workflows"
  Also fits: "Risk & Compliance" ($16K)

This module provides:
  1. Migration Risk Monitor — real-time chain health + bridge monitoring
  2. CRE Workflow Spec — the workflow definition for Chainlink CRE
  3. Alert Engine — configurable thresholds for migration signals
  4. Risk Dashboard Data — JSON feed for monitoring dashboards
"""

import json
import sys
import os
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from apis.defillama import get_all_chains, get_chain_health, compare_chains
from apis.wormhole import get_scorecards, assess_bridge_risk, get_top_chain_pairs
from core.chain_health import full_chain_comparison
from core.risk_scorer import compute_migration_risk, BRIDGE_INCIDENTS
from core.token_analysis import get_available_bridges


# ─────────────────────────────────────────────────────────────────────────────
# CRE Workflow Definition
# ─────────────────────────────────────────────────────────────────────────────

CRE_WORKFLOW = {
    "name": "crossguard-migration-monitor",
    "version": "0.1.0",
    "description": (
        "AI-powered cross-chain migration risk monitor. Monitors chain health, "
        "bridge activity, and generates migration alerts using Chainlink CRE."
    ),
    "triggers": [
        {
            "type": "schedule",
            "schedule": "*/30 * * * *",  # Every 30 minutes
            "description": "Periodic chain health check",
        },
        {
            "type": "on-chain-event",
            "description": "Bridge large transfer event",
            "chains": ["ethereum", "solana", "arbitrum", "base"],
        },
    ],
    "steps": [
        {
            "id": "fetch_chain_data",
            "type": "external_api",
            "config": {
                "url": "https://api.llama.fi/v2/chains",
                "method": "GET",
                "description": "Fetch TVL data for all chains from DeFi Llama",
            },
        },
        {
            "id": "fetch_bridge_data",
            "type": "external_api",
            "config": {
                "url": "https://api.wormholescan.io/api/v1/scorecards",
                "method": "GET",
                "description": "Fetch Wormhole bridge health metrics",
            },
        },
        {
            "id": "analyze_risk",
            "type": "compute",
            "config": {
                "description": "AI risk analysis — composite scoring from chain health + bridge data",
                "inputs": ["fetch_chain_data.output", "fetch_bridge_data.output"],
                "logic": "MigrateAI risk scoring engine (chain risk + bridge risk + code complexity + historical incidents)",
            },
        },
        {
            "id": "check_thresholds",
            "type": "condition",
            "config": {
                "description": "Check if any monitored chain has crossed alert thresholds",
                "conditions": [
                    {"metric": "tvl_change_30d", "operator": "lt", "value": -15, "severity": "HIGH"},
                    {"metric": "tvl_change_30d", "operator": "lt", "value": -10, "severity": "MEDIUM"},
                    {"metric": "bridge_risk_score", "operator": "gt", "value": 50, "severity": "HIGH"},
                    {"metric": "protocol_count_change", "operator": "lt", "value": -5, "severity": "MEDIUM"},
                ],
            },
        },
        {
            "id": "generate_alert",
            "type": "compute",
            "config": {
                "description": "Generate migration alert with AI recommendation",
                "depends_on": "check_thresholds",
                "only_if": "thresholds_breached",
            },
        },
        {
            "id": "publish_alert",
            "type": "on-chain-action",
            "config": {
                "description": "Publish alert on-chain (or via webhook/notification)",
                "depends_on": "generate_alert",
                "action": "emit_event",
            },
        },
    ],
    "outputs": {
        "risk_dashboard": {
            "type": "json",
            "description": "Full risk dashboard data for all monitored chains",
        },
        "alerts": {
            "type": "array",
            "description": "Active migration alerts",
        },
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Alert system
# ─────────────────────────────────────────────────────────────────────────────

class MigrationAlert:
    """A migration risk alert."""

    def __init__(self, chain: str, severity: str, metric: str, value: float,
                 threshold: float, message: str):
        self.chain = chain
        self.severity = severity
        self.metric = metric
        self.value = value
        self.threshold = threshold
        self.message = message
        self.timestamp = datetime.utcnow().isoformat() + "Z"

    def to_dict(self):
        return {
            "chain": self.chain,
            "severity": self.severity,
            "metric": self.metric,
            "value": self.value,
            "threshold": self.threshold,
            "message": self.message,
            "timestamp": self.timestamp,
        }


# Alert thresholds
THRESHOLDS = {
    "tvl_decline_high": {"metric": "tvl_change_30d_pct", "op": "lt", "value": -20, "severity": "HIGH"},
    "tvl_decline_medium": {"metric": "tvl_change_30d_pct", "op": "lt", "value": -10, "severity": "MEDIUM"},
    "tvl_decline_low": {"metric": "tvl_change_30d_pct", "op": "lt", "value": -5, "severity": "LOW"},
    "low_tvl": {"metric": "tvl", "op": "lt", "value": 1_000_000, "severity": "HIGH"},
    "very_low_tvl": {"metric": "tvl", "op": "lt", "value": 100_000, "severity": "CRITICAL"},
}


def check_alerts(chain_health: dict) -> list:
    """Check a chain's health against alert thresholds."""
    alerts = []
    chain = chain_health.get("chain", "Unknown")

    for alert_name, config in THRESHOLDS.items():
        metric = config["metric"]
        actual = chain_health.get(metric, 0)
        threshold = config["value"]

        triggered = False
        if config["op"] == "lt" and actual < threshold:
            triggered = True
        elif config["op"] == "gt" and actual > threshold:
            triggered = True

        if triggered:
            message = (
                f"{chain}: {metric} = {actual:.1f} "
                f"(threshold: {config['op']} {threshold})"
            )
            alerts.append(MigrationAlert(
                chain=chain,
                severity=config["severity"],
                metric=metric,
                value=actual,
                threshold=threshold,
                message=message,
            ))

    return alerts


# ─────────────────────────────────────────────────────────────────────────────
# Monitor
# ─────────────────────────────────────────────────────────────────────────────

# Chains to monitor (configurable watchlist)
DEFAULT_WATCHLIST = [
    "Ethereum", "Solana", "Arbitrum", "Optimism", "Base", "Polygon",
    "BSC", "Avalanche", "Fantom", "Sui", "Aptos",
    "Cronos", "Celo", "Moonbeam", "Harmony", "Near",
]


def run_monitor(watchlist: list = None, verbose: bool = True) -> dict:
    """
    Run the CrossGuard monitor. This simulates what the CRE workflow does.
    Returns a dashboard data payload.
    """
    watchlist = watchlist or DEFAULT_WATCHLIST

    if verbose:
        print("🛡️  CrossGuard Migration Monitor")
        print(f"   Monitoring {len(watchlist)} chains\n")

    dashboard = {
        "monitor_run": datetime.utcnow().isoformat() + "Z",
        "chains_monitored": len(watchlist),
        "chain_status": [],
        "alerts": [],
        "bridge_health": None,
        "summary": {},
    }

    # 1. Fetch bridge health
    bridge = assess_bridge_risk()
    dashboard["bridge_health"] = bridge
    if verbose and isinstance(bridge, dict) and "error" not in bridge:
        print(f"🌉 Wormhole: TVL ${bridge.get('tvl', 0)/1e9:.2f}B, "
              f"Risk: {bridge.get('risk_level', '?')}")

    # 2. Check each chain
    all_alerts = []
    healthy = 0
    warning = 0
    critical = 0

    for chain_name in watchlist:
        health = get_chain_health(chain_name)
        if isinstance(health, dict) and "error" not in health:
            status = {
                "chain": chain_name,
                "tvl": health.get("tvl", 0),
                "tvl_formatted": health.get("tvl_formatted", "?"),
                "tvl_change_30d": health.get("tvl_change_30d_pct", 0),
                "trend": health.get("tvl_trend", "unknown"),
                "protocol_count": health.get("protocol_count", 0),
            }

            # Check alerts
            alerts = check_alerts(health)
            status["alert_count"] = len(alerts)
            status["max_severity"] = max((a.severity for a in alerts), default="NONE")
            all_alerts.extend(alerts)

            if alerts:
                max_sev = status["max_severity"]
                if max_sev in ("HIGH", "CRITICAL"):
                    critical += 1
                else:
                    warning += 1
            else:
                healthy += 1

            dashboard["chain_status"].append(status)

            if verbose:
                sev = status["max_severity"]
                emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(sev, "✅")
                print(f"  {emoji} {chain_name:<15} {health.get('tvl_formatted', '?'):>12} "
                      f"  {health.get('tvl_change_30d_pct', 0):>+7.1f}%  "
                      f"{health.get('tvl_trend', '?')}")

    # Alerts
    dashboard["alerts"] = [a.to_dict() for a in all_alerts]

    # Summary
    dashboard["summary"] = {
        "healthy": healthy,
        "warning": warning,
        "critical": critical,
        "total_alerts": len(all_alerts),
        "high_alerts": sum(1 for a in all_alerts if a.severity in ("HIGH", "CRITICAL")),
    }

    if verbose:
        print(f"\n📊 Summary: {healthy} healthy, {warning} warning, {critical} critical")
        print(f"   Total alerts: {len(all_alerts)}")
        if all_alerts:
            print("\n⚠️  Active Alerts:")
            for a in sorted(all_alerts, key=lambda x: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(x.severity, 4)):
                emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(a.severity, "⚪")
                print(f"   {emoji} [{a.severity}] {a.message}")

    return dashboard


def generate_cre_workflow_spec() -> str:
    """Generate the CRE workflow specification (TypeScript pseudo-code)."""
    return """// CrossGuard: AI Migration Monitor — CRE Workflow
// Chainlink Runtime Environment (CRE) specification
//
// This workflow monitors cross-chain health and generates
// migration alerts using AI-powered risk analysis.

import { Workflow, Trigger, Step } from "@chainlink/cre-sdk";
import { AIAgent } from "./ai-agent";

// Workflow definition
const crossguard = new Workflow({
  name: "crossguard-migration-monitor",
  version: "0.1.0",
});

// Trigger: Run every 30 minutes
crossguard.addTrigger(
  Trigger.schedule("*/30 * * * *", "periodic-health-check")
);

// Trigger: On large bridge transfer (>$100K)
crossguard.addTrigger(
  Trigger.onChainEvent({
    chains: ["ethereum", "solana", "arbitrum", "base"],
    event: "BridgeTransfer",
    filter: { amount: { gt: 100000 } },
  })
);

// Step 1: Fetch chain data from DeFi Llama
crossguard.addStep(
  Step.externalAPI({
    id: "fetch_chains",
    url: "https://api.llama.fi/v2/chains",
    method: "GET",
  })
);

// Step 2: Fetch Wormhole bridge health
crossguard.addStep(
  Step.externalAPI({
    id: "fetch_wormhole",
    url: "https://api.wormholescan.io/api/v1/scorecards",
    method: "GET",
  })
);

// Step 3: AI Risk Analysis
crossguard.addStep(
  Step.compute({
    id: "analyze_risk",
    inputs: ["fetch_chains.output", "fetch_wormhole.output"],
    handler: async (chainData, bridgeData) => {
      const agent = new AIAgent();
      
      // Monitor watchlist chains
      const watchlist = [
        "Ethereum", "Solana", "Arbitrum", "Fantom", "Harmony",
        "BSC", "Polygon", "Avalanche", "Cronos", "Celo",
      ];

      const results = [];
      for (const chain of watchlist) {
        const health = analyzeChainHealth(chainData, chain);
        const bridges = findBridges(chain, "Solana");
        const risk = computeRisk(health, bridgeData, bridges);
        
        results.push({
          chain,
          health,
          risk,
          bridges: bridges.length,
          alerts: checkThresholds(health, risk),
        });
      }

      return {
        timestamp: new Date().toISOString(),
        chains: results,
        summary: summarize(results),
      };
    },
  })
);

// Step 4: Check thresholds and generate alerts
crossguard.addStep(
  Step.condition({
    id: "check_alerts",
    input: "analyze_risk.output",
    condition: (data) => data.summary.totalAlerts > 0,
    onTrue: "publish_alert",
    onFalse: "update_dashboard",
  })
);

// Step 5a: Publish alert on-chain
crossguard.addStep(
  Step.onChainAction({
    id: "publish_alert",
    chain: "ethereum", // or Solana via CRE cross-chain
    action: "emit",
    event: "MigrationAlert",
    data: "analyze_risk.output.alerts",
  })
);

// Step 5b: Update dashboard
crossguard.addStep(
  Step.externalAPI({
    id: "update_dashboard",
    url: "${DASHBOARD_URL}/api/update",
    method: "POST",
    body: "analyze_risk.output",
  })
);

export default crossguard;

// --- Helper functions ---

function analyzeChainHealth(allChains: any[], chain: string) {
  const data = allChains.find((c) => c.name.toLowerCase() === chain.toLowerCase());
  if (!data) return { error: "Chain not found" };
  
  return {
    chain: data.name,
    tvl: data.tvl || 0,
    // Note: In production, fetch historical data for trend calculation
    // For CRE demo, we'd store previous readings and compare
  };
}

function computeRisk(health: any, bridgeData: any, bridges: any[]) {
  let score = 30;
  // Chain declining
  if (health.tvlChange30d < -20) score += 25;
  else if (health.tvlChange30d < -10) score += 15;
  // Bridge availability
  if (bridges.length === 0) score += 25;
  // Bridge health
  if (bridgeData.risk_score > 50) score += 10;
  
  return {
    score: Math.min(100, score),
    level: score < 30 ? "LOW" : score < 50 ? "MODERATE" : score < 70 ? "HIGH" : "CRITICAL",
  };
}

function checkThresholds(health: any, risk: any) {
  const alerts = [];
  if (health.tvlChange30d < -15) {
    alerts.push({
      severity: "HIGH",
      message: `${health.chain} TVL declining ${health.tvlChange30d.toFixed(1)}% in 30d`,
    });
  }
  if (risk.score > 70) {
    alerts.push({
      severity: "CRITICAL",
      message: `${health.chain} migration risk is CRITICAL (${risk.score}/100)`,
    });
  }
  return alerts;
}

function summarize(results: any[]) {
  return {
    totalChains: results.length,
    healthy: results.filter((r) => r.alerts.length === 0).length,
    alerting: results.filter((r) => r.alerts.length > 0).length,
    totalAlerts: results.reduce((sum, r) => sum + r.alerts.length, 0),
  };
}
"""


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

BANNER = """
╔══════════════════════════════════════════════════╗
║  🛡️  CrossGuard: AI Migration Monitor v0.1       ║
║  MigrateAI × Chainlink Convergence 2026          ║
║  CRE & AI Track                                  ║
╚══════════════════════════════════════════════════╝
"""


def main():
    if len(sys.argv) < 2:
        print(BANNER)
        print("Usage:")
        print("  python crossguard.py monitor               — Run migration monitor")
        print("  python crossguard.py monitor --chains A,B   — Monitor specific chains")
        print("  python crossguard.py workflow               — Show CRE workflow spec")
        print("  python crossguard.py spec                   — Show workflow JSON spec")
        print("  python crossguard.py risk <src> <tgt>       — Risk assessment for a pair")
        print("  python crossguard.py incidents              — List historical bridge incidents")
        print()
        print("Examples:")
        print("  python crossguard.py monitor")
        print("  python crossguard.py monitor --chains Fantom,Harmony,Cronos")
        print("  python crossguard.py workflow > crossguard-workflow.ts")
        print("  python crossguard.py risk Fantom Solana")
        return

    cmd = sys.argv[1].lower()
    args = sys.argv[2:]

    if cmd == "monitor":
        print(BANNER)
        watchlist = None
        for i, a in enumerate(args):
            if a == "--chains" and i + 1 < len(args):
                watchlist = [c.strip() for c in args[i + 1].split(",")]
        result = run_monitor(watchlist)
        print(f"\n📋 Full dashboard data: {len(json.dumps(result))} bytes")

    elif cmd == "workflow":
        print(generate_cre_workflow_spec())

    elif cmd == "spec":
        print(BANNER)
        print(json.dumps(CRE_WORKFLOW, indent=2))

    elif cmd == "risk":
        print(BANNER)
        if len(args) < 2:
            print("Usage: crossguard.py risk <source> <target>")
            return
        risk = compute_migration_risk(args[0], args[1])
        print(json.dumps(risk, indent=2))

    elif cmd == "incidents":
        print(BANNER)
        print("🛡️  Historical Bridge Incidents:\n")
        for name, inc in BRIDGE_INCIDENTS.items():
            recovered = "✅ Recovered" if inc["recovered"] else "❌ Not recovered"
            print(f"  {name.upper()} ({inc['date']}): ${inc['loss_usd']/1e6:.0f}M — {recovered}")
            print(f"    {inc['note']}\n")

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
