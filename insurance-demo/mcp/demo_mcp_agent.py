#!/usr/bin/env python3
"""
Local claim-review agent using real MCP servers (OpenAI Agents SDK).

Usage:
  cd insurance-demo/mcp
  pip install -r requirements.txt openai-agents python-dotenv
  export OPENAI_API_KEY=...
  export NTFY_TOPIC=leon-hospital-claims
  python demo_mcp_agent.py --claim-id CLM-50001

Agent Studio on CAI does not attach MCP natively — this script is for local/Cursor demos.
The claim-review-ui Flask app calls the same MCP server via mcp_client.py.
"""

from __future__ import annotations

import argparse
import asyncio
import os
from contextlib import AsyncExitStack

from agents import Agent, Runner
from agents.mcp import MCPServerStdio
from dotenv import load_dotenv

from mcp_params import insurance_demo_mcp_servers

load_dotenv(override=True)

INSTRUCTIONS = """
You are Leon Hospital MediShield Claim Review Copilot.

For each claim:
1. State whether the claim should be approved, partial approval, rejected, or manual review.
2. Use only governed facts you are given in the user message.
3. If recommendation is MANUAL REVIEW, you MUST call notify_manual_review_ticket
   with claim_id and a one-line reason (no PII).
4. Do NOT call notify_manual_review_ticket for approved, rejected, or partial claims.
"""


async def run_claim_review(claim_id: str, facts: str) -> None:
    prompt = (
        f"Review hospital insurance claim {claim_id}.\n\n"
        f"Governed claim facts (from Trino):\n{facts}\n\n"
        "Recommend approve, partial approval, reject, or manual review. "
        "If manual review, open a ticket via MCP notify tool."
    )

    async with AsyncExitStack() as stack:
        mcp_servers = [
            await stack.enter_async_context(
                MCPServerStdio(params, client_session_timeout_seconds=60)
            )
            for params in insurance_demo_mcp_servers
        ]
        agent = Agent(
            name="Leon Hospital Claim Copilot",
            instructions=INSTRUCTIONS,
            mcp_servers=mcp_servers,
        )
        result = await Runner.run(agent, prompt, max_turns=10)
        print(result.final_output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--claim-id", default="CLM-50001")
    parser.add_argument(
        "--facts",
        default=(
            "suggested_outcome=manual_review; experimental_treatment_excluded; "
            "requires_clinical_review; total_billed_amount=668.78; plan_type=standard"
        ),
    )
    args = parser.parse_args()
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("Set OPENAI_API_KEY for the local MCP agent demo.")
    asyncio.run(run_claim_review(args.claim_id, args.facts))


if __name__ == "__main__":
    main()
