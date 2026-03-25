#!/usr/bin/env python3
"""Scrape products from a Shopify store using /products.json or Apify fallback."""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from urllib.parse import urlparse

import requests

# Browser-like headers to bypass basic 403 blocks
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
}


def get_store_name(url):
    """Extract a clean store name from URL."""
    domain = urlparse(url).netloc or urlparse(url).path
    domain = domain.replace("www.", "")
    return re.sub(r"[^a-zA-Z0-9]", "_", domain.split(".")[0])


def scrape_shopify_direct(store_url):
    """Scrape products via the free Shopify /products.json endpoint."""
    base = store_url.rstrip("/")
    all_products = []
    page = 1

    print(f"🔍 Scraping {base}/products.json ...")

    session = requests.Session()
    session.headers.update(BROWSER_HEADERS)

    # First visit the homepage to get cookies (bypass some bot detection)
    try:
        session.get(base, timeout=15)
    except Exception:
        pass

    while True:
        url = f"{base}/products.json?limit=250&page={page}"
        try:
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            if page == 1:
                raise  # First page failed — not a Shopify store or blocked
            break  # Pagination ended

        data = resp.json()
        products = data.get("products", [])
        if not products:
            break

        all_products.extend(products)
        print(f"   📦 Page {page}: fetched {len(products)} products (total: {len(all_products)})")

        if len(products) < 250:
            break
        page += 1
        time.sleep(0.5)  # Be polite

    return all_products


def scrape_via_apify(store_url, api_token):
    """Fall back to Apify web scraper for any store."""
    print(f"🔄 Falling back to Apify web scraper...")

    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}

    # Try multiple Shopify scraper actors in order of reliability
    actors = [
        ("logie~shopify-products-scraper", {
            "startUrls": [{"url": store_url}],
            "maxProducts": 500,
            "proxyConfiguration": {"useApifyProxy": True},
        }),
        ("autofacts~shopify", {
            "startUrls": [{"url": store_url}],
            "maxProducts": 500,
        }),
        ("pocesar~shopify-scraper", {
            "startUrls": [{"url": store_url}],
        }),
    ]

    resp = None
    for actor_id, payload in actors:
        print(f"   🛒 Trying actor: {actor_id}...")
        run_url = f"https://api.apify.com/v2/acts/{actor_id}/runs"
        try:
            resp = requests.post(run_url, json=payload, headers=headers, timeout=30)
            if resp.status_code in (200, 201):
                print(f"   ✅ Actor {actor_id} started successfully")
                break
            print(f"   ⚠️  Actor {actor_id} returned {resp.status_code}")
        except Exception as e:
            print(f"   ⚠️  Actor {actor_id} failed: {e}")
            resp = None
            continue

    if not resp or resp.status_code not in (200, 201):
        raise RuntimeError("All Apify actors failed to start")

    run_data = resp.json()["data"]
    run_id = run_data["id"]
    dataset_id = run_data["defaultDatasetId"]

    print(f"   🚀 Apify run started: {run_id}")

    # Poll until finished (max 180s)
    status_url = f"https://api.apify.com/v2/actor-runs/{run_id}"
    for _ in range(36):
        time.sleep(5)
        try:
            status_resp = requests.get(status_url, headers=headers, timeout=15).json()
            status = status_resp["data"]["status"]
        except Exception:
            continue
        if status == "SUCCEEDED":
            break
        if status in ("FAILED", "ABORTED", "TIMED-OUT"):
            raise RuntimeError(f"Apify run {status}")
        print(f"   ⏳ Apify status: {status}")
    else:
        raise RuntimeError("Apify run timed out after 180s")

    # Fetch results
    dataset_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?format=json"
    items = requests.get(dataset_url, headers=headers, timeout=30).json()
    print(f"   📦 Apify returned {len(items)} products")
    return items


def normalize_product(product):
    """Normalize a product dict to a consistent schema."""
    variants = []
    for v in product.get("variants", []):
        variants.append({
            "id": v.get("id"),
            "title": v.get("title", "Default"),
            "price": v.get("price", "0.00"),
            "compare_at_price": v.get("compare_at_price"),
            "available": v.get("available", True),
            "sku": v.get("sku", ""),
        })

    images = [img.get("src", "") for img in product.get("images", [])]

    # Handle Apify web scraper output format (flatter structure)
    price = product.get("price", "0.00")
    if variants:
        price = variants[0]["price"]
    elif isinstance(price, str) and price.replace(".", "").isdigit():
        pass  # Already a price string
    elif isinstance(price, (int, float)):
        price = f"{price:.2f}"

    return {
        "id": product.get("id", hash(product.get("handle", product.get("title", "")))),
        "title": product.get("title", "Unknown"),
        "handle": product.get("handle", ""),
        "vendor": product.get("vendor", ""),
        "product_type": product.get("product_type", ""),
        "tags": product.get("tags", []) if isinstance(product.get("tags"), list)
                else [t.strip() for t in str(product.get("tags", "")).split(",") if t.strip()],
        "variants": variants,
        "price": price,
        "compare_at_price": variants[0]["compare_at_price"] if variants else product.get("compare_at_price"),
        "images": images,
        "created_at": product.get("created_at", ""),
        "updated_at": product.get("updated_at", ""),
    }


def main():
    parser = argparse.ArgumentParser(description="Scrape a Shopify store's products")
    parser.add_argument("--store", required=True, help="Store URL (e.g. https://www.gymshark.com)")
    parser.add_argument("--apify-token", default=None, help="Apify API token (or set APIFY_API_TOKEN)")
    args = parser.parse_args()

    store_url = args.store.rstrip("/")
    if not store_url.startswith("http"):
        store_url = "https://" + store_url

    apify_token = args.apify_token or os.environ.get("APIFY_API_TOKEN", "")
    store_name = get_store_name(store_url)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Try direct Shopify endpoint first
    products = []
    try:
        raw_products = scrape_shopify_direct(store_url)
        products = [normalize_product(p) for p in raw_products]
    except Exception as e:
        print(f"   ⚠️  Direct scrape failed: {e}")
        if apify_token:
            try:
                raw_products = scrape_via_apify(store_url, apify_token)
                products = [normalize_product(p) for p in raw_products]
            except Exception as e2:
                print(f"   ❌ Apify fallback also failed: {e2}")
                sys.exit(1)
        else:
            print("   ⚠️  No APIFY_API_TOKEN set — cannot fall back to Apify.")
            print("   💡 Set APIFY_API_TOKEN to scrape non-Shopify stores.")
            sys.exit(1)

    if not products:
        print("❌ No products found.")
        sys.exit(1)

    # Write output
    output_file = f"{store_name}_products_{timestamp}.json"
    output_data = {
        "store_url": store_url,
        "store_name": store_name,
        "scraped_at": datetime.now().isoformat(),
        "product_count": len(products),
        "products": products,
    }

    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"\n✅ Scraped {len(products)} products from {store_url}")
    print(f"📁 Output: {output_file}")
    # Print just the path on last line for agent to capture
    print(output_file)


if __name__ == "__main__":
    main()
