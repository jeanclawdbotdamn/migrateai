#!/usr/bin/env python3
"""
MigrateAI API Server — Zero-dependency REST API for cross-chain migration analysis.

Endpoints:
  GET  /                              → Web UI
  GET  /api/health                    → Server health check
  GET  /api/chains                    → All chains with TVL
  GET  /api/chains/top?limit=20       → Top chains by TVL
  GET  /api/chain/<name>              → Single chain health
  GET  /api/compare/<src>/<tgt>       → Chain-vs-chain comparison
  GET  /api/risk/<src>/<tgt>          → Risk assessment
  GET  /api/tokens/<src>/<tgt>        → Token migration analysis
  GET  /api/bridges                   → All bridges from DeFi Llama
  GET  /api/bridges/<src>/<tgt>       → Available bridges for a pair
  POST /api/contracts                 → Contract pattern analysis
  GET  /api/playbook/<src>/<tgt>      → Migration playbook (text)
  GET  /api/full/<src>/<tgt>          → Full combined analysis (JSON)
  GET  /api/dying?threshold=-10       → Declining chains scanner
  POST /api/codegen                   → Generate Anchor project (ZIP)
  GET  /api/wormhole                  → Wormhole network scorecards

Usage:
  python server.py                    → Start on port 8000
  python server.py --port 3000        → Start on port 3000
  python server.py --host 0.0.0.0     → Bind all interfaces

Built with Python stdlib only. No Flask, no FastAPI, no dependencies.
"""

import json
import os
import sys
import io
import zipfile
import re
import time
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
from datetime import datetime

# Add project root to path
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from apis.defillama import (
    get_all_chains, get_chain_health, compare_chains,
    get_all_bridges, get_all_protocols, get_protocols_by_chain,
    find_protocol_on_chains, get_bridge_chains,
)
from apis.wormhole import (
    get_scorecards, get_top_assets, get_top_chain_pairs,
    get_chain_activity, get_token_bridge_support, assess_bridge_risk,
)
from core.chain_health import full_chain_comparison, scan_dying_chains
from core.risk_scorer import (
    compute_migration_risk, get_contract_complexity,
    EVM_TO_SOLANA_CHALLENGES, BRIDGE_INCIDENTS,
)
from core.token_analysis import (
    analyze_token_migration, get_available_bridges, get_dex_ecosystem,
)
from core.contract_analyzer import (
    identify_patterns, estimate_project_complexity,
    EVM_TO_SOLANA_PATTERNS, COMPLEXITY_LEVELS,
)
from core.playbook import generate_playbook
from core.codegen import generate_anchor_project


# ─────────────────────────────────────────────────────────────────────────────
# Simple in-memory cache with TTL
# ─────────────────────────────────────────────────────────────────────────────
class Cache:
    """Simple in-memory cache with TTL."""

    def __init__(self, default_ttl: int = 300):
        self._store = {}
        self._ttl = default_ttl

    def get(self, key: str):
        entry = self._store.get(key)
        if entry and time.time() < entry["expires"]:
            return entry["value"]
        if entry:
            del self._store[key]
        return None

    def set(self, key: str, value, ttl: int = None):
        self._store[key] = {
            "value": value,
            "expires": time.time() + (ttl or self._ttl),
        }

    def clear(self):
        self._store.clear()

    @property
    def size(self):
        return len(self._store)


cache = Cache(default_ttl=300)  # 5 min default


