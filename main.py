# main.py
from halo_client import HaloClient
from datetime import datetime, timedelta
import json


def main():
    print("--- Starting HaloPSA Ticket Fetch ---")

    # Initialize the client
    client = HaloClient()

    # Calculate date 30 days ago for our filter
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    print(f"Fetching tickets since: {thirty_days_ago}...")

    try:
        # Call the new method
        tickets_data = client.get_tickets(start_date=thirty_days_ago, page_size=5)

        # HaloPSA API usually returns a dict with a 'tickets' list key,
        # or sometimes a direct list depending on configuration.
        # We handle both cases safely:
        tickets = (
            tickets_data.get("tickets", [])
            if isinstance(tickets_data, dict)
            else tickets_data
        )

        if tickets:
            print(f"✅ Success! Retrieved {len(tickets)} tickets.")

            # Print the first ticket to inspect the structure (Crucial for Week 2 Task 3)
            first_ticket = tickets[0]
            print("\n--- Sample Ticket Structure ---")
            print(json.dumps(first_ticket, indent=2))

            # Check for our key metrics fields
            print("\n--- Data Check ---")
            print(f"ID: {first_ticket.get('id')}")
            print(f"Summary: {first_ticket.get('summary')}")
            print(f"Date Occurred: {first_ticket.get('dateoccurred')}")
            print(
                f"Type: {first_ticket.get('tickettype_id')} (You will need to map this ID to a name later)"
            )
        else:
            print("⚠️ Request succeeded, but 0 tickets were returned.")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
