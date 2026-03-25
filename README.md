# shopify-competitor-monitor

An OpenClaw skill that monitors competitor Shopify stores for price changes, new products, and inventory shifts — then generates AI-powered competitive intelligence reports. Built with five sponsor integrations: Apify for live web scraping, Redis for stateful memory across scans, FriendliAI for fast natural language analysis, Contextual AI for grounded citations, and Civic for safe action gating.

## Architecture

```
User
 │
 ▼
OpenClaw Agent ──reads──▶ SKILL.md (runbook)
 │
 ├─ Step 1 ──▶ scrape_store.py ──▶ Shopify /products.json + Apify fallback
 │                                       │
 ├─ Step 2 ──▶ cache_and_diff.py ◀──────┘
 │                  │
 │                  ▼
 │              Redis (state store)
 │                  │ snapshot diff
 │                  ▼
 ├─ Step 3 ──▶ analyze_changes.py ──▶ FriendliAI (Llama 3.3 70B)
 │                                       │
 │                                       ▼
 ├─ Step 4 ──▶ ground_analysis.py ──▶ Contextual AI (RAG + citations)
 │                                       │
 │                                       ▼
 ├─ Step 5 ──▶ Present report to user
 │
 └─ Step 6 ──▶ gate_action.py ──▶ Civic (human-in-the-loop auth)
                                       │
                                       ▼
                                  Execute or deny
```

## Quick Start

### 1. Install the skill

```bash
npx clawhub@latest install usmanjameel/shopify-competitor-monitor
```

Or clone manually:

```bash
git clone https://github.com/usmanjameel/shopify-competitor-monitor.git
cd shopify-competitor-monitor
pip install -r requirements.txt
```

### 2. Set environment variables

```bash
# Required for full functionality (each enables graceful fallback if missing)
export APIFY_API_TOKEN="your-apify-token"       # Extends scraping to non-Shopify stores
export REDIS_URL="redis://localhost:6379"         # State memory (falls back to local files)
export FRIENDLI_TOKEN="your-friendli-token"       # AI analysis (falls back to structured report)
export CONTEXTUAL_API_KEY="your-contextual-key"   # Grounded citations (optional)
export CIVIC_URL="your-civic-mcp-url"             # Action gating (falls back to manual approval)
export CIVIC_TOKEN="your-civic-token"             # Action gating
```

### 3. Use it

Tell your OpenClaw agent:

- "Monitor gymshark.com for price changes"
- "Track competitor products on youngla.com"
- "Run a competitive analysis on alphaleteathletics.com"
- "Compare my competitors' pricing — here are their stores: ..."

### 4. Standalone testing

Each script works independently:

```bash
# Scrape a store
python3 scripts/scrape_store.py --store https://www.gymshark.com

# Cache and diff (run twice to see changes)
python3 scripts/cache_and_diff.py --store https://www.gymshark.com --data gymshark_products_*.json

# Generate analysis
python3 scripts/analyze_changes.py --diff gymshark_diff_*.json

# Ground with citations
python3 scripts/ground_analysis.py --report gymshark_analysis_*.md --data gymshark_products_*.json

# Gate an action
python3 scripts/gate_action.py --action "Lower prices on competing items by 5%"
```

## Sponsor Integrations

| Sponsor | Role | Script | Fallback |
|---------|------|--------|----------|
| **Apify** | Web scraping for non-Shopify stores | `scrape_store.py` | Free Shopify /products.json endpoint |
| **Redis** | State memory for snapshot diffs | `cache_and_diff.py` | Local JSON file cache |
| **FriendliAI** | Fast LLM inference for analysis | `analyze_changes.py` | Structured markdown report |
| **Contextual AI** | Grounded RAG with citations | `ground_analysis.py` | Pass-through (ungrounded) |
| **Civic** | Human-in-the-loop action auth | `gate_action.py` | Manual terminal approval |

## How It Works

1. **Scrape**: Fetches all products from a Shopify store's public `/products.json` endpoint. For non-Shopify stores, falls back to Apify's scraping infrastructure.

2. **Cache & Diff**: Stores the product snapshot in Redis and compares it against the previous scan. Detects new products, removed products, price increases/decreases, and stock changes.

3. **Analyze**: Sends the structured diff to FriendliAI (Llama 3.3 70B) for competitive intelligence analysis with strategic insights and recommended actions.

4. **Ground**: Uses Contextual AI to verify every claim in the analysis against the actual scraped data, adding citations and confidence tags.

5. **Gate**: Before the agent takes any action based on the intelligence (price adjustments, team alerts, campaigns), Civic requires explicit human authorization.

## License

MIT

---

Built at the OpenClaw Hackathon 2025. Powered by Apify, Redis, FriendliAI, Contextual AI, and Civic.
