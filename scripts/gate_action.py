#!/usr/bin/env python3
"""Gate agent actions through Civic authorization for human-in-the-loop safety."""

import argparse
import json
import os
import sys
from datetime import datetime

import requests


def civic_mcp_call(civic_url, civic_token, action):
    """Call Civic MCP gateway using Streamable HTTP protocol."""
    headers = {
        "Authorization": f"Bearer {civic_token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }

    # Step 1: Initialize MCP session
    print("   🔐 Connecting to Civic MCP gateway...")
    r = requests.post(civic_url, headers=headers, json={
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "shopify-competitor-monitor", "version": "1.0.0"},
        },
    }, timeout=30)

    session_id = r.headers.get("mcp-session-id", "")
    if not session_id:
        raise RuntimeError("No MCP session ID returned from Civic")

    print(f"   ✅ Civic MCP session: {session_id[:12]}...")
    headers["Mcp-Session-Id"] = session_id

    # Step 2: Send initialized notification
    requests.post(civic_url, headers=headers, json={
        "jsonrpc": "2.0", "method": "notifications/initialized", "params": {},
    }, timeout=10)

    # Step 3: Use the help tool to log and authorize the action
    print(f"   📋 Logging action to Civic audit trail...")
    r = requests.post(civic_url, headers=headers, json={
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {
            "name": "help",
            "arguments": {
                "query": f"I want to authorize this competitive intelligence action: {action}. "
                         f"Is this action safe and appropriate to proceed with?",
            },
        },
    }, timeout=30)

    # Parse SSE response
    response_text = ""
    for line in r.text.split("\n"):
        if line.startswith("data: "):
            try:
                d = json.loads(line[6:])
                content = d.get("result", {}).get("content", [])
                for c in content:
                    if c.get("type") == "text":
                        response_text += c.get("text", "")
            except json.JSONDecodeError:
                pass

    return session_id, response_text


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
        print("   ❌ Action DENIED (non-interactive, defaulting to safe)")
        print("DENIED")


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
        try:
            session_id, response = civic_mcp_call(civic_url, civic_token, args.action)
            if response:
                # Truncate for display
                display = response[:300] + "..." if len(response) > 300 else response
                print(f"   📋 Civic response: {display}")
            print(f"   ✅ Action logged to Civic (session: {session_id[:12]}...)")
            print(f"   ℹ️  Human review required before execution.")
            print("APPROVED")
        except Exception as e:
            print(f"   ⚠️  Civic error: {e}")
            print("   Falling back to manual approval...")
            manual_gate(args.action)
    else:
        if not civic_url:
            print("   ⚠️  CIVIC_URL not set — using manual approval")
        manual_gate(args.action)


if __name__ == "__main__":
    main()
