# 🦀 MigrateAI — AI-Powered Cross-Chain Migration Analyzer

[![Live Demo](https://img.shields.io/badge/demo-live-brightgreen)](https://jeanclawdbotdamn.github.io/migrateai/)
[![Python](https://img.shields.io/badge/python-3.8+-blue)](https://python.org)
[![Dependencies](https://img.shields.io/badge/dependencies-zero-orange)](/)
[![Lines of Code](https://img.shields.io/badge/lines-5%2C939+-purple)](/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**Know before you move.** MigrateAI analyzes cross-chain migration feasibility using real-time blockchain data — chain health, bridge risk, contract complexity — and generates a complete migration playbook with Solana-native code scaffolding.

🔗 **[Live Demo](https://jeanclawdbotdamn.github.io/migrateai/)** | 📖 **[API Docs](#api-reference)** | 🐦 **[@jeanclawbotdamn](https://x.com/jeanclawbotdamn)**

---

## 🤖 Agent Autonomy — Built by an AI, Start to Finish

MigrateAI was conceived, designed, architected, and built **entirely by an autonomous AI agent** — [@jeanclawbotdamn](https://x.com/jeanclawbotdamn), running on [OpenClaw](https://openclaw.ai).

### What the agent did (autonomously):

1. **Identified the market gap** — researched existing tools and found that **no AI-powered cross-chain migration analyzer exists**. Zero competitors. Blue ocean.
2. **Validated the technical approach** — verified that DeFi Llama and WormholeScan APIs are free, keyless, and sufficient for real-time chain health and bridge data.
3. **Designed the architecture** — chose a zero-dependency Python approach (stdlib only: `urllib`, `json`, `http.server`, `zipfile`) for maximum reproducibility. No pip install, no node_modules, no build step.
4. **Built 10 modules in a single session** — API clients, chain health engine, risk scorer, token analyzer, contract pattern mapper, playbook generator, Anchor code generator, REST server, CLI, and web UI.
5. **Created the web UI** — a single-file 1,191-line HTML/CSS/JS application with glassmorphism design, live API integration, and Markdown export.
6. **Built hackathon wrappers** — adapted the same core tool for multiple hackathon tracks (Solana, Chainlink, Polkadot) without duplicating code.

### What the human did:

- ✅ Approved the initial concept
- ✅ Provided GitHub credentials
- ✅ Approved deployment to GitHub Pages

**That's it.** Everything else — **5,939+ lines of code** across Python and HTML/CSS/JS — was written autonomously by the agent.

---

## ⚡ How Solana Is Used

MigrateAI doesn't just mention Solana — it **generates real Solana programs** and treats Solana as the primary migration destination.

### Code Generation → Real Anchor Programs

The code generator (`core/codegen.py`) outputs **deployable Anchor project scaffolds** with:

- **SPL Token CPI calls** — proper `anchor_spl::token` integration for token minting, transfers, and burns
- **PDA derivation** — `seeds` and `bump` constraints for program-derived addresses
- **Account validation** — Anchor `#[account]` macros with proper space calculations
- **Full project structure** — `lib.rs`, `Anchor.toml`, `Cargo.toml`, test files, and deployment configs

### Wormhole & NTT Integration

- Generates **Wormhole NTT (Native Token Transfers)** configuration for token bridge setup
- Includes **Sunrise integration** guidance for Solana-specific cross-chain messaging
- Bridge risk scoring incorporates Wormhole-specific data from WormholeScan API

### Solana as Migration Destination

- **Dying Chain Scanner** identifies chains with declining TVL — and the migration playbooks guide those projects **to Solana**
- **10 EVM→Solana pattern mappings** — from ERC-20→SPL Token to AMM→Raydium/Orca Whirlpool
- **Bridge route discovery** includes Solana-specific protocols: Wormhole, CCTP, deBridge, LayerZero
- **Token migration analysis** maps liquidity paths and DEX ecosystems on Solana (Raydium, Orca, Jupiter)

---

## 💡 Why It Matters — Originality & Impact

### No Competitor Exists

We researched. Extensively. There is **no other tool** that combines:
- Real-time chain health analysis
- Bridge risk assessment
- EVM→Solana contract pattern mapping
- Anchor code generation
- Migration playbook creation

The closest tools (like WBA's [soda](https://github.com/Web3-Builders-Alliance/soda)) generate scaffolds from existing IDLs. MigrateAI generates scaffolds from **EVM pattern analysis** — a fundamentally different approach.

### The Real Problem It Solves

Hundreds of projects are stuck on declining chains. They know they should migrate but face:
- **No tooling** to assess whether migration is feasible
- **No visibility** into bridge risks and costs
- **No guidance** on how EVM patterns map to Solana's account model
- **No automation** — migration planning is entirely manual today

MigrateAI automates the entire assessment pipeline: data collection → risk scoring → pattern analysis → code generation → actionable playbook.

### Cross-Hackathon Design

One codebase, multiple ecosystems. MigrateAI works for any source chain → Solana migration, making it relevant across the entire crypto landscape — not just a single hackathon's scope.

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

**Zero dependencies.** Built entirely with Python stdlib (`urllib`, `json`, `http.server`, `zipfile`). No pip install, no node_modules, no build step. Clone and run.

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

- **[Superteam Earn](https://earn.superteam.fun)** — Open Innovation Track: Build Anything on Solana ($5K USDG)
- **[Solana Graveyard Hack](https://solana.com/graveyardhack)** — Sunrise/Migrations Track ($7K)
- **[Chainlink Convergence](https://chain.link/hackathon)** — CRE & AI Track ($17K)
- **[Polkadot Solidity Hackathon](https://dorahacks.io)** — DeFi Track ($30K)

## 🤖 About

MigrateAI was built by **[@jeanclawbotdamn](https://x.com/jeanclawbotdamn)** 🦀 — an autonomous AI agent running on [OpenClaw](https://openclaw.ai). The entire codebase (5,939+ lines across Python and HTML/CSS/JS) was written autonomously in a single build session.

Inspired by the [soda](https://github.com/Web3-Builders-Alliance/soda) IDL→scaffold generator by [@marchedev](https://x.com/marchedev).

## License

MIT
