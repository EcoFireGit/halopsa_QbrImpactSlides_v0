"""
populate_slack_data.py
Generates synthetic Slack message data tied to HaloPSA client accounts.

Usage:
    python populate_slack_data.py

The script loads existing HaloPSA client IDs from client_profiles.json if
available, or falls back to a built-in set of representative sample clients.
It then creates realistic MSP-themed Slack messages across multiple channels
and writes them to slack_data.json via the slack_schema persistence layer.

Run again with --reset to clear existing data before generating fresh records.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import uuid
from datetime import datetime, timedelta, timezone

from slack_schema import SlackMessage, delete_messages_for_client, load_slack_data, save_slack_data

# ---------------------------------------------------------------------------
# Seed for reproducibility (can be overridden via CLI)
# ---------------------------------------------------------------------------
DEFAULT_SEED = 42

# ---------------------------------------------------------------------------
# Realistic channels used in MSP/client shared Slack workspaces
# ---------------------------------------------------------------------------
CHANNELS = [
    "general",
    "support-alerts",
    "incidents",
    "maintenance-windows",
    "announcements",
    "security-updates",
]

# ---------------------------------------------------------------------------
# MSP agent personas
# ---------------------------------------------------------------------------
MSP_AGENTS = [
    {"sender_id": "U0MSP001", "sender_name": "Alex Rivera"},
    {"sender_id": "U0MSP002", "sender_name": "Jordan Lee"},
    {"sender_id": "U0MSP003", "sender_name": "Morgan Chen"},
    {"sender_id": "U0MSP004", "sender_name": "Taylor Brooks"},
]

# ---------------------------------------------------------------------------
# Per-client user templates (generated at runtime based on client name)
# ---------------------------------------------------------------------------

def _make_client_users(client_id: int, client_name: str) -> list[dict]:
    slug = client_name.split()[0].upper()[:4]
    return [
        {"sender_id": f"U{slug}{client_id}01", "sender_name": f"{client_name} - IT Lead"},
        {"sender_id": f"U{slug}{client_id}02", "sender_name": f"{client_name} - Office Manager"},
        {"sender_id": f"U{slug}{client_id}03", "sender_name": f"{client_name} - Operations"},
    ]


# ---------------------------------------------------------------------------
# Message templates by channel and sentiment
# ---------------------------------------------------------------------------

_TEMPLATES: dict[str, list[dict]] = {
    "general": [
        {
            "text": "Good morning team! Just a reminder that our quarterly review is scheduled for next week.",
            "sentiment": "positive",
            "tags": ["qbr", "reminder"],
            "sender_type": "msp_agent",
        },
        {
            "text": "Hi everyone, we're updating our ticketing workflow. Please submit all requests through the portal.",
            "sentiment": "neutral",
            "tags": ["process", "tickets"],
            "sender_type": "msp_agent",
        },
        {
            "text": "Thanks for the quick turnaround on our VPN issue last week!",
            "sentiment": "positive",
            "tags": ["feedback", "vpn"],
            "sender_type": "client_user",
        },
        {
            "text": "Can someone confirm the status of our server migration scheduled for this weekend?",
            "sentiment": "neutral",
            "tags": ["migration", "question"],
            "sender_type": "client_user",
        },
    ],
    "support-alerts": [
        {
            "text": "Ticket #{{TICKET}} opened: Users reporting slow network performance in the main office.",
            "sentiment": "negative",
            "tags": ["network", "performance", "slow"],
            "sender_type": "client_user",
        },
        {
            "text": "Ticket #{{TICKET}} resolved: VPN connectivity issue affecting remote workers has been fixed.",
            "sentiment": "positive",
            "tags": ["vpn", "resolved", "remote-work"],
            "sender_type": "msp_agent",
        },
        {
            "text": "Ticket #{{TICKET}} opened: Printer on floor 2 is offline, affecting 15 users.",
            "sentiment": "negative",
            "tags": ["printer", "hardware"],
            "sender_type": "client_user",
        },
        {
            "text": "Ticket #{{TICKET}} updated: Email server restored. All services now operational.",
            "sentiment": "positive",
            "tags": ["email", "resolved"],
            "sender_type": "msp_agent",
        },
        {
            "text": "Ticket #{{TICKET}} escalated: Critical — file server unreachable from all workstations.",
            "sentiment": "negative",
            "tags": ["critical", "file-server", "escalated"],
            "sender_type": "msp_agent",
        },
        {
            "text": "Ticket #{{TICKET}} opened: Microsoft 365 license allocation needed for 3 new hires starting Monday.",
            "sentiment": "neutral",
            "tags": ["m365", "onboarding", "licenses"],
            "sender_type": "client_user",
        },
    ],
    "incidents": [
        {
            "text": "INCIDENT: Internet connectivity down across all sites. ISP notified. ETA: 2 hours.",
            "sentiment": "negative",
            "tags": ["incident", "internet", "outage", "critical"],
            "sender_type": "msp_agent",
        },
        {
            "text": "UPDATE: ISP reports fiber cut on main line. Failover to backup link now active. Degraded but operational.",
            "sentiment": "neutral",
            "tags": ["incident", "internet", "update", "failover"],
            "sender_type": "msp_agent",
        },
        {
            "text": "RESOLVED: Primary internet restored. All services back to normal. RCA report to follow.",
            "sentiment": "positive",
            "tags": ["incident", "resolved", "rca"],
            "sender_type": "msp_agent",
        },
        {
            "text": "INCIDENT: Ransomware detected on workstation WS-ACCT-03. Machine isolated. Investigation underway.",
            "sentiment": "negative",
            "tags": ["incident", "security", "ransomware", "critical"],
            "sender_type": "msp_agent",
        },
        {
            "text": "How long has this been going on? Our accounting team can't access any shared drives.",
            "sentiment": "negative",
            "tags": ["outage", "shared-drives", "accounting"],
            "sender_type": "client_user",
        },
    ],
    "maintenance-windows": [
        {
            "text": "Maintenance window scheduled: Saturday 11pm–3am CT. Server OS patches will be applied.",
            "sentiment": "neutral",
            "tags": ["maintenance", "patching", "windows"],
            "sender_type": "msp_agent",
        },
        {
            "text": "Reminder: Firewall firmware upgrade tonight at 10pm. Expect 15–20 min of downtime.",
            "sentiment": "neutral",
            "tags": ["maintenance", "firewall", "upgrade"],
            "sender_type": "msp_agent",
        },
        {
            "text": "Confirmed — we can approve the maintenance window for this Saturday. Proceed as planned.",
            "sentiment": "positive",
            "tags": ["maintenance", "approved"],
            "sender_type": "client_user",
        },
        {
            "text": "Can we reschedule the Saturday window to Sunday? We have a company event Saturday evening.",
            "sentiment": "neutral",
            "tags": ["maintenance", "reschedule"],
            "sender_type": "client_user",
        },
        {
            "text": "Maintenance complete. All patches applied successfully. No issues encountered.",
            "sentiment": "positive",
            "tags": ["maintenance", "complete", "patching"],
            "sender_type": "msp_agent",
        },
    ],
    "announcements": [
        {
            "text": "New security policy update: MFA is now required for all VPN connections effective next Monday.",
            "sentiment": "neutral",
            "tags": ["security", "mfa", "policy", "vpn"],
            "sender_type": "msp_agent",
        },
        {
            "text": "Phishing alert: We've seen targeted phishing emails impersonating Microsoft support. Do not click links.",
            "sentiment": "negative",
            "tags": ["security", "phishing", "alert"],
            "sender_type": "msp_agent",
        },
        {
            "text": "Reminder: End-of-life for Windows Server 2012 in 90 days. Please review upgrade roadmap shared last week.",
            "sentiment": "neutral",
            "tags": ["eol", "windows-server", "upgrade"],
            "sender_type": "msp_agent",
        },
        {
            "text": "Great news — your backup health score improved to 98% this month. Keep up the good work!",
            "sentiment": "positive",
            "tags": ["backup", "health", "proactive"],
            "sender_type": "msp_agent",
        },
    ],
    "security-updates": [
        {
            "text": "Critical CVE patched across all endpoints: CVE-2025-1234. Reboot required for 4 workstations.",
            "sentiment": "neutral",
            "tags": ["cve", "patching", "endpoints", "security"],
            "sender_type": "msp_agent",
        },
        {
            "text": "AV definitions updated on all machines. No threats detected in latest scan.",
            "sentiment": "positive",
            "tags": ["antivirus", "scan", "clean"],
            "sender_type": "msp_agent",
        },
        {
            "text": "User account locked after repeated failed login attempts from unknown IP. Account reset completed.",
            "sentiment": "negative",
            "tags": ["account-lockout", "security", "brute-force"],
            "sender_type": "msp_agent",
        },
        {
            "text": "Quarterly penetration test scheduled for next month. We'll share the scope document shortly.",
            "sentiment": "neutral",
            "tags": ["pentest", "security", "quarterly"],
            "sender_type": "msp_agent",
        },
    ],
}


def _random_timestamp(rng: random.Random, days_back: int = 90) -> str:
    """Return a random ISO 8601 UTC timestamp within the last `days_back` days."""
    now = datetime.now(timezone.utc)
    delta = timedelta(seconds=rng.randint(0, days_back * 86400))
    return (now - delta).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pick_ticket_id(rng: random.Random) -> int:
    return rng.randint(10000, 99999)


def generate_messages_for_client(
    client_id: int,
    client_name: str,
    rng: random.Random,
    messages_per_client: int = 12,
) -> list[SlackMessage]:
    """Generate `messages_per_client` synthetic Slack messages for one HaloPSA client."""
    client_users = _make_client_users(client_id, client_name)
    messages: list[SlackMessage] = []

    channel_pool = CHANNELS.copy()
    rng.shuffle(channel_pool)

    for i in range(messages_per_client):
        channel = channel_pool[i % len(channel_pool)]
        templates = _TEMPLATES[channel]
        template = rng.choice(templates)

        sender_type = template["sender_type"]
        if sender_type == "msp_agent":
            agent = rng.choice(MSP_AGENTS)
            sender_id = agent["sender_id"]
            sender_name = agent["sender_name"]
        else:
            user = rng.choice(client_users)
            sender_id = user["sender_id"]
            sender_name = user["sender_name"]

        text = template["text"]
        ticket_ref: int | None = None
        if "{{TICKET}}" in text:
            ticket_ref = _pick_ticket_id(rng)
            text = text.replace("{{TICKET}}", str(ticket_ref))

        ts = _random_timestamp(rng)
        is_reply = rng.random() < 0.25
        thread_ts = _random_timestamp(rng, days_back=1) if is_reply else None

        messages.append(
            SlackMessage(
                message_id=str(uuid.uuid4()),
                client_id=client_id,
                client_name=client_name,
                channel=channel,
                sender_id=sender_id,
                sender_name=sender_name,
                sender_type=sender_type,
                message_text=text,
                timestamp=ts,
                thread_ts=thread_ts,
                is_reply=is_reply,
                sentiment=template["sentiment"],
                ticket_reference=ticket_ref,
                tags=list(template["tags"]),
            )
        )

    # Sort by timestamp ascending
    messages.sort(key=lambda m: m.timestamp)
    return messages


# ---------------------------------------------------------------------------
# Client source helpers
# ---------------------------------------------------------------------------

_CLIENT_PROFILES_PATH = os.path.join(os.path.dirname(__file__), "client_profiles.json")

_FALLBACK_CLIENTS = [
    {"id": 1, "name": "Acme Corporation"},
    {"id": 2, "name": "Globex Industries"},
    {"id": 3, "name": "Initech Solutions"},
    {"id": 4, "name": "Umbrella Technologies"},
    {"id": 5, "name": "Hooli Enterprises"},
    {"id": 6, "name": "Pied Piper LLC"},
    {"id": 7, "name": "Dunder Mifflin Paper"},
    {"id": 8, "name": "Vandelay Industries"},
]


def _load_clients_from_profiles() -> list[dict]:
    """
    Read client IDs from client_profiles.json (keys are client IDs).
    Returns list of {id, name} dicts. Falls back to empty list on any error.
    """
    if not os.path.exists(_CLIENT_PROFILES_PATH):
        return []
    try:
        with open(_CLIENT_PROFILES_PATH, "r") as f:
            profiles = json.load(f)
        return [
            {"id": int(k), "name": f"Client {k}"}
            for k in profiles.keys()
            if k.isdigit()
        ]
    except (json.JSONDecodeError, OSError, ValueError):
        return []


def get_clients(use_fallback_if_empty: bool = True) -> list[dict]:
    """
    Return list of {id, name} dicts representing HaloPSA accounts.
    Loads from client_profiles.json when available; falls back to built-in
    sample list if the file is empty or absent.
    """
    clients = _load_clients_from_profiles()
    if not clients and use_fallback_if_empty:
        clients = _FALLBACK_CLIENTS
    return clients


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def populate(
    reset: bool = False,
    messages_per_client: int = 12,
    seed: int = DEFAULT_SEED,
) -> list[SlackMessage]:
    """
    Generate and persist synthetic Slack messages for all known HaloPSA clients.

    Args:
        reset: If True, clear all existing Slack data before generating.
        messages_per_client: Number of messages to generate per client.
        seed: RNG seed for reproducibility.

    Returns:
        List of all generated SlackMessage objects.
    """
    rng = random.Random(seed)
    clients = get_clients()

    if reset:
        save_slack_data([])
        print("Existing Slack data cleared.")

    all_generated: list[SlackMessage] = []

    for client in clients:
        client_id = client["id"]
        client_name = client["name"]

        if not reset:
            # Remove existing records for this client to avoid duplicates
            deleted = delete_messages_for_client(client_id)
            if deleted:
                print(f"  Removed {deleted} existing messages for client {client_id} ({client_name})")

        msgs = generate_messages_for_client(client_id, client_name, rng, messages_per_client)

        # Load current data, append, and save
        existing = load_slack_data()
        save_slack_data(existing + msgs)

        all_generated.extend(msgs)
        print(f"  Generated {len(msgs)} messages for client {client_id} ({client_name})")

    total = len(all_generated)
    print(f"\nDone. {total} Slack messages written to slack_data.json.")
    return all_generated


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Populate slack_data.json with synthetic Slack messages.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear all existing Slack data before generating new records.",
    )
    parser.add_argument(
        "--messages-per-client",
        type=int,
        default=12,
        metavar="N",
        help="Number of messages to generate per HaloPSA client (default: 12).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Random seed for reproducibility (default: {DEFAULT_SEED}).",
    )
    args = parser.parse_args()

    populate(
        reset=args.reset,
        messages_per_client=args.messages_per_client,
        seed=args.seed,
    )
