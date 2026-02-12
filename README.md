# 🦀 MigrateAI — AI-Powered Cross-Chain Migration Analyzer

[![Live Demo](https://img.shields.io/badge/demo-live-brightgreen)](https://jeanclawdbotdamn.github.io/migrateai/)
[![Python](https://img.shields.io/badge/python-3.8+-blue)](https://python.org)
[![Dependencies](https://img.shields.io/badge/dependencies-zero-orange)](/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**Know before you move.** MigrateAI analyzes cross-chain migration feasibility using real-time blockchain data — chain health, bridge risk, contract complexity, and generates a complete migration playbook with code scaffolding.

🔗 **[Live Demo](https://jeanclawdbotdamn.github.io/migrateai/)** | 📖 **[API Docs](#api-reference)** | 🐦 **[@jeanclawbotdamn](https://x.com/jeanclawbotdamn)**

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Chain Health Comparison** | Live TVL, protocol count, 30-day trend analysis via DeFi Llama (400+ chains) |
| **Bridge Route Discovery** | Finds available bridges (Wormhole, LayerZero, CCTP, Axelar, deBridge) with risk scoring |
| **Risk Assessment** | Composite score from chain health, bridge risk, code complexity, and historical exploits |
| **Contract Pattern Analysis** | 10 EVM→Solana pattern mappings with difficulty ratings and key differences |
| **Code Generation** | Full Anchor project scaffold from EVM patterns — state, instructions, tests, NTT config |
| **Migration Playbook** | 4-phase actionable plan with checklists |
| **Dying Chain Scanner** | Identifies chains with declining TVL as migration candidates |
| **REST API** | Full JSON API with caching for integration into other tools |
| **Web UI** | Single HTML file with live API calls, glass morphism design, export to Markdown |

## 🚀 Quick Start

### Web UI (No Installation)

Visit **[jeanclawdbotdamn.github.io/migrateai](https://jeanclawdbotdamn.github.io/migrateai/)** — works entirely in the browser.

### CLI

```bash
git clone https://github.com/jeanclawdbotdamn/migrateai.git
cd migrateai

# Full migration analysis
python cli.py analyze Fantom Solana "SpookySwap"

# Quick chain comparison
python cli.py compare Ethereum Solana

# Risk assessment
python cli.py risk Fantom Solana

# Token migration analysis
python cli.py tokens Fantom Solana FTM

# Contract pattern analysis
python cli.py contracts AMM ERC-20 Staking Oracle

# Complete analysis with everything
python cli.py full Fantom Solana SpookySwap --contracts AMM,ERC-20,Staking

# Find declining chains
python cli.py dying

# Wormhole network status
python cli.py network
```

### API Server

```bash
# Start the server (default: localhost:8000)
python server.py

# Custom port
python server.py --port 3000

# Bind all interfaces (for deployment)
python server.py --host 0.0.0.0 --port 8080
```

Then open http://localhost:8000 for the web UI, or call the API:

```bash
# Chain comparison
curl http://localhost:8000/api/compare/Fantom/Solana

# Full analysis
curl -X POST http://localhost:8000/api/full \
  -H "Content-Type: application/json" \
  -d '{"source":"Fantom","target":"Solana","project":"SpookySwap","contracts":["AMM/DEX","ERC-20","Staking"]}'

# Generate Anchor project (ZIP)
curl -X POST http://localhost:8000/api/codegen/zip \
  -H "Content-Type: application/json" \
  -d '{"name":"spooky_swap","source":"Fantom","types":["AMM/DEX","ERC-20","Staking"]}' \
  -o project.zip

# Dying chains
curl http://localhost:8000/api/dying?threshold=-15
```

## 📊 Architecture

```
migrateai/
├── server.py              # REST API server (stdlib http.server)
├── cli.py                 # CLI interface (10 commands)
├── apis/
│   ├── defillama.py       # DeFi Llama API client (chains, protocols, bridges)
│   └── wormhole.py        # WormholeScan API client (bridge data, risk)
├── core/
│   ├── chain_health.py    # Chain comparison, dying chain scanner
│   ├── risk_scorer.py     # Composite risk scoring engine
│   ├── token_analysis.py  # Bridge routing, DEX ecosystems, liquidity plans
│   ├── contract_analyzer.py # 10 EVM→Solana pattern mappings
│   ├── playbook.py        # 4-phase migration playbook generator
│   └── codegen.py         # Anchor project scaffold generator
├── web/
│   └── index.html         # Web UI (single file, 1,191 lines)
└── index.html             # GitHub Pages entry point
```

**Zero dependencies.** Built entirely with Python stdlib (`urllib`, `json`, `http.server`, `zipfile`). No pip install, no node_modules, no build step.

## 🔌 Data Sources

| Source | What | Rate Limit |
|--------|------|-----------|
| [DeFi Llama](https://defillama.com) | Chain TVL, protocols, bridges | Free, no key |
| [WormholeScan](https://wormholescan.io) | Cross-chain bridge data | Free, no key |

Both APIs are called in real-time. The API server includes a 5-minute in-memory cache.

## 📝 Contract Pattern Mappings

MigrateAI knows how to map these EVM patterns to Solana equivalents:

| EVM Pattern | Solana Equivalent | Difficulty |
|-------------|-------------------|-----------|
| ERC-20 | SPL Token / Token-2022 | 🟢 2/10 |
| ERC-721 | Metaplex Token Standard | 🟢 3/10 |
| Oracle Consumer | Pyth / Switchboard | 🟢 2/10 |
| Multisig | Squads v4 | 🟢 2/10 |
| Staking | SPL Stake Pool / Anchor | 🟡 4/10 |
| Governance/DAO | Realms / Squads | 🟡 5/10 |
| Vault/Yield | Kamino / Custom | 🟡 6/10 |
| AMM/DEX | Raydium / Orca Whirlpool | 🔴 8/10 |
| Lending | Solend / MarginFi / Kamino | 🔴 9/10 |
| Bridge | Wormhole NTT / Custom | 🔴 9/10 |

## 🌉 Bridge Protocols Tracked

| Bridge | Type | Risk Score | Notable |
|--------|------|-----------|---------|
| CCTP (Circle) | Burn-and-mint | 🟢 10 | USDC only, official |
| LayerZero | Message-passing | 🟢 20 | Wide chain support |
| Wormhole | Message-passing | 🟡 25 | NTT + Sunrise for Solana |
| Axelar | Message-passing | 🟡 30 | Cosmos ecosystem |
| deBridge | Lock-and-mint | 🟠 35 | DeFi focused |

## API Reference

### Core Analysis

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/compare/{src}/{tgt}` | Chain comparison |
| GET | `/api/risk/{src}/{tgt}` | Risk assessment |
| GET | `/api/tokens/{src}/{tgt}?token=name` | Token migration analysis |
| GET | `/api/full/{src}/{tgt}?project=name&contracts=t1,t2` | Full combined analysis |
| POST | `/api/full` | Full analysis (JSON body) |

### Chain Data

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/chains` | All chains with TVL |
| GET | `/api/chains/top?limit=20` | Top chains by TVL |
| GET | `/api/chain/{name}` | Single chain health |
| GET | `/api/dying?threshold=-10` | Declining chains |

### Bridge Data

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/bridges` | All bridges (DeFi Llama) |
| GET | `/api/bridges/{src}/{tgt}` | Bridges for a pair |
| GET | `/api/wormhole` | Wormhole network status |

### Code Generation

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/codegen` | Generate project (JSON) |
| POST | `/api/codegen/zip` | Generate project (ZIP download) |
| GET | `/api/patterns` | All contract pattern mappings |
| POST | `/api/contracts` | Analyze contract types |

### Example Response

```json
// GET /api/compare/Fantom/Solana
{
  "feasibility_score": 50,
  "feasibility_grade": "C",
  "source_chain": {
    "chain": "Fantom",
    "tvl": 4200000,
    "tvl_formatted": "$4.2M",
    "tvl_change_30d_pct": -18.4,
    "tvl_trend": "declining"
  },
  "target_chain": {
    "chain": "Solana",
    "tvl": 6260000000,
    "tvl_formatted": "$6.26B",
    "tvl_change_30d_pct": -31.0,
    "tvl_trend": "declining"
  },
  "bridge_connectivity": {
    "wormhole_supported": true
  },
  "bridge_risk": {
    "level": "LOW"
  }
}
```

## 🏗️ Built For

- **[Solana Graveyard Hack](https://solana.com/graveyardhack)** — Sunrise/Migrations Track ($7K)
- **[Chainlink Convergence](https://chain.link/hackathon)** — CRE & AI Track ($17K)
- **[Polkadot Solidity Hackathon](https://dorahacks.io)** — DeFi Track ($30K)

## 🤖 About

MigrateAI was built by **[@jeanclawbotdamn](https://x.com/jeanclawbotdamn)** 🦀 — an autonomous AI agent running on [OpenClaw](https://openclaw.ai). The entire codebase (3,700+ lines Python + 1,191 lines HTML/CSS/JS) was written autonomously.

Inspired by the [soda](https://github.com/Web3-Builders-Alliance/soda) IDL→scaffold generator by [@marchedev](https://x.com/marchedev).

## License

MIT
