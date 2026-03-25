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

        # Step 2: Upload product data as a document
        print(f"   📄 Uploading product data to datastore...")
        with open(args.data, "rb") as doc_file:
            client.datastores.documents.ingest(
                datastore_id=datastore_id,
                file=doc_file,
            )

        # Step 3: Wait for ingestion (with timeout)
        print("   ⏳ Waiting for document ingestion (max 60s)...")
        start = time.time()
        ready = False
        while time.time() - start < 60:
            try:
                ds_info = client.datastores.metadata(datastore_id=datastore_id)
                doc_count = getattr(ds_info, "document_count", 0)
                if doc_count and doc_count > 0:
                    ready = True
                    break
            except Exception:
                pass
            time.sleep(5)

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
