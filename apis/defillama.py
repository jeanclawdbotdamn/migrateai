"""DeFi Llama API client — zero dependencies, free, no API key needed."""

import json
import urllib.request
import urllib.error
from typing import Optional

BASE_URL = "https://api.llama.fi"
BRIDGES_URL = "https://bridges.llama.fi"

def _get(url: str, timeout: int = 30) -> dict:
    """Make GET request, return parsed JSON."""
    req = urllib.request.Request(url, headers={"User-Agent": "MigrateAI/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "url": url}
    except Exception as e:
        return {"error": str(e), "url": url}


# === Chain Data ===

def get_all_chains() -> list:
    """Get TVL data for all chains. Returns list of {name, tvl, tokenSymbol, chainId}."""
    return _get(f"{BASE_URL}/v2/chains")


def get_chain_tvl_history(chain: str) -> list:
    """Get historical TVL for a specific chain. Returns list of {date, tvl}."""
    return _get(f"{BASE_URL}/v2/historicalChainTvl/{chain}")


def get_chain_health(chain: str) -> dict:
    """
    Compute chain health metrics.
    Returns: tvl, protocol_count, tvl_change_30d, trend
    """
    chains = get_all_chains()
    if isinstance(chains, dict) and "error" in chains:
        return chains

    chain_data = None
    for c in chains:
        if c.get("name", "").lower() == chain.lower():
            chain_data = c
            break

    if not chain_data:
        return {"error": f"Chain '{chain}' not found", "available": [c["name"] for c in chains[:20]]}

    # Get historical TVL for trend
    history = get_chain_tvl_history(chain)
    tvl_trend = "unknown"
    tvl_change_30d = 0

    if isinstance(history, list) and len(history) > 30:
        current_tvl = history[-1].get("tvl", 0)
        tvl_30d_ago = history[-31].get("tvl", 0)
        if tvl_30d_ago > 0:
            tvl_change_30d = ((current_tvl - tvl_30d_ago) / tvl_30d_ago) * 100
            tvl_trend = "growing" if tvl_change_30d > 5 else "declining" if tvl_change_30d < -5 else "stable"

    # Count protocols on this chain
    protocols = get_protocols_by_chain(chain)
    protocol_count = len(protocols) if isinstance(protocols, list) else 0

    return {
        "chain": chain_data.get("name"),
        "tvl": chain_data.get("tvl", 0),
        "tvl_formatted": (
            f"${chain_data.get('tvl', 0) / 1e9:.2f}B" if chain_data.get('tvl', 0) >= 1e9
            else f"${chain_data.get('tvl', 0) / 1e6:.1f}M" if chain_data.get('tvl', 0) >= 1e6
            else f"${chain_data.get('tvl', 0) / 1e3:.0f}K" if chain_data.get('tvl', 0) >= 1e3
            else f"${chain_data.get('tvl', 0):.0f}"
        ),
        "token_symbol": chain_data.get("tokenSymbol"),
        "chain_id": chain_data.get("chainId"),
        "protocol_count": protocol_count,
        "tvl_change_30d_pct": round(tvl_change_30d, 2),
        "tvl_trend": tvl_trend,
    }


# === Protocol Data ===

def get_all_protocols() -> list:
    """Get all protocols with TVL. Returns list of protocol objects."""
    return _get(f"{BASE_URL}/protocols")


def get_protocols_by_chain(chain: str) -> list:
    """Get protocols deployed on a specific chain."""
    all_protocols = get_all_protocols()
    if isinstance(all_protocols, dict) and "error" in all_protocols:
        return all_protocols

    return [
        p for p in all_protocols
        if chain.lower() in [c.lower() for c in p.get("chains", [])]
    ]


def get_protocol(slug: str) -> dict:
    """Get detailed protocol data including chain breakdown."""
    return _get(f"{BASE_URL}/protocol/{slug}")


def find_protocol_on_chains(protocol_name: str) -> dict:
    """Find which chains a protocol is deployed on and its TVL per chain."""
    all_protocols = get_all_protocols()
    if isinstance(all_protocols, dict) and "error" in all_protocols:
        return all_protocols

    matches = []
    name_lower = protocol_name.lower()
    for p in all_protocols:
        if name_lower in p.get("name", "").lower() or name_lower in p.get("slug", "").lower():
            matches.append({
                "name": p.get("name"),
                "slug": p.get("slug"),
                "chains": p.get("chains", []),
                "tvl": p.get("tvl", 0),
                "chain_tvls": p.get("chainTvls", {}),
                "category": p.get("category"),
            })

    return {"query": protocol_name, "matches": matches}


# === Bridge Data ===

def get_all_bridges() -> list:
    """Get all tracked bridges with volumes."""
    data = _get(f"{BRIDGES_URL}/bridges")
    if isinstance(data, dict):
        return data.get("bridges", [])
    return data


def get_bridge_volume(bridge_id: int) -> dict:
    """Get volume data for a specific bridge."""
    return _get(f"{BRIDGES_URL}/bridge/{bridge_id}")


def get_bridge_chains() -> list:
    """Get bridge volume by chain — shows which chains have most bridge activity."""
    return _get(f"{BRIDGES_URL}/chains")


# === Chain Comparison ===

def compare_chains(source: str, target: str) -> dict:
    """
    Compare two chains for migration analysis.
    Returns health metrics for both + migration signals.
    """
    source_health = get_chain_health(source)
    target_health = get_chain_health(target)

    if "error" in source_health or "error" in target_health:
        return {
            "error": "Failed to get chain data",
            "source": source_health,
            "target": target_health,
        }

    # Migration signal: positive = migration makes sense
    tvl_ratio = target_health["tvl"] / max(source_health["tvl"], 1)
    protocol_ratio = target_health["protocol_count"] / max(source_health["protocol_count"], 1)

    source_declining = source_health["tvl_change_30d_pct"] < -5
    target_growing = target_health["tvl_change_30d_pct"] > 5

    migration_signal = 0
    reasons = []

    if source_declining:
        migration_signal += 25
        reasons.append(f"Source chain declining ({source_health['tvl_change_30d_pct']:.1f}% 30d)")
    if target_growing:
        migration_signal += 25
        reasons.append(f"Target chain growing ({target_health['tvl_change_30d_pct']:.1f}% 30d)")
    if tvl_ratio > 2:
        migration_signal += 15
        reasons.append(f"Target has {tvl_ratio:.1f}x more TVL")
    if protocol_ratio > 1.5:
        migration_signal += 15
        reasons.append(f"Target has {protocol_ratio:.1f}x more protocols")
    if not source_declining and not target_growing:
        reasons.append("Both chains appear stable — migration may not be urgent")

    return {
        "source": source_health,
        "target": target_health,
        "migration_signal_score": min(migration_signal, 100),
        "migration_reasons": reasons,
        "recommendation": (
            "STRONG migration case" if migration_signal >= 50
            else "MODERATE migration case" if migration_signal >= 25
            else "WEAK migration case — consider staying"
        ),
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        result = compare_chains(sys.argv[1], sys.argv[2])
    elif len(sys.argv) > 1:
        result = get_chain_health(sys.argv[1])
    else:
        result = {"usage": "python defillama.py <chain> [target_chain]"}
    print(json.dumps(result, indent=2))
