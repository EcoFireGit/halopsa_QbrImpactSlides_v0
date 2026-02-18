# main.py
from halo_client import HaloClient
from datetime import datetime, timedelta


def main():
    client = HaloClient()

    # --- CONFIGURATION ---
    # REPLACE THIS with a real Client ID from your Halo trial
    TARGET_CLIENT_ID = 2

    # Calculate dates: Last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    # Format dates as YYYY-MM-DD for the API
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    print(f"Target Client ID: {TARGET_CLIENT_ID}")
    print(f"Date Range: {start_str} to {end_str}")

    try:
        # Fetch filtered tickets
        # We request 100 to ensure we get enough data to test
        data = client.get_tickets(
            client_id=TARGET_CLIENT_ID,
            start_date=start_str,
            end_date=end_str,
            page_size=100,
        )

        # Handle the response structure safely
        tickets = data.get("tickets", []) if isinstance(data, dict) else data

        if not tickets:
            print(
                "⚠️ No tickets found. Check if the Client ID exists and has recent tickets."
            )
            return

        print(f"✅ Retrieved {len(tickets)} tickets.")

        # --- VERIFICATION STEP ---
        # We loop through the results to ensure the API actually filtered them.
        # This is crucial because some API versions ignore params if malformed.

        errors = 0
        for t in tickets:
            # Check Client ID (Note: API might return client_id as int or string)
            tid = t.get("client_id")
            if str(tid) != str(TARGET_CLIENT_ID):
                print(
                    f"❌ Error: Ticket {t.get('id')} belongs to Client {tid}, not {TARGET_CLIENT_ID}"
                )
                errors += 1

            # Check Date
            # Halo date format is usually "2023-10-27T10:00:00"
            t_date_str = t.get("dateoccurred", "").split("T")[0]
            if t_date_str < start_str:
                print(
                    f"❌ Error: Ticket {t.get('id')} is from {t_date_str}, which is too old."
                )
                errors += 1

        if errors == 0:
            print("🎉 PASSED: All tickets match the Client ID and Date Range.")
        else:
            print(
                f"⚠️ FOUND {errors} FILTRATION ERRORS. The API params might not be working as expected."
            )

    except Exception as e:
        print(f"❌ Critical Error: {e}")


if __name__ == "__main__":
    main()
