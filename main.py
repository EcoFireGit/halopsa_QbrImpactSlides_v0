# main.py
from halo_client import HaloClient


def main():
    print("--- Starting HaloPSA Authentication Test ---")

    # Initialize the client
    client = HaloClient()

    try:
        # Attempt to get the token
        token = client.authenticate()

        # Verify success
        if token:
            print("✅ Success! Access Token retrieved.")
            print(
                f"Token snippet: {token[:15]}..."
            )  # Only print the first few chars for security

            # READY FOR WEEK 2:
            # logic to fetch tickets will go here using client.get_headers()
        else:
            print("❌ Failed to retrieve token.")

    except Exception as e:
        print(f"❌ Critical Error: {e}")


if __name__ == "__main__":
    main()
