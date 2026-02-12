"""Token Analysis Module — bridge liquidity and DEX availability analysis."""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from apis.defillama import get_all_bridges, get_all_protocols, _get as api_call


# Well-known DEX protocols per chain
CHAIN_DEX_MAP = {
    "solana": ["Jupiter", "Raydium", "Orca", "Meteora", "Phoenix", "Lifinity"],
    "ethereum": ["Uniswap", "Curve", "Balancer", "SushiSwap", "1inch", "Maverick"],
    "bsc": ["PancakeSwap", "Venus", "Biswap", "Thena"],
    "polygon": ["QuickSwap", "Uniswap", "Balancer", "Curve"],
    "arbitrum": ["GMX", "Camelot", "Uniswap", "Curve", "Trader Joe"],
    "optimism": ["Velodrome", "Uniswap", "Curve", "Synthetix"],
    "avalanche": ["Trader Joe", "Pangolin", "Platypus", "Curve"],
    "fantom": ["SpookySwap", "Beethoven X", "Equalizer", "SpiritSwap"],
    "base": ["Aerodrome", "Uniswap", "BaseSwap", "Maverick"],
    "sui": ["Cetus", "Turbos", "KriyaDEX", "FlowX"],
}

# Stablecoin availability per chain
CHAIN_STABLECOINS = {
    "solana": ["USDC (native)", "USDT", "pyUSD", "UXD"],
    "ethereum": ["USDC", "USDT", "DAI", "FRAX", "LUSD", "GHO"],
    "bsc": ["USDT", "USDC", "BUSD (deprecated)", "DAI"],
    "polygon": ["USDC (native)", "USDT", "DAI", "FRAX"],
    "arbitrum": ["USDC (native)", "USDT", "DAI", "FRAX"],
    "optimism": ["USDC (native)", "USDT", "DAI", "sUSD"],
    "avalanche": ["USDC", "USDT", "DAI"],
    "fantom": ["USDC (bridged)", "USDT (bridged)", "DAI (bridged)"],
    "base": ["USDC (native)", "USDbC", "DAI"],
}

# Bridge protocols and their chain support
BRIDGE_PROTOCOLS = {
    "Wormhole": {
        "type": "message-passing",
        "supports": ["solana", "ethereum", "bsc", "polygon", "arbitrum", "optimism", "avalanche", "base", "sui", "fantom"],
        "ntt": True,
        "sunrise": True,
        "risk_score": 25,
    },
    "LayerZero": {
        "type": "message-passing",
        "supports": ["ethereum", "bsc", "polygon", "arbitrum", "optimism", "avalanche", "base", "fantom", "solana"],
        "ntt": False,
        "risk_score": 20,
    },
    "CCTP (Circle)": {
        "type": "burn-and-mint",
        "supports": ["ethereum", "arbitrum", "optimism", "base", "polygon", "solana", "avalanche"],
        "ntt": False,
        "risk_score": 10,
        "note": "USDC-only, official Circle bridge",
    },
    "Axelar": {
        "type": "message-passing",
        "supports": ["ethereum", "polygon", "avalanche", "fantom", "arbitrum", "optimism", "base"],
        "ntt": False,
        "risk_score": 30,
    },
    "deBridge": {
        "type": "lock-and-mint",
        "supports": ["ethereum", "bsc", "polygon", "arbitrum", "solana", "avalanche", "base"],
        "ntt": False,
        "risk_score": 35,
    },
}


def get_available_bridges(source: str, target: str) -> list:
    """Find bridges that support both source and target chains."""
    source_l = source.lower()
    target_l = target.lower()
    available = []

    for name, info in BRIDGE_PROTOCOLS.items():
        supports = [c.lower() for c in info["supports"]]
        if source_l in supports and target_l in supports:
            available.append({
                "name": name,
                "type": info["type"],
                "ntt_support": info.get("ntt", False),
                "sunrise_support": info.get("sunrise", False),
                "risk_score": info["risk_score"],
                "note": info.get("note", ""),
            })

    return sorted(available, key=lambda x: x["risk_score"])


