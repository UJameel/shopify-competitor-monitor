#!/usr/bin/env python3
"""Cache product snapshots in Redis (or local files) and compute diffs."""

import argparse
import json
import os
import sys
from datetime import datetime
from urllib.parse import urlparse

# Try Redis, fall back gracefully
try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False


def get_domain(url):
    parsed = urlparse(url)
    return (parsed.netloc or parsed.path).replace("www.", "")


class RedisCache:
    def __init__(self, redis_url):
        self.client = redis.from_url(redis_url, decode_responses=True)
        self.client.ping()
        print("📡 Connected to Redis")

    def get(self, key):
        data = self.client.get(key)
        return json.loads(data) if data else None

    def set(self, key, value, ttl=86400 * 30):
        self.client.set(key, json.dumps(value), ex=ttl)
        print(f"   💾 Redis SET {key} (TTL: {ttl}s)")


class LocalCache:
    def __init__(self):
        self.cache_dir = os.path.join(os.path.dirname(__file__), "..", ".cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        print("📂 Using local file cache (no Redis)")

    def _path(self, key):
        safe_key = key.replace(":", "_").replace("/", "_")
        return os.path.join(self.cache_dir, f"{safe_key}.json")

    def get(self, key):
        path = self._path(key)
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return None

    def set(self, key, value, ttl=None):
        path = self._path(key)
        with open(path, "w") as f:
            json.dump(value, f, indent=2)
        print(f"   💾 Cached to {path}")


def build_product_index(products):
    """Index products by handle for fast comparison."""
    return {p["handle"]: p for p in products if p.get("handle")}


def compute_diff(old_products, new_products, domain):
    """Compute structured diff between two product snapshots."""
    old_idx = build_product_index(old_products)
    new_idx = build_product_index(new_products)

    old_handles = set(old_idx.keys())
    new_handles = set(new_idx.keys())

    added = new_handles - old_handles
    removed = old_handles - new_handles
    common = old_handles & new_handles

    new_products_list = [
        {"title": new_idx[h]["title"], "handle": h, "price": new_idx[h].get("price", "0.00"),
         "product_type": new_idx[h].get("product_type", "")}
        for h in added
    ]

    removed_products_list = [
        {"title": old_idx[h]["title"], "handle": h, "price": old_idx[h].get("price", "0.00")}
        for h in removed
    ]

    price_increases, price_decreases = [], []
    back_in_stock, out_of_stock = [], []

    for h in common:
        old_p, new_p = old_idx[h], new_idx[h]

        # Price comparison
        try:
            old_price = float(old_p.get("price", 0))
            new_price = float(new_p.get("price", 0))
        except (ValueError, TypeError):
            continue

        if old_price != new_price and old_price > 0:
            change = {"title": new_p["title"], "handle": h,
                      "old_price": f"{old_price:.2f}", "new_price": f"{new_price:.2f}",
                      "change_percent": f"{((new_price - old_price) / old_price) * 100:.1f}%"}
            if new_price > old_price:
                price_increases.append(change)
            else:
                price_decreases.append(change)

        # Stock comparison (check first variant)
        old_avail = old_p.get("variants", [{}])[0].get("available", True) if old_p.get("variants") else True
        new_avail = new_p.get("variants", [{}])[0].get("available", True) if new_p.get("variants") else True

        if not old_avail and new_avail:
            back_in_stock.append({"title": new_p["title"], "handle": h})
        elif old_avail and not new_avail:
            out_of_stock.append({"title": new_p["title"], "handle": h})

    return {
        "store": domain,
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_products_current": len(new_products),
            "total_products_previous": len(old_products),
            "new_products": len(new_products_list),
            "removed_products": len(removed_products_list),
            "price_increases": len(price_increases),
            "price_decreases": len(price_decreases),
            "back_in_stock": len(back_in_stock),
            "out_of_stock": len(out_of_stock),
        },
        "changes": {
            "new_products": new_products_list,
            "removed_products": removed_products_list,
            "price_increases": price_increases,
            "price_decreases": price_decreases,
            "back_in_stock": back_in_stock,
            "out_of_stock": out_of_stock,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Cache product data and compute diffs")
    parser.add_argument("--store", required=True, help="Store URL")
    parser.add_argument("--data", required=True, help="Path to scraped products JSON")
    args = parser.parse_args()

    domain = get_domain(args.store)
    key_latest = f"shopify_monitor:{domain}:latest"
    key_previous = f"shopify_monitor:{domain}:previous"

    # Load new data
    with open(args.data) as f:
        new_data = json.load(f)
    new_products = new_data.get("products", [])

    # Connect to cache
    redis_url = os.environ.get("REDIS_URL", "")
    if redis_url and HAS_REDIS:
        try:
            cache = RedisCache(redis_url)
        except Exception as e:
            print(f"⚠️  Redis connection failed ({e}), using local cache")
            cache = LocalCache()
    else:
        if not redis_url:
            print("⚠️  REDIS_URL not set")
        cache = LocalCache()

    # Get previous snapshot
    previous_data = cache.get(key_latest)

    if previous_data is None:
        # First run — establish baseline
        cache.set(key_latest, new_products)
        cache.set(key_previous, new_products)

        store_name = domain.split(".")[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        diff_file = f"{store_name}_diff_{timestamp}.json"

        baseline = {
            "store": domain,
            "timestamp": datetime.now().isoformat(),
            "baseline": True,
            "summary": {
                "total_products_current": len(new_products),
                "new_products": 0, "removed_products": 0,
                "price_increases": 0, "price_decreases": 0,
                "back_in_stock": 0, "out_of_stock": 0,
            },
            "changes": {
                "new_products": [], "removed_products": [],
                "price_increases": [], "price_decreases": [],
                "back_in_stock": [], "out_of_stock": [],
            },
        }

        with open(diff_file, "w") as f:
            json.dump(baseline, f, indent=2)

        print(f"\n🆕 Baseline established. {len(new_products)} products catalogued for {domain}.")
        print(f"📁 Diff: {diff_file}")
        print(diff_file)
    else:
        # Subsequent run — compute diff
        cache.set(key_previous, previous_data)
        cache.set(key_latest, new_products)

        diff = compute_diff(previous_data, new_products, domain)

        store_name = domain.split(".")[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        diff_file = f"{store_name}_diff_{timestamp}.json"

        with open(diff_file, "w") as f:
            json.dump(diff, f, indent=2)

        s = diff["summary"]
        print(f"\n📊 Diff computed for {domain}:")
        print(f"   📦 Products: {s['total_products_previous']} → {s['total_products_current']}")
        print(f"   🆕 New: {s['new_products']}  🗑️  Removed: {s['removed_products']}")
        print(f"   📈 Price increases: {s['price_increases']}  📉 Price decreases: {s['price_decreases']}")
        print(f"   ✅ Back in stock: {s['back_in_stock']}  ❌ Out of stock: {s['out_of_stock']}")
        print(f"📁 Diff: {diff_file}")
        print(diff_file)


if __name__ == "__main__":
    main()
