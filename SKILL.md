---
name: shopify-competitor-monitor
description: Monitor competitor Shopify stores for price changes, new products, inventory shifts, and strategic competitive insights. Uses Apify for live web scraping, Redis for state tracking and memory, FriendliAI for fast AI-powered analysis, Contextual AI for grounded citations, and Civic for action authorization. Use when the user says "monitor competitors", "track competitor prices", "shopify competitor analysis", "watch store for changes", "competitive intelligence", "price tracking", or mentions tracking another store's products or pricing. Also trigger when user asks to compare their store with competitors or wants alerts on competitor activity.
version: 1.0.0
metadata:
  openclaw:
    requires:
      env:
        - APIFY_API_TOKEN
        - REDIS_URL
        - FRIENDLI_TOKEN
        - CONTEXTUAL_API_KEY
      bins:
        - python3
      primaryEnv: APIFY_API_TOKEN
    emoji: "🔍"
---

# Shopify Competitor Monitor

Monitor competitor Shopify stores and generate competitive intelligence reports with grounded analysis and safe action gating.

## When to use

Trigger when the user asks to monitor, track, or analyze competitor Shopify stores, prices, products, or inventory. Also trigger when the user mentions competitive intelligence, price tracking, or watching a store for changes.

## Setup

Ensure dependencies are installed:

```bash
pip install -r {baseDir}/requirements.txt
```

## Workflow

### Step 1: Identify target stores

Ask the user which Shopify store(s) they want to monitor. Accept one or more URLs. If the user provides a domain without protocol, prepend `https://`. If a config file exists at `{baseDir}/config.json`, offer to use the stores listed there.

### Step 2: Scrape competitor store(s)

For each store URL the user provides, run the scraper:

```bash
python3 {baseDir}/scripts/scrape_store.py --store <STORE_URL>
```

This uses the free Shopify `/products.json` endpoint first, falling back to Apify for non-Shopify stores. Capture the output JSON file path printed to stdout.

If scraping multiple stores, run them sequentially and collect all output paths.

### Step 3: Cache and diff against previous scan

For each scraped store, run:

```bash
python3 {baseDir}/scripts/cache_and_diff.py --store <STORE_URL> --data <JSON_PATH>
```

This stores the current snapshot in Redis (or local cache) and computes a diff against the last scan. On first run, it establishes a baseline. Capture the diff JSON file path printed to stdout.

### Step 4: Generate competitive analysis

For each diff that contains changes (not just a baseline), run:

```bash
python3 {baseDir}/scripts/analyze_changes.py --diff <DIFF_PATH>
```

This sends the diff to FriendliAI for fast AI-powered competitive analysis. Capture the analysis markdown file path printed to stdout.

### Step 5: Ground the analysis with citations

If `CONTEXTUAL_API_KEY` is available and the user wants grounded analysis, run:

```bash
python3 {baseDir}/scripts/ground_analysis.py --report <ANALYSIS_PATH> --data <JSON_PATH>
```

This uses Contextual AI to verify every claim in the analysis against actual scraped product data. Each claim gets a [GROUNDED] or [UNVERIFIED] tag with citations. Skip this step if the env var is not set or the user wants quick results.

### Step 6: Present results

Format the final report for the user. Include:

- **Summary**: Total products scanned, number of changes detected
- **Price Changes** (markdown table): Product name, old price, new price, percent change
- **New Products** (bullet list): Product name, price, category
- **Removed Products** (bullet list): Product name, last known price
- **Stock Changes** (bullet list): Products that went in/out of stock
- **Strategic Insights**: What the changes suggest about competitor strategy
- **Recommended Actions**: What the user should consider doing in response

### Step 7: Gate actions with Civic authorization

If the user wants to take action based on the intelligence (adjust their own prices, alert their team, trigger marketing campaigns, restock items), ALWAYS run the gate first:

```bash
python3 {baseDir}/scripts/gate_action.py --action "<DESCRIPTION_OF_ACTION>"
```

This requires human authorization via Civic before proceeding. Do NOT execute any actions without completing this step and receiving "APPROVED" output.

If the gate returns "DENIED", inform the user that the action was not authorized and ask if they want to modify the action or proceed differently.

## Multi-store monitoring

When monitoring multiple stores, present a combined report with per-store sections and a cross-store summary highlighting the most significant changes across all competitors.

## Scheduling

If the user wants recurring monitoring, suggest they set up a cron job or use their CI/CD pipeline to run the scrape → diff → analyze pipeline on their preferred interval. The Redis state layer ensures each run compares against the previous scan automatically.