def get_dex_ecosystem(chain: str) -> dict:
    """Get DEX ecosystem info for a chain."""
    chain_l = chain.lower()
    dexes = CHAIN_DEX_MAP.get(chain_l, [])
    stables = CHAIN_STABLECOINS.get(chain_l, [])

    # Try to get protocol counts from DeFi Llama
    all_protocols = get_all_protocols()

    dex_protocols = []
    if isinstance(all_protocols, list):
        for p in all_protocols:
            chains = [c.lower() for c in (p.get("chains") or [])]
            if chain_l in chains and p.get("category") in ["Dexes", "Derivatives", "Yield"]:
                dex_protocols.append({
                    "name": p.get("name", "Unknown"),
                    "category": p.get("category", ""),
                    "tvl": p.get("tvl", 0),
                })

    # Sort by TVL
    dex_protocols.sort(key=lambda x: x.get("tvl", 0), reverse=True)

    return {
        "chain": chain,
        "known_dexes": dexes,
        "stablecoins": stables,
        "defi_protocols_on_chain": len(dex_protocols),
        "top_protocols": dex_protocols[:10],
        "liquidity_rating": _rate_liquidity(chain_l, len(dex_protocols)),
    }


def _rate_liquidity(chain: str, protocol_count: int) -> str:
    """Simple liquidity rating."""
    high_liquidity = {"ethereum", "solana", "arbitrum", "bsc", "base"}
    medium_liquidity = {"polygon", "optimism", "avalanche", "sui"}

    if chain in high_liquidity:
        return "HIGH"
    elif chain in medium_liquidity:
        return "MEDIUM"
    elif protocol_count > 20:
        return "MEDIUM"
    elif protocol_count > 5:
        return "LOW"
    else:
        return "VERY LOW"


def analyze_token_migration(source: str, target: str, token_name: str = "Project Token") -> dict:
    """Complete token migration analysis."""
    bridges = get_available_bridges(source, target)
    source_dex = get_dex_ecosystem(source)
    target_dex = get_dex_ecosystem(target)

    # Bridge strategy recommendation
    bridge_strategy = _recommend_bridge_strategy(bridges, source, target)

    # Liquidity bootstrapping plan
    liquidity_plan = _liquidity_plan(target, target_dex)

    return {
        "token_name": token_name,
        "source_chain": source,
        "target_chain": target,
        "available_bridges": bridges,
        "bridge_count": len(bridges),
        "recommended_strategy": bridge_strategy,
        "source_dex_ecosystem": source_dex,
        "target_dex_ecosystem": target_dex,
        "liquidity_plan": liquidity_plan,
        "migration_complexity": _token_migration_complexity(bridges, source, target),
    }


def _recommend_bridge_strategy(bridges: list, source: str, target: str) -> dict:
    """Recommend the best bridge strategy."""
    target_is_solana = target.lower() == "solana"

    if not bridges:
        return {
            "strategy": "CUSTOM_BRIDGE",
            "detail": "No standard bridges support this chain pair. Custom bridge or intermediary chain required.",
            "risk": "HIGH",
        }

    # Check for Wormhole NTT/Sunrise (best for Solana migrations)
    for b in bridges:
        if b["name"] == "Wormhole" and target_is_solana and b.get("sunrise_support"):
            return {
                "strategy": "WORMHOLE_SUNRISE",
                "bridge": "Wormhole NTT (Sunrise)",
                "detail": "Use Wormhole's Sunrise program for canonical asset onboarding to Solana with day-one liquidity.",
                "risk": "LOW",
                "ntt": True,
            }

    # Check for CCTP (best for USDC)
    for b in bridges:
        if b["name"] == "CCTP (Circle)":
            return {
                "strategy": "CCTP_PRIMARY",
                "bridge": "CCTP (Circle)",
                "detail": "Use Circle's CCTP for native USDC bridging (burn-and-mint, official).",
                "risk": "LOW",
                "supplementary": bridges[0]["name"] if bridges[0]["name"] != "CCTP (Circle)" else (bridges[1]["name"] if len(bridges) > 1 else None),
            }

    # Default: lowest risk bridge
    best = bridges[0]
    return {
        "strategy": "STANDARD_BRIDGE",
        "bridge": best["name"],
        "detail": f"Use {best['name']} ({best['type']}) for token transfers.",
        "risk": "MEDIUM" if best["risk_score"] < 30 else "HIGH",
    }