# ─────────────────────────────────────────────────────────────────────────────
# Request Handler
# ─────────────────────────────────────────────────────────────────────────────
class MigrateAIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for MigrateAI API."""

    server_version = "MigrateAI/0.1"

    def log_message(self, format, *args):
        """Custom log format."""
        ts = datetime.utcnow().strftime("%H:%M:%S")
        sys.stderr.write(f"  [{ts}] {args[0]}\n")

    # ── CORS ──────────────────────────────────────────────────────────────

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    # ── Response helpers ──────────────────────────────────────────────────

    def _json(self, data, status=200):
        body = json.dumps(data, indent=2, default=str).encode("utf-8")
        self.send_response(status)
        self._cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _text(self, text, status=200, content_type="text/plain"):
        body = text.encode("utf-8")
        self.send_response(status)
        self._cors_headers()
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, html, status=200):
        self._text(html, status, "text/html")

    def _binary(self, data, filename, content_type="application/octet-stream"):
        self.send_response(200)
        self._cors_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _error(self, status, message):
        self._json({"error": message, "status": status}, status)

    # ── Routing ───────────────────────────────────────────────────────────

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path).rstrip("/") or "/"
        params = parse_qs(parsed.query)

        try:
            # Static files
            if path == "/" or path == "/index.html":
                return self._serve_ui()

            # API routes
            if path == "/api/health":
                return self._api_health()
            if path == "/api/chains":
                return self._api_chains(params)
            if path == "/api/chains/top":
                return self._api_chains_top(params)
            if path.startswith("/api/chain/"):
                name = path.split("/api/chain/", 1)[1]
                return self._api_chain(name)
            if re.match(r"^/api/compare/[^/]+/[^/]+$", path):
                parts = path.split("/")
                return self._api_compare(parts[3], parts[4])
            if re.match(r"^/api/risk/[^/]+/[^/]+$", path):
                parts = path.split("/")
                return self._api_risk(parts[3], parts[4])
            if re.match(r"^/api/tokens/[^/]+/[^/]+$", path):
                parts = path.split("/")
                return self._api_tokens(parts[3], parts[4], params)
            if path == "/api/bridges":
                return self._api_bridges(params)
            if re.match(r"^/api/bridges/[^/]+/[^/]+$", path):
                parts = path.split("/")
                return self._api_bridges_pair(parts[3], parts[4])
            if re.match(r"^/api/playbook/[^/]+/[^/]+$", path):
                parts = path.split("/")
                return self._api_playbook(parts[3], parts[4], params)
            if re.match(r"^/api/full/[^/]+/[^/]+$", path):
                parts = path.split("/")
                return self._api_full(parts[3], parts[4], params)
            if path == "/api/dying":
                return self._api_dying(params)
            if path == "/api/wormhole":
                return self._api_wormhole()
            if path == "/api/wormhole/pairs":
                return self._api_wormhole_pairs(params)
            if path == "/api/wormhole/assets":
                return self._api_wormhole_assets(params)
            if path == "/api/patterns":
                return self._api_patterns()
            if path == "/api/complexity":
                return self._api_complexity(params)
            if path == "/api/protocols":
                return self._api_protocols(params)
            if path.startswith("/api/protocol/"):
                name = path.split("/api/protocol/", 1)[1]
                return self._api_protocol(name)
            if path == "/api/cache/stats":
                return self._api_cache_stats()
            if path == "/api/cache/clear":
                cache.clear()
                return self._json({"cleared": True})

            self._error(404, f"Not found: {path}")

        except Exception as e:
            traceback.print_exc()
            self._error(500, str(e))

    def do_POST(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path).rstrip("/")

        try:
            # Read body
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length else b"{}"
            data = json.loads(body) if body else {}

            if path == "/api/contracts":
                return self._api_contracts(data)
            if path == "/api/codegen":
                return self._api_codegen(data)
            if path == "/api/codegen/zip":
                return self._api_codegen_zip(data)
            if path == "/api/full":
                return self._api_full_post(data)

            self._error(404, f"Not found: {path}")

        except json.JSONDecodeError:
            self._error(400, "Invalid JSON body")
        except Exception as e:
            traceback.print_exc()
            self._error(500, str(e))

    # ── Static file server ────────────────────────────────────────────────

    def _serve_ui(self):
        """Serve the web UI."""
        # Try web/index.html first, then root index.html
        for candidate in ["web/index.html", "index.html"]:
            filepath = os.path.join(ROOT, candidate)
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    return self._html(f.read())
        self._error(404, "Web UI not found. Expected web/index.html or index.html")

    # ── API endpoints ─────────────────────────────────────────────────────

    def _api_health(self):
        """Server health + basic stats."""
        self._json({
            "status": "ok",
            "version": "0.1.0",
            "name": "MigrateAI",
            "description": "AI-Powered Cross-Chain Migration Analyzer",
            "cache_entries": cache.size,
            "endpoints": [
                "GET /api/health",
                "GET /api/chains",
                "GET /api/chains/top?limit=N",
                "GET /api/chain/<name>",
                "GET /api/compare/<src>/<tgt>",
                "GET /api/risk/<src>/<tgt>",
                "GET /api/tokens/<src>/<tgt>?token=name",
                "GET /api/bridges",
                "GET /api/bridges/<src>/<tgt>",
                "POST /api/contracts  {types:[...]}",
                "GET /api/playbook/<src>/<tgt>?project=name",
                "GET /api/full/<src>/<tgt>?project=name&contracts=t1,t2",
                "POST /api/full  {source,target,project,contracts:[]}",
                "GET /api/dying?threshold=-10",
                "POST /api/codegen  {name,source,types:[]}",
                "POST /api/codegen/zip  {name,source,types:[]}",
                "GET /api/wormhole",
                "GET /api/wormhole/pairs?span=7d",
                "GET /api/wormhole/assets?span=7d",
                "GET /api/patterns",
                "GET /api/protocols?chain=name",
                "GET /api/protocol/<name>",
            ],
        })

    def _api_chains(self, params):
        """All chains."""
        cached = cache.get("chains:all")
        if cached:
            return self._json(cached)
        data = get_all_chains()
        if isinstance(data, list):
            cache.set("chains:all", data, ttl=600)
        self._json(data)

    def _api_chains_top(self, params):
        """Top chains by TVL."""
        limit = int(params.get("limit", [20])[0])
        cached = cache.get("chains:all")
        chains = cached if cached else get_all_chains()
        if isinstance(chains, list):
            if not cached:
                cache.set("chains:all", chains, ttl=600)
            sorted_chains = sorted(chains, key=lambda x: x.get("tvl", 0), reverse=True)[:limit]
            return self._json({
                "total": len(chains),
                "showing": len(sorted_chains),
                "chains": sorted_chains,
            })
        self._json(chains)

    def _api_chain(self, name):
        """Single chain health."""
        key = f"chain:{name.lower()}"
        cached = cache.get(key)
        if cached:
            return self._json(cached)
        data = get_chain_health(name)
        if isinstance(data, dict) and "error" not in data:
            cache.set(key, data)
        self._json(data)

    def _api_compare(self, source, target):
        """Chain comparison."""
        key = f"compare:{source.lower()}:{target.lower()}"
        cached = cache.get(key)
        if cached:
            return self._json(cached)
        data = full_chain_comparison(source, target)
        if isinstance(data, dict) and "error" not in data:
            cache.set(key, data)
        self._json(data)

    def _api_risk(self, source, target):
        """Risk assessment."""
        key = f"risk:{source.lower()}:{target.lower()}"
        cached = cache.get(key)
        if cached:
            return self._json(cached)
        data = compute_migration_risk(source, target)
        cache.set(key, data)
        self._json(data)

    def _api_tokens(self, source, target, params):
        """Token migration analysis."""
        token = params.get("token", ["Project Token"])[0]
        key = f"tokens:{source.lower()}:{target.lower()}:{token}"
        cached = cache.get(key)
        if cached:
            return self._json(cached)
        data = analyze_token_migration(source, target, token)
        cache.set(key, data)
        self._json(data)

    def _api_bridges(self, params):
        """All bridges from DeFi Llama."""
        cached = cache.get("bridges:all")
        if cached:
            return self._json(cached)
        data = get_all_bridges()
        if isinstance(data, list):
            cache.set("bridges:all", data, ttl=600)
        self._json(data)

    def _api_bridges_pair(self, source, target):
        """Available bridges for a chain pair."""
        data = get_available_bridges(source, target)
        self._json({
            "source": source,
            "target": target,
            "count": len(data),
            "bridges": data,
        })

    def _api_contracts(self, data):
        """Contract pattern analysis."""
        types = data.get("types", [])
        if not types:
            return self._error(400, "Missing 'types' array")
        source = data.get("source", "EVM")
        target = data.get("target", "Solana")
        analysis = estimate_project_complexity(types)
        return self._json(analysis)

    def _api_playbook(self, source, target, params):
        """Migration playbook (markdown)."""
        project = params.get("project", ["Your Project"])[0]
        playbook = generate_playbook(source, target, project)
        content_type = params.get("format", ["text"])[0]
        if content_type == "json":
            return self._json({"source": source, "target": target, "project": project, "playbook": playbook})
        return self._text(playbook, content_type="text/markdown")

    def _api_full(self, source, target, params):
        """Full combined analysis (JSON)."""
        project = params.get("project", ["Your Project"])[0]
        contracts_str = params.get("contracts", [""])[0]
        contracts = [c.strip() for c in contracts_str.split(",") if c.strip()] if contracts_str else []
        return self._run_full(source, target, project, contracts)

    def _api_full_post(self, data):
        """Full analysis via POST."""
        source = data.get("source", "")
        target = data.get("target", "")
        if not source or not target:
            return self._error(400, "Missing 'source' and/or 'target'")
        project = data.get("project", "Your Project")
        contracts = data.get("contracts", [])
        return self._run_full(source, target, project, contracts)

    def _run_full(self, source, target, project, contracts):
        """Execute full analysis pipeline."""
        key = f"full:{source.lower()}:{target.lower()}:{','.join(sorted(c.lower() for c in contracts))}"
        cached = cache.get(key)
        if cached:
            return self._json(cached)

        result = {
            "source": source,
            "target": target,
            "project": project,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }

        # Chain comparison
        comparison = full_chain_comparison(source, target)
        result["chain_comparison"] = comparison

        # Risk assessment
        risk = compute_migration_risk(source, target)
        result["risk"] = risk

        # Token analysis
        tokens = analyze_token_migration(source, target, project)
        result["token_analysis"] = tokens

        # Bridge data
        bridges = get_available_bridges(source, target)
        result["bridges"] = {"count": len(bridges), "available": bridges}

        # Wormhole
        wh = assess_bridge_risk()
        result["wormhole_health"] = wh

        # Contract analysis (if provided)
        if contracts:
            result["contract_analysis"] = estimate_project_complexity(contracts)

        # DEX ecosystems
        result["source_dex"] = get_dex_ecosystem(source)
        result["target_dex"] = get_dex_ecosystem(target)

        # Contract complexity
        complexity = get_contract_complexity(source, target)
        result["migration_complexity"] = complexity

        cache.set(key, result, ttl=300)
        self._json(result)

    def _api_dying(self, params):
        """Scan for declining chains."""
        threshold = float(params.get("threshold", [-10])[0])
        limit = int(params.get("limit", [20])[0])

        cached = cache.get(f"dying:{threshold}")
        if cached:
            return self._json(cached)

        dying = scan_dying_chains(threshold)
        result = {
            "threshold_pct": threshold,
            "total_found": len(dying),
            "showing": min(len(dying), limit),
            "chains": dying[:limit],
        }
        cache.set(f"dying:{threshold}", result, ttl=900)  # 15 min cache (expensive call)
        self._json(result)

    def _api_codegen(self, data):
        """Generate Anchor project scaffold (JSON with file contents)."""
        name = data.get("name", "my_project")
        source = data.get("source", "EVM")
        types = data.get("types", [])
        if not types:
            return self._error(400, "Missing 'types' array")

        files = generate_anchor_project(name, types, source)
        result = {
            "project_name": name,
            "source_chain": source,
            "contract_types": types,
            "file_count": len(files),
            "files": {path: {"content": content, "lines": content.count("\n") + 1}
                      for path, content in files.items()},
            "total_lines": sum(c.count("\n") + 1 for c in files.values()),
        }
        self._json(result)

    def _api_codegen_zip(self, data):
        """Generate Anchor project and return as ZIP file."""
        name = data.get("name", "my_project")
        source = data.get("source", "EVM")
        types = data.get("types", [])
        if not types:
            return self._error(400, "Missing 'types' array")

        files = generate_anchor_project(name, types, source)

        # Create ZIP in memory
        buf = io.BytesIO()
        slug = name.lower().replace(" ", "_").replace("-", "_")
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for filepath, content in sorted(files.items()):
                zf.writestr(f"{slug}/{filepath}", content)

            # Add a quick-start README
            zf.writestr(f"{slug}/README.md", f"""# {name}
