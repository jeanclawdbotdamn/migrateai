# Graveyard Hack - Improvements Plan

From Claude Code review (Feb 18, 2026):

1. **Real Wormhole NTT API Integration** — check_sunrise_eligibility uses stub flags that never trigger. Use actual WormholeScan API / NTT registry.
2. **Fix Migration Score Formula** — ceiling at ~90, ignores complexity, grade boundaries unreachable. Add complexity weight + continuous bridge bonuses.
3. **Add batch_rank_graveyard()** — GRAVEYARD_CANDIDATES defined but no ranked leaderboard function. Add sorted Markdown/JSON output.
4. **CLI Entry Point with argparse** — no __main__ block. Add subcommands: scan, analyze, batch, codegen with --output flag.
5. **Surface Anchor Codegen in Reports** — analyze_graveyard_chain never calls codegen. Integrate scaffold preview for high-scoring chains.