def _liquidity_plan(target: str, target_dex: dict) -> list:
    """Generate liquidity bootstrapping steps."""
    target_l = target.lower()
    steps = []

    if target_l == "solana":
        steps = [
            "Deploy SPL token (or Token-2022 for advanced features)",
            "Seed liquidity on Jupiter aggregator via Meteora or Orca CLMM",
            "Apply for Jupiter Verified Token List",
            "Set up Raydium CPMM pool for stable liquidity",
            "Consider Meteora DLMM for concentrated liquidity",
            "Register on Solana token registry (solana-labs/token-list)",
        ]
    elif target_l in ("ethereum", "arbitrum", "optimism", "base", "polygon"):
        steps = [
            "Deploy ERC-20 token contract",
            f"Create Uniswap V3 pool on {target}",
            "Seed initial liquidity ($10K+ recommended)",
            "Register on token lists (Uniswap, CoinGecko)",
            "Consider Curve pool if stablecoin-adjacent",
        ]
    else:
        primary_dex = target_dex["known_dexes"][0] if target_dex["known_dexes"] else "primary DEX"
        steps = [
            f"Deploy token on {target}",
            f"Create pool on {primary_dex}",
            "Seed initial liquidity",
            "Register on chain's token list",
        ]

    return steps


def _token_migration_complexity(bridges: list, source: str, target: str) -> str:
    """Rate token migration complexity."""
    if not bridges:
        return "VERY HIGH — no standard bridge support"

    has_ntt = any(b.get("ntt_support") for b in bridges)
    has_cctp = any(b["name"] == "CCTP (Circle)" for b in bridges)

    source_evm = source.lower() in {"ethereum", "bsc", "polygon", "arbitrum", "optimism", "base", "avalanche", "fantom"}
    target_evm = target.lower() in {"ethereum", "bsc", "polygon", "arbitrum", "optimism", "base", "avalanche"}

    if source_evm and target_evm:
        return "LOW — EVM to EVM, standard bridge"
    elif has_ntt or has_cctp:
        return "MEDIUM — established bridge path available"
    else:
        return "HIGH — cross-VM migration with custom bridge integration"


def generate_token_report(source: str, target: str, token_name: str = "Project Token") -> str:
    """Generate a human-readable token migration report."""
    analysis = analyze_token_migration(source, target, token_name)

    report = f"""# 🪙 Token Migration Analysis: {token_name}
## {source} → {target}

### Available Bridges ({analysis['bridge_count']})
"""
    for b in analysis["available_bridges"]:
        emoji = "🟢" if b["risk_score"] < 20 else ("🟡" if b["risk_score"] < 35 else "🔴")
        ntt_tag = " [NTT]" if b.get("ntt_support") else ""
        sunrise_tag = " [Sunrise]" if b.get("sunrise_support") else ""
        note = f" — {b['note']}" if b.get("note") else ""
        report += f"- {emoji} **{b['name']}** ({b['type']}){ntt_tag}{sunrise_tag}{note}\n"

    strat = analysis["recommended_strategy"]
    report += f"""
### Recommended Strategy: {strat['strategy']}
- Bridge: {strat.get('bridge', 'N/A')}
- Risk: {strat['risk']}
- Detail: {strat['detail']}

### Complexity: {analysis['migration_complexity']}

### Source DEX Ecosystem ({source})
- Known DEXes: {', '.join(analysis['source_dex_ecosystem']['known_dexes']) or 'Unknown'}
- Stablecoins: {', '.join(analysis['source_dex_ecosystem']['stablecoins']) or 'Unknown'}
- Liquidity Rating: {analysis['source_dex_ecosystem']['liquidity_rating']}

### Target DEX Ecosystem ({target})
- Known DEXes: {', '.join(analysis['target_dex_ecosystem']['known_dexes']) or 'Unknown'}
- Stablecoins: {', '.join(analysis['target_dex_ecosystem']['stablecoins']) or 'Unknown'}
- Liquidity Rating: {analysis['target_dex_ecosystem']['liquidity_rating']}

### Liquidity Bootstrapping Plan
"""
    for i, step in enumerate(analysis["liquidity_plan"], 1):
        report += f"{i}. {step}\n"

    return report


if __name__ == "__main__":
    if len(sys.argv) > 2:
        src = sys.argv[1]
        tgt = sys.argv[2]
        name = sys.argv[3] if len(sys.argv) > 3 else "Project Token"
        print(generate_token_report(src, tgt, name))
    else:
        print("Usage: python token_analysis.py <source> <target> [token_name]")
        print("Example: python token_analysis.py Fantom Solana FTM")
