#!/usr/bin/env python3
"""Generate competitive intelligence report from product diffs using FriendliAI."""

import argparse
import json
import os
import sys
from datetime import datetime


def format_diff_as_text(diff_data):
    """Format diff data into readable text for the LLM."""
    lines = [f"Store: {diff_data.get('store', 'Unknown')}"]
    lines.append(f"Scan time: {diff_data.get('timestamp', 'Unknown')}")

    s = diff_data.get("summary", {})
    lines.append(f"\nProducts: {s.get('total_products_previous', '?')} → {s.get('total_products_current', '?')}")

    changes = diff_data.get("changes", {})

    if changes.get("new_products"):
        lines.append("\n--- NEW PRODUCTS ---")
        for p in changes["new_products"]:
            lines.append(f"  + {p['title']} — ${p.get('price', '?')} ({p.get('product_type', 'N/A')})")

    if changes.get("removed_products"):
        lines.append("\n--- REMOVED PRODUCTS ---")
        for p in changes["removed_products"]:
            lines.append(f"  - {p['title']} — was ${p.get('price', '?')}")

    if changes.get("price_increases"):
        lines.append("\n--- PRICE INCREASES ---")
        for p in changes["price_increases"]:
            lines.append(f"  ↑ {p['title']}: ${p['old_price']} → ${p['new_price']} ({p['change_percent']})")

    if changes.get("price_decreases"):
        lines.append("\n--- PRICE DECREASES ---")
        for p in changes["price_decreases"]:
            lines.append(f"  ↓ {p['title']}: ${p['old_price']} → ${p['new_price']} ({p['change_percent']})")

    if changes.get("back_in_stock"):
        lines.append("\n--- BACK IN STOCK ---")
        for p in changes["back_in_stock"]:
            lines.append(f"  ✅ {p['title']}")

    if changes.get("out_of_stock"):
        lines.append("\n--- OUT OF STOCK ---")
        for p in changes["out_of_stock"]:
            lines.append(f"  ❌ {p['title']}")

    return "\n".join(lines)


def generate_fallback_report(diff_data):
    """Generate a simple report without LLM."""
    store = diff_data.get("store", "Unknown")
    s = diff_data.get("summary", {})
    changes = diff_data.get("changes", {})

    lines = [f"# Competitive Intelligence Report: {store}\n"]
    lines.append(f"*Generated: {datetime.now().isoformat()}*\n")
    lines.append("## Summary\n")
    lines.append(f"- **Total products**: {s.get('total_products_previous', '?')} → {s.get('total_products_current', '?')}")
    lines.append(f"- **New products**: {s.get('new_products', 0)}")
    lines.append(f"- **Removed products**: {s.get('removed_products', 0)}")
    lines.append(f"- **Price increases**: {s.get('price_increases', 0)}")
    lines.append(f"- **Price decreases**: {s.get('price_decreases', 0)}")
    lines.append(f"- **Stock changes**: {s.get('back_in_stock', 0)} back, {s.get('out_of_stock', 0)} out\n")

    if changes.get("price_increases") or changes.get("price_decreases"):
        lines.append("## Price Changes\n")
        lines.append("| Product | Old Price | New Price | Change |")
        lines.append("|---------|-----------|-----------|--------|")
        for p in changes.get("price_increases", []):
            lines.append(f"| {p['title']} | ${p['old_price']} | ${p['new_price']} | {p['change_percent']} |")
        for p in changes.get("price_decreases", []):
            lines.append(f"| {p['title']} | ${p['old_price']} | ${p['new_price']} | {p['change_percent']} |")
        lines.append("")

    if changes.get("new_products"):
        lines.append("## New Products\n")
        for p in changes["new_products"]:
            lines.append(f"- **{p['title']}** — ${p.get('price', '?')} ({p.get('product_type', '')})")
        lines.append("")

    if changes.get("removed_products"):
        lines.append("## Removed Products\n")
        for p in changes["removed_products"]:
            lines.append(f"- **{p['title']}** — was ${p.get('price', '?')}")
        lines.append("")

    lines.append("\n*⚠️ Analysis generated without FriendliAI (FRIENDLI_TOKEN not set). Set FRIENDLI_TOKEN for AI-powered strategic insights.*")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate competitive analysis from diff")
    parser.add_argument("--diff", required=True, help="Path to diff JSON file")
    args = parser.parse_args()

    with open(args.diff) as f:
        diff_data = json.load(f)

    store = diff_data.get("store", "unknown")
    store_name = store.split(".")[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"{store_name}_analysis_{timestamp}.md"

    # Check if this is just a baseline (no changes)
    if diff_data.get("baseline"):
        report = f"# Baseline Scan: {store}\n\n"
        report += f"*Generated: {datetime.now().isoformat()}*\n\n"
        report += f"First scan complete. {diff_data['summary']['total_products_current']} products catalogued.\n"
        report += "Run again after the next scan to see changes.\n"

        with open(output_file, "w") as f:
            f.write(report)
        print(f"📝 Baseline report written to {output_file}")
        print(output_file)
        return

    friendli_token = os.environ.get("FRIENDLI_TOKEN", "")
    diff_text = format_diff_as_text(diff_data)

    if not friendli_token:
        print("⚠️  FRIENDLI_TOKEN not set — generating report without AI analysis")
        report = generate_fallback_report(diff_data)
    else:
        print("🤖 Sending diff to FriendliAI for analysis...")
        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=friendli_token,
                base_url="https://api.friendli.ai/serverless/v1",
            )

            response = client.chat.completions.create(
                model="meta-llama-3.3-70b-instruct",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a competitive intelligence analyst for ecommerce brands. "
                            "Analyze the following product changes from a competitor's Shopify store. "
                            "Provide strategic insights about what these changes suggest about their strategy. "
                            "Format your response in markdown with these sections:\n"
                            "## Summary\n## Price Changes Analysis\n## Product Strategy Insights\n"
                            "## Recommended Actions\n"
                            "Be specific, actionable, and data-driven."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Analyze these competitor product changes:\n\n{diff_text}",
                    },
                ],
                max_tokens=2000,
                temperature=0.7,
            )

            ai_analysis = response.choices[0].message.content
            report = f"# Competitive Intelligence Report: {store}\n\n"
            report += f"*Generated: {datetime.now().isoformat()} | Powered by FriendliAI*\n\n"
            report += ai_analysis
            print("✅ FriendliAI analysis complete")

        except Exception as e:
            print(f"⚠️  FriendliAI error: {e}")
            print("   Falling back to structured report...")
            report = generate_fallback_report(diff_data)

    with open(output_file, "w") as f:
        f.write(report)

    print(f"\n📊 Analysis written to {output_file}")
    print(output_file)


if __name__ == "__main__":
    main()