## Migrated from {source} → Solana
*Generated by MigrateAI*

### Quick Start
```bash
cd {slug}
yarn install
anchor build
anchor test
anchor deploy --provider.cluster devnet
```

### Contract Types
{chr(10).join(f'- {t}' for t in types)}

### Generated Files
{chr(10).join(f'- `{f}` ({c.count(chr(10))+1} lines)' for f, c in sorted(files.items()))}

---
*https://github.com/jeanclawdbotdamn/migrateai*
""")

        zip_bytes = buf.getvalue()
        filename = f"migrateai-{slug}.zip"
        self._binary(zip_bytes, filename, "application/zip")

    def _api_wormhole(self):
        """Wormhole network status."""
        cached = cache.get("wormhole:scorecards")
        if cached:
            return self._json(cached)
        data = get_scorecards()
        if isinstance(data, dict) and "error" not in data:
            cache.set("wormhole:scorecards", data, ttl=300)
        self._json(data)

    def _api_wormhole_pairs(self, params):
        """Top chain pairs on Wormhole."""
        span = params.get("span", ["7d"])[0]
        data = get_top_chain_pairs(span)
        self._json(data)

    def _api_wormhole_assets(self, params):
        """Top assets on Wormhole."""
        span = params.get("span", ["7d"])[0]
        data = get_top_assets(span)
        self._json(data)

    def _api_patterns(self):
        """List all known contract migration patterns."""
        patterns = {}
        for name, info in EVM_TO_SOLANA_PATTERNS.items():
            patterns[name] = {
                "description": info["description"],
                "solana_equivalent": info["solana_equivalent"],
                "difficulty": info["difficulty"],
                "notes": info["notes"],
                "key_differences": info["key_differences"],
            }
        self._json({
            "pattern_count": len(patterns),
            "patterns": patterns,
            "complexity_levels": {
                f"{lo}-{hi}": info for (lo, hi), info in COMPLEXITY_LEVELS.items()
            },
        })

    def _api_complexity(self, params):
        """Check chain-to-chain migration complexity."""
        source = params.get("source", [""])[0]
        target = params.get("target", [""])[0]
        if not source or not target:
            return self._error(400, "Missing 'source' and 'target' params")
        data = get_contract_complexity(source, target)
        self._json(data)

    def _api_protocols(self, params):
        """Get protocols, optionally filtered by chain."""
        chain = params.get("chain", [""])[0]
        if chain:
            data = get_protocols_by_chain(chain)
            return self._json({
                "chain": chain,
                "count": len(data) if isinstance(data, list) else 0,
                "protocols": data[:100] if isinstance(data, list) else data,
            })
        # Without chain filter, return count only (too large for full response)
        all_p = get_all_protocols()
        if isinstance(all_p, list):
            return self._json({"total_protocols": len(all_p)})
        return self._json(all_p)

    def _api_protocol(self, name):
        """Find protocol by name."""
        data = find_protocol_on_chains(name)
        self._json(data)

    def _api_cache_stats(self):
        """Cache statistics."""
        self._json({
            "entries": cache.size,
            "keys": list(cache._store.keys()),
        })


# ─────────────────────────────────────────────────────────────────────────────
# Server startup
# ─────────────────────────────────────────────────────────────────────────────
def main():
    host = "127.0.0.1"
    port = 8000

    # Parse args
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] in ("--port", "-p") and i + 1 < len(args):
            port = int(args[i + 1])
            i += 2
        elif args[i] in ("--host", "-H") and i + 1 < len(args):
            host = args[i + 1]
            i += 2
        elif args[i] in ("--help", "-h"):
            print(__doc__)
            return
        else:
            # Positional: port
            try:
                port = int(args[i])
            except ValueError:
                print(f"Unknown argument: {args[i]}")
                print("Usage: python server.py [--port PORT] [--host HOST]")
                return
            i += 1

    server = HTTPServer((host, port), MigrateAIHandler)
    url = f"http://{host}:{port}"
    print(f"""
╔══════════════════════════════════════════════════╗
║  🦀 MigrateAI API Server v0.1                   ║
║  AI-Powered Cross-Chain Migration Analyzer       ║
╠══════════════════════════════════════════════════╣
║  URL:  {url:<41s}║
║  API:  {url + '/api/health':<41s}║
╠══════════════════════════════════════════════════╣
║  Data: DeFi Llama · WormholeScan                 ║
║  Deps: Zero (Python stdlib only)                 ║
╚══════════════════════════════════════════════════╝
""")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
