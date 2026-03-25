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

    while True:
        url = f"{base}/products.json?limit=250&page={page}"
        try:
            resp = requests.get(url, timeout=30, headers={
                "User-Agent": "Mozilla/5.0 (compatible; ShopifyMonitor/1.0)"
            })
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
    """Fall back to Apify actor for non-Shopify stores."""
    print(f"🔄 Direct endpoint failed. Falling back to Apify scraper...")

    actor_id = "dainty_screw~shopify-products-scraper"
    run_url = f"https://api.apify.com/v2/acts/{actor_id}/runs"

    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    payload = {"startUrls": [{"url": store_url}], "maxProducts": 500}

    # Start the actor run
    resp = requests.post(run_url, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    run_data = resp.json()["data"]
    run_id = run_data["id"]
    dataset_id = run_data["defaultDatasetId"]

    print(f"   🚀 Apify run started: {run_id}")

    # Poll until finished (max 120s)
    status_url = f"https://api.apify.com/v2/actor-runs/{run_id}"
    for _ in range(24):
        time.sleep(5)
        status = requests.get(status_url, headers=headers, timeout=15).json()["data"]["status"]
        if status == "SUCCEEDED":
            break
        if status in ("FAILED", "ABORTED", "TIMED-OUT"):
            raise RuntimeError(f"Apify run {status}")
        print(f"   ⏳ Apify run status: {status}")
    else:
        raise RuntimeError("Apify run timed out after 120s")

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

    return {
        "id": product.get("id"),
        "title": product.get("title", "Unknown"),
        "handle": product.get("handle", ""),
        "vendor": product.get("vendor", ""),
        "product_type": product.get("product_type", ""),
        "tags": product.get("tags", []) if isinstance(product.get("tags"), list)
                else [t.strip() for t in product.get("tags", "").split(",") if t.strip()],
        "variants": variants,
        "price": variants[0]["price"] if variants else "0.00",
        "compare_at_price": variants[0]["compare_at_price"] if variants else None,
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
