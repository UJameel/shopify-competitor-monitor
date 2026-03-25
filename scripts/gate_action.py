#!/usr/bin/env python3
"""Gate agent actions through Civic authorization for human-in-the-loop safety."""

import argparse
import json
import os
import sys
from datetime import datetime

import requests


def main():
    parser = argparse.ArgumentParser(description="Gate actions via Civic authorization")
    parser.add_argument("--action", required=True, help="Description of the proposed action")
    args = parser.parse_args()

    civic_url = os.environ.get("CIVIC_URL", "")
    civic_token = os.environ.get("CIVIC_TOKEN", "")

    print(f"🛡️  Action gate requested:")
    print(f"   Action: {args.action}")
    print(f"   Time: {datetime.now().isoformat()}")

    if civic_url and civic_token:
        # Use Civic MCP gateway for authorization via JSON-RPC (MCP protocol)
        print("   🔐 Checking Civic authorization...")
        try:
            headers = {
                "Authorization": f"Bearer {civic_token}",
                "Content-Type": "application/json",
            }
            # Civic uses MCP (JSON-RPC 2.0) protocol
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "authorize_action",
                    "arguments": {
                        "action": args.action,
                        "timestamp": datetime.now().isoformat(),
                        "source": "shopify-competitor-monitor",
                    },
                },
            }
            resp = requests.post(
                civic_url,
                json=payload,
                headers=headers,
                timeout=15,
            )

            if resp.status_code == 200:
                result = resp.json()
                rpc_result = result.get("result", {})
                content = rpc_result.get("content", [{}])
                text = content[0].get("text", "") if content else ""
                if "approved" in text.lower() or rpc_result.get("approved", False):
                    print(f"   ✅ Civic: Action APPROVED")
                    print(f"   📋 Civic response: {text[:200]}" if text else "")
                    print("APPROVED")
                else:
                    print(f"   ❌ Civic: Action DENIED")
                    print(f"   📋 Civic response: {text[:200]}" if text else "")
                    print("DENIED")
            elif resp.status_code == 202:
                print("   ⏳ Civic: Action PENDING human review")
                print("   📋 Action logged to Civic audit trail")
                print("DENIED")
            else:
                print(f"   ⚠️  Civic returned status {resp.status_code}")
                print(f"   📋 Civic audit logged: {args.action}")
                print("   Falling back to manual approval...")
                manual_gate(args.action)
        except Exception as e:
            print(f"   ⚠️  Civic error: {e}")
            print("   Falling back to manual approval...")
            manual_gate(args.action)
    else:
        if not civic_url:
            print("   ⚠️  CIVIC_URL not set — using manual approval")
        manual_gate(args.action)


def manual_gate(action):
    """Simple manual approval fallback when Civic is not configured."""
    print(f"\n🔒 MANUAL APPROVAL REQUIRED")
    print(f"   Proposed action: {action}")
    print(f"   The agent wants to take this action based on competitive intelligence.")
    print(f"   Type 'yes' to approve or 'no' to deny:")

    try:
        response = input("   > ").strip().lower()
        if response in ("yes", "y", "approve"):
            print("   ✅ Action APPROVED (manual)")
            print("APPROVED")
        else:
            print("   ❌ Action DENIED (manual)")
            print("DENIED")
    except (EOFError, KeyboardInterrupt):
        # Non-interactive — deny by default for safety
        print("   ❌ Action DENIED (non-interactive, defaulting to safe)")
        print("DENIED")


if __name__ == "__main__":
    main()
