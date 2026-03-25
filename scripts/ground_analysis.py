#!/usr/bin/env python3
"""Ground competitive analysis with citations using Contextual AI."""

import argparse
import json
import os
import sys
import time
from datetime import datetime


def passthrough_report(report_text, reason):
    """Return report as-is when grounding is unavailable."""
    return report_text + f"\n\n---\n*⚠️ Grounding skipped: {reason}*\n"


def main():
    parser = argparse.ArgumentParser(description="Ground analysis with Contextual AI citations")
    parser.add_argument("--report", required=True, help="Path to analysis markdown file")
    parser.add_argument("--data", required=True, help="Path to scraped products JSON file")
    args = parser.parse_args()

    with open(args.report) as f:
        report_text = f.read()

    # Determine output file name
    base = os.path.basename(args.report).replace("_analysis_", "_grounded_").replace(".md", "")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"{base}_{timestamp}.md" if "_grounded_" not in base else f"{base}.md"

    api_key = os.environ.get("CONTEXTUAL_API_KEY", "")
    if not api_key:
        print("⚠️  CONTEXTUAL_API_KEY not set — skipping grounding")
        grounded = passthrough_report(report_text, "CONTEXTUAL_API_KEY not set")
        with open(output_file, "w") as f:
            f.write(grounded)
        print(f"📁 Output (ungrounded): {output_file}")
        print(output_file)
        return

    print("🔬 Grounding analysis with Contextual AI...")

    try:
        from contextual import ContextualAI

        client = ContextualAI(api_key=api_key)

        # Step 1: Create a datastore
        ds_name = f"shopify-monitor-{int(time.time())}"
        print(f"   📦 Creating datastore: {ds_name}")
        datastore = client.datastores.create(name=ds_name)
        datastore_id = datastore.id

        # Step 2: Convert JSON to HTML and upload (Contextual AI requires HTML/PDF)
        print(f"   📄 Converting product data to HTML and uploading...")
        import tempfile

        with open(args.data) as jf:
            product_data = json.load(jf)

        html = "<html><head><title>Product Data</title></head><body>\n"
        html += f"<h1>Products from {product_data.get('store_url', 'Unknown')}</h1>\n"
        html += f"<p>Scraped: {product_data.get('scraped_at', '')}, Count: {product_data.get('product_count', 0)}</p>\n"
        html += "<table border='1'><tr><th>Title</th><th>Price</th><th>Compare At</th><th>Type</th><th>Vendor</th><th>Available</th></tr>\n"
        for p in product_data.get("products", [])[:100]:  # Cap at 100 for fast ingestion
            avail = "Yes"
            if p.get("variants") and not p["variants"][0].get("available", True):
                avail = "No"
            html += f"<tr><td>{p.get('title','')}</td><td>${p.get('price','0')}</td>"
            html += f"<td>{p.get('compare_at_price','') or ''}</td>"
            html += f"<td>{p.get('product_type','')}</td><td>{p.get('vendor','')}</td>"
            html += f"<td>{avail}</td></tr>\n"
        html += "</table></body></html>"

        html_path = tempfile.mktemp(suffix=".html")
        with open(html_path, "w") as hf:
            hf.write(html)

        with open(html_path, "rb") as doc_file:
            client.datastores.documents.ingest(
                datastore_id=datastore_id,
                file=doc_file,
            )
        os.unlink(html_path)

        # Step 3: Wait for ingestion (with timeout)
        print("   ⏳ Waiting for document ingestion (max 180s)...")
        start = time.time()
        ready = False
        while time.time() - start < 180:
            try:
                docs = client.datastores.documents.list(datastore_id=datastore_id)
                for doc in docs.documents:
                    status = getattr(doc, "status", "unknown")
                    print(f"      Document status: {status}")
                    if status == "completed":
                        ready = True
                        break
                if ready:
                    break
            except Exception:
                pass
            time.sleep(10)

        if not ready:
            print("   ⚠️  Ingestion still processing — using async grounding note")
            grounded = report_text + "\n\n---\n*🔄 Contextual AI grounding is processing. Citations will be available shortly.*\n"
            with open(output_file, "w") as f:
                f.write(grounded)
            print(f"📁 Output: {output_file}")
            print(output_file)
            return

        # Step 4: Create agent linked to datastore
        print("   🤖 Creating grounding agent...")
        agent = client.agents.create(
            name="shopify-grounding-agent",
            datastore_ids=[datastore_id],
        )
        agent_id = agent.id

        # Step 5: Query the agent to verify claims
        print("   🔍 Verifying claims against source data...")
        query_prompt = (
            "Review the following competitive analysis report. For each factual claim, "
            "verify it against the source product data. Mark verified claims as [GROUNDED] "
            "and unverified claims as [UNVERIFIED]. Add specific citations from the product "
            "data where possible.\n\nReport:\n" + report_text
        )

        response = client.agents.query.create(
            agent_id=agent_id,
            messages=[{"role": "user", "content": query_prompt}],
        )

        grounded_text = response.message.content if hasattr(response, "message") else str(response)

        # Build final grounded report
        grounded = f"# Grounded Competitive Intelligence Report\n\n"
        grounded += f"*Verified by Contextual AI on {datetime.now().isoformat()}*\n\n"
        grounded += grounded_text

        # Add attribution info if available
        if hasattr(response, "attribution") and response.attribution:
            grounded += "\n\n## Source Citations\n\n"
            for attr in response.attribution:
                source = getattr(attr, "source", "product data")
                text = getattr(attr, "text", "")
                grounded += f"- **Source**: {source}\n  > {text}\n\n"

        print("   ✅ Grounding complete")

    except ImportError:
        print("⚠️  contextual-client not installed. Run: pip install contextual-client")
        grounded = passthrough_report(report_text, "contextual-client package not installed")
    except Exception as e:
        print(f"⚠️  Contextual AI error: {e}")
        grounded = passthrough_report(report_text, str(e))

    with open(output_file, "w") as f:
        f.write(grounded)

    print(f"\n📁 Grounded report: {output_file}")
    print(output_file)


if __name__ == "__main__":
    main()
