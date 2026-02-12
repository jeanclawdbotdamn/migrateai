"""WormholeScan API client — bridge data, cross-chain transfers."""

import json
import urllib.request
import urllib.error
from typing import Optional

BASE_URL = "https://api.wormholescan.io/api/v1"

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


# Wormhole chain IDs
CHAIN_IDS = {
    "solana": 1,
    "ethereum": 2,
    "bsc": 4,
    "polygon": 5,
    "avalanche": 6,
    "fantom": 10,
    "arbitrum": 23,
    "optimism": 24,
    "base": 30,
    "sui": 21,
    "aptos": 22,
    "near": 15,
    "cosmos": 20,  # cosmoshub
}

CHAIN_NAMES = {v: k for k, v in CHAIN_IDS.items()}


def get_scorecards() -> dict:
    """Get Wormhole network overview: total messages, volume, TVL."""
    return _get(f"{BASE_URL}/scorecards")


def get_top_assets(time_span: str = "7d") -> dict:
    """Get top assets by volume. time_span: 7d, 15d, 30d."""
    return _get(f"{BASE_URL}/top-assets-by-volume?timeSpan={time_span}")


def get_top_chain_pairs(time_span: str = "7d") -> dict:
    """Get top source→destination chain pairs by volume."""
    return _get(f"{BASE_URL}/top-chain-pairs-by-num-transfers?timeSpan={time_span}")


def get_chain_activity() -> dict:
    """Get activity metrics per chain on Wormhole."""
    return _get(f"{BASE_URL}/x-chain-activity")


def get_recent_transactions(page: int = 0, page_size: int = 20) -> list:
    """Get recent cross-chain transactions."""
    return _get(f"{BASE_URL}/last-txs?page={page}&pageSize={page_size}")


def get_token_bridge_support(source_chain: str, target_chain: str) -> dict:
    """
    Check what's bridgeable between two chains via Wormhole.
    Returns bridge activity and feasibility.
    """
    source_id = CHAIN_IDS.get(source_chain.lower())
    target_id = CHAIN_IDS.get(target_chain.lower())

    if not source_id or not target_id:
        return {
            "error": "Unknown chain",
            "source": source_chain,
            "target": target_chain,
            "available_chains": list(CHAIN_IDS.keys()),
        }

    # Get chain pair data
    pairs = get_top_chain_pairs("30d")
    activity = get_chain_activity()

    result = {
        "source": source_chain,
        "target": target_chain,
        "wormhole_source_id": source_id,
        "wormhole_target_id": target_id,
        "bridge_supported": True,  # Both chains are on Wormhole
    }

    # Find specific pair data
    if isinstance(pairs, list):
        for pair in pairs:
            emitter = pair.get("emitterChain")
            dest = pair.get("destinationChain")
            if emitter == source_id and dest == target_id:
                result["pair_transfers_30d"] = pair.get("numberOfTransfers", 0)
                break

    # Get overall network stats
    scorecards = get_scorecards()
    if isinstance(scorecards, dict) and "error" not in scorecards:
        result["network_total_volume"] = scorecards.get("total_volume")
        result["network_tvl"] = scorecards.get("tvl")
        result["network_24h_volume"] = scorecards.get("24h_volume")

    return result


def assess_bridge_risk() -> dict:
    """
    Assess overall Wormhole bridge health/risk.
    Based on: volume, TVL, activity levels.
    """
    scorecards = get_scorecards()
    if isinstance(scorecards, dict) and "error" not in scorecards:
        tvl = float(scorecards.get("tvl", 0))
        daily_vol = float(scorecards.get("24h_volume", 0))
        total_vol = float(scorecards.get("total_volume", 0))

        # Risk signals
        risk_score = 0
        risk_factors = []

        # TVL health
        if tvl > 1e9:
            risk_factors.append(f"Strong TVL: ${tvl/1e9:.1f}B locked")
        elif tvl > 100e6:
            risk_score += 10
            risk_factors.append(f"Moderate TVL: ${tvl/1e6:.0f}M")
        else:
            risk_score += 30
            risk_factors.append(f"Low TVL: ${tvl/1e6:.0f}M — liquidity risk")

        # Activity
        msgs_24h = int(scorecards.get("24h_messages", 0))
        if msgs_24h > 100000:
            risk_factors.append(f"High activity: {msgs_24h:,} messages/24h")
        elif msgs_24h > 10000:
            risk_factors.append(f"Moderate activity: {msgs_24h:,} messages/24h")
        else:
            risk_score += 20
            risk_factors.append(f"Low activity: {msgs_24h:,} messages/24h")

        return {
            "bridge": "Wormhole",
            "tvl": tvl,
            "daily_volume": daily_vol,
            "risk_score": risk_score,  # 0 = safe, 100 = risky
            "risk_level": "LOW" if risk_score < 20 else "MEDIUM" if risk_score < 50 else "HIGH",
            "factors": risk_factors,
        }

    return {"error": "Could not fetch Wormhole data"}


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        result = get_token_bridge_support(sys.argv[1], sys.argv[2])
    else:
        result = get_scorecards()
    print(json.dumps(result, indent=2))
