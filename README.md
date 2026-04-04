<div align="center">

```
 ░██████     ░██████  ░███     ░███ 
 ░██   ░██   ░██   ░██ ░████   ░████ 
░██         ░██        ░██░██ ░██░██ 
 ░████████  ░██        ░██ ░████ ░██ 
        ░██ ░██        ░██  ░██  ░██ 
 ░██   ░██   ░██   ░██ ░██       ░██ 
  ░██████     ░██████  ░██       ░██ 

 Shopify Competitor Monitor
```

### *Know your competition before they know you.*

<br/>

[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e.svg?style=flat-square)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11+-3b82f6.svg?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-Skill-f97316.svg?style=flat-square)](https://github.com/openclaw)
[![Apify](https://img.shields.io/badge/Apify-Scraping-00c2e0.svg?style=flat-square)](https://apify.com)
[![Redis](https://img.shields.io/badge/Redis-State-dc2626.svg?style=flat-square&logo=redis&logoColor=white)](https://redis.io)
[![FriendliAI](https://img.shields.io/badge/FriendliAI-Llama%203.3%2070B-8b5cf6.svg?style=flat-square)](https://friendli.ai)
[![Contextual AI](https://img.shields.io/badge/Contextual%20AI-RAG-0ea5e9.svg?style=flat-square)](https://contextual.ai)
[![Civic](https://img.shields.io/badge/Civic-Auth%20Gating-f59e0b.svg?style=flat-square)](https://civic.com)
[![Built at OpenClaw Hackathon](https://img.shields.io/badge/Built%20at-OpenClaw%20Hackathon%202025-e11d48.svg?style=flat-square)](#)

<br/>

> An **OpenClaw skill** that watches competitor Shopify stores around the clock —  
> detecting price changes, new product drops, and inventory shifts in real time,  
> then delivering AI-grounded intelligence reports with human-gated action control.

</div>

---

## What It Does

You give it a competitor's store URL. It watches. When something changes — a product launches, a price shifts, stock moves — it runs a full AI analysis, grounds every claim against the raw scraped data, and flags you for approval before doing anything about it.

Five integrations, one pipeline:

- **Apify** — scrapes stores that block public endpoints
- **Redis** — holds memory between scans so diffs are exact
- **FriendliAI** (Llama 3.3 70B) — turns raw diffs into strategic intelligence
- **Contextual AI** — grounds every claim with citations from the actual data
- **Civic** — gates every downstream action behind explicit human sign-off

---

## Architecture

```
User prompt
    │
    ▼
OpenClaw Agent ──reads──▶ SKILL.md (runbook)
    │
    ├─ Step 1 ──▶ scrape_store.py ─────────────────────────────────────┐
    │                 │                                                 │
    │                 ├── Shopify /products.json (public, free)        │
    │                 └── Apify fallback  (bot-protected stores)       │
    │                                                                  │
    ├─ Step 2 ──▶ cache_and_diff.py ◀─────────────────────────────────┘
    │                 │
    │                 ├── Redis  (snapshot store)
    │                 └── Structured diff  (new · removed · price Δ · stock Δ)
    │
    ├─ Step 3 ──▶ analyze_changes.py ──▶ FriendliAI  (Llama 3.3 70B)
    │                                          │
    │                                          └── Strategic insights + actions
    │
    ├─ Step 4 ──▶ ground_analysis.py ──▶ Contextual AI  (RAG + citations)
    │                                          │
    │                                          └── Verified claims · confidence scores
    │
    ├─ Step 5 ──▶ Report delivered to user
    │
    └─ Step 6 ──▶ gate_action.py ──▶ Civic  (human-in-the-loop)
                                          │
                                     ┌────┴────┐
                                  Approved   Denied
                                     │
                               Action executes
```

---

## Quick Start

### Install via OpenClaw

```bash
npx clawhub@latest install usmanjameel/shopify-competitor-monitor
```

### Or clone manually

```bash
git clone https://github.com/UJameel/shopify-competitor-monitor.git
cd shopify-competitor-monitor
pip install -r requirements.txt
cp config.json.example config.json
```

### Configure environment variables

```bash
# Scraping — extends reach to non-Shopify / bot-protected stores
export APIFY_API_TOKEN="your-apify-token"

# State — enables precise diffs across runs
export REDIS_URL="redis://localhost:6379"

# AI analysis — fast Llama 3.3 70B inference
export FRIENDLI_TOKEN="your-friendli-token"

# Grounding — citations backed by real scraped data
export CONTEXTUAL_API_KEY="your-contextual-key"

# Action gating — nothing executes without human approval
export CIVIC_URL="your-civic-mcp-url"
export CIVIC_TOKEN="your-civic-token"
```

> Every integration has a graceful fallback — the skill runs with zero API keys,
> using free Shopify endpoints, local file cache, and plain structured reports.

### Tell your agent

```
"Monitor gymshark.com for price changes"
"Track new product drops on youngla.com"
"Run a competitive analysis on alphaleteathletics.com"
"Compare pricing across these competitors: ..."
```

---

## Standalone Script Usage

Each script runs independently — useful for testing, debugging, or wiring into your own pipelines.

```bash
# 1. Scrape a store
python3 scripts/scrape_store.py --store https://www.gymshark.com

# 2. Cache snapshot and generate a diff  (run twice to see changes)
python3 scripts/cache_and_diff.py --store https://www.gymshark.com --data gymshark_products_*.json

# 3. Analyze the diff with FriendliAI
python3 scripts/analyze_changes.py --diff gymshark_diff_*.json

# 4. Ground the analysis with Contextual AI citations
python3 scripts/ground_analysis.py --report gymshark_analysis_*.md --data gymshark_products_*.json

# 5. Gate an action through Civic
python3 scripts/gate_action.py --action "Lower prices on competing items by 5%"
```

---

## Sponsor Integrations

| Sponsor | Role | Script | Fallback |
|---|---|---|---|
| **Apify** | Web scraping for stores behind bot protection | `scrape_store.py` | Free Shopify `/products.json` |
| **Redis** | Stateful memory — snapshots between scans | `cache_and_diff.py` | Local JSON file cache |
| **FriendliAI** | Llama 3.3 70B inference for competitive analysis | `analyze_changes.py` | Structured markdown report |
| **Contextual AI** | RAG-grounded citations against scraped data | `ground_analysis.py` | Pass-through (ungrounded) |
| **Civic** | Human-in-the-loop authorization before any action | `gate_action.py` | Manual terminal approval |

---

## How Each Step Works

**Scrape** — Hits the store's public `/products.json` endpoint and pulls the full catalog. For stores without one, or that block it, Apify's scraping infrastructure takes over.

**Cache & Diff** — Snapshots the catalog in Redis and compares it to the previous run. Surfaces exactly what changed: new products, removals, price increases, price decreases, stock movements.

**Analyze** — Sends the structured diff to FriendliAI running Llama 3.3 70B. Returns competitive intelligence: what the changes signal, how they compare to market patterns, what actions to consider.

**Ground** — Passes the analysis through Contextual AI, which verifies every claim against the actual scraped data and adds inline citations with confidence scores. No hallucinations reach you.

**Gate** — Before the agent touches anything in your store, sends any alert, or triggers any downstream action, Civic requires explicit human authorization. You approve or deny. If you deny, nothing happens.

---

## License

```
MIT License — Copyright (c) 2025 Usman Jameel
```

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files, to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, subject to the following conditions: The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

---

<div align="center">

Built at the **OpenClaw Hackathon 2025**

Powered by **Apify · Redis · FriendliAI · Contextual AI · Civic**

</div>
