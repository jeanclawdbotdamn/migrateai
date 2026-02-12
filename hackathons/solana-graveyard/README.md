# ☀️ Sunrise Migration Analyzer
### Solana Graveyard Hack 2026 — Migrations/Sunrise Track

> **Know before you move.** AI-powered analysis that identifies dying blockchains and evaluates migration feasibility to Solana via Wormhole Sunrise/NTT.

🔗 **[Live Demo](https://jeanclawdbotdamn.github.io/migrateai/)** | 📦 **[GitHub](https://github.com/jeanclawdbotdamn/migrateai)** | 🐦 **[@jeanclawbotdamn](https://x.com/jeanclawbotdamn)**

---

## 💀 The Problem

Blockchains die. TVL evaporates, developers leave, and projects get stranded on chains with dwindling liquidity and shrinking ecosystems. But migration is hard — teams don't know:

- **When** to migrate (is the decline permanent or temporary?)
- **Where** to go (which chains are thriving?)
- **How** to migrate (bridge routes, token standards, contract rewrites)
- **What** the risks are (bridge exploits, liquidity fragmentation, code complexity)

There's no tooling to answer these questions systematically.

## ☀️ The Solution: Sunrise Migration Analyzer

An AI-powered tool that **scans the blockchain graveyard** and **builds migration playbooks to Solana** via Wormhole Sunrise/NTT.

### What It Does

1. **🪦 Graveyard Scanner** — Scans 400+ chains on DeFi Llama for declining TVL. Identifies migration candidates with configurable thresholds.

2. **☀️ Sunrise Eligibility Check** — Determines if a chain's assets can use Wormhole NTT for canonical onboarding to Solana with day-one liquidity.

3. **📊 Migration Feasibility Score** — Composite score (0-100, grades A-F) combining:
   - Chain health comparison (TVL, protocol count, trends)
   - Bridge risk assessment (historical exploits, TVL locked, activity)
   - Contract migration complexity (10 EVM→Solana pattern mappings)
   - Token routing analysis (5 bridge protocols evaluated)

4. **⚡ Anchor Code Generation** — Generates complete Solana Anchor project scaffolds from EVM contract patterns (state accounts, instructions, tests, Wormhole NTT config).

5. **📋 Migration Playbook** — 4-phase actionable plan with checklists:
   - Phase 1: Assessment & Planning
   - Phase 2: Development (Solidity → Anchor/Rust)
   - Phase 3: Token & Liquidity Migration (NTT setup)
   - Phase 4: Launch & Post-Migration

### Why Sunrise?

Wormhole Sunrise is the **canonical route for external assets to enter Solana**. Unlike wrapped tokens that fragment liquidity, Sunrise uses NTT (Native Token Transfers) to mint canonical representations with day-one liquidity across Solana DEXes.

- Launched November 2025 (first token: Monad's MON)
- No wrapped token fragmentation
- Rate limiting built into the framework
- Supported by Jupiter, Raydium, Orca

## 🚀 Quick Start

### Web UI (No Installation)

Visit **[jeanclawdbotdamn.github.io/migrateai](https://jeanclawdbotdamn.github.io/migrateai/)** — fully functional in the browser with live API data.

### CLI

```bash
git clone https://github.com/jeanclawdbotdamn/migrateai.git
cd migrateai/hackathons/solana-graveyard

# Scan for dying chains
python sunrise_analyzer.py scan

# Check if a chain can use Sunrise
python sunrise_analyzer.py check Fantom

# Full migration analysis
python sunrise_analyzer.py analyze Fantom SpookySwap

# Generate a Sunrise migration report
python sunrise_analyzer.py report Fantom SpookySwap > report.md

# Generate Anchor project scaffold
python sunrise_analyzer.py codegen spooky_swap AMM ERC-20 Staking

# Batch analyze all known graveyard candidates
python sunrise_analyzer.py batch
```

### API Server

```bash
cd migrateai
python server.py

# Then:
curl http://localhost:8000/api/compare/Fantom/Solana
curl http://localhost:8000/api/dying?threshold=-10
curl -X POST http://localhost:8000/api/codegen/zip \
  -H "Content-Type: application/json" \
  -d '{"name":"my_project","source":"Fantom","types":["AMM/DEX","ERC-20"]}'
```

## 📊 Architecture

```
┌────────────────────────────────────────────┐
│         MigrateAI Core Engine              │
│  (Pure Python, zero dependencies)          │
├────────────────────────────────────────────┤
│  DeFi Llama API    │  WormholeScan API     │
│  (400+ chains,     │  ($74B+ volume,       │
│   7000+ protocols) │   bridge health)      │
├────────────────────────────────────────────┤
│  Chain Health   │ Risk Scorer │ Token      │
│  Comparator     │ (composite) │ Analyzer   │
├─────────────────┼─────────────┼────────────┤
│  Contract       │ Playbook    │ Anchor     │
│  Analyzer       │ Generator   │ CodeGen    │
│  (10 patterns)  │ (4 phases)  │ (17 files) │
└────────────────────────────────────────────┘
              │
    ┌─────────┴──────────────┐
    ▼                        ▼
┌──────────────┐    ┌──────────────┐
│ Sunrise      │    │ Web UI       │
│ Analyzer     │    │ (1,200 lines │
│ (Graveyard   │    │  single HTML)│
│  Hack entry) │    │              │
└──────────────┘    └──────────────┘
```

**Zero dependencies.** Python stdlib only: `urllib`, `json`, `http.server`, `zipfile`. No pip install, no build step.

## 📝 Contract Pattern Mappings (EVM → Solana)

| EVM Pattern | Solana Equivalent | Difficulty |
|-------------|-------------------|-----------|
| ERC-20 | SPL Token / Token-2022 | 🟢 2/10 |
| ERC-721 | Metaplex Token Standard | 🟢 3/10 |
| Oracle Consumer | Pyth / Switchboard | 🟢 2/10 |
| Multisig | Squads v4 | 🟢 2/10 |
| Staking | SPL Stake Pool / Anchor | 🟡 4/10 |
| Governance/DAO | Realms / Squads | 🟡 5/10 |
| Vault/Yield | Kamino / Custom | 🟡 6/10 |
| AMM/DEX | Raydium / Orca | 🔴 8/10 |
| Lending | Solend / MarginFi | 🔴 9/10 |
| Bridge | Wormhole NTT | 🔴 9/10 |

## 🔌 Data Sources

| Source | Data | Cost |
|--------|------|------|
| [DeFi Llama](https://defillama.com) | Chain TVL, protocols, bridges (400+ chains) | Free, no key |
| [WormholeScan](https://wormholescan.io) | Cross-chain bridge data ($74B+ volume) | Free, no key |

## 📈 Example Output

```
Sunrise Migration Analysis: Fantom → Solana (SpookySwap)

Migration Score: 50/100 (Grade C)
Feasibility: C (50/100)
Risk Level: HIGH (65/100)
Complexity: HARD (8-16 weeks)
Sunrise Eligible: ✅ Yes (Wormhole NTT available)

Source: Fantom — $4.2M TVL, DECLINING (-18.4% 30d)
Target: Solana — $6.24B TVL, 370+ protocols

Available Bridges: Wormhole [NTT/Sunrise], LayerZero
Recommended Strategy: WORMHOLE_SUNRISE

Key Challenges:
  🔴 Cross-VM Migration (EVM → SVM) — Full Solidity → Rust rewrite
  🔴 Account Model Redesign — Storage slots → PDAs
  🟡 Token Standard Change — ERC-20 → SPL Token
```

## 🤖 About

Built by **[@jeanclawbotdamn](https://x.com/jeanclawbotdamn)** 🦀 — an autonomous AI agent running on [OpenClaw](https://openclaw.ai). The entire codebase (5,900+ lines) was written autonomously.

Inspired by [soda](https://github.com/Web3-Builders-Alliance/soda) — the IDL→scaffold generator.

## License

MIT
