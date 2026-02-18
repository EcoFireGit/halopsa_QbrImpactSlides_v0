# halo_client.py
import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class HaloClient:
    def __init__(self):
        self.host = os.getenv("HALO_HOST")
        self.client_id = os.getenv("CLIENT_ID")
        self.client_secret = os.getenv("CLIENT_SECRET")
        self.scope = os.getenv("HALO_SCOPE", "all")
        self.token = None

        # Ensure host doesn't have a trailing slash for cleaner URL building
        if self.host.endswith("/"):
            self.host = self.host[:-1]

    def authenticate(self):
        """
        Exchanges Client ID/Secret for an Access Token.
        Returns the access token as a string.
        """
        auth_url = f"{self.host}/auth/token"

        # Payload for OAuth2 Client Credentials Flow
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": self.scope,
        }

        # Headers - standard form-urlencoded for OAuth
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            response = requests.post(auth_url, data=payload, headers=headers)
            response.raise_for_status()  # Raises error for 4xx/5xx responses

            data = response.json()
            self.token = data.get("access_token")

            # Optional: Print expiration or other debug info
            # print(f"Token obtained! Expires in: {data.get('expires_in')} seconds")

            return self.token

        except requests.exceptions.HTTPError as err:
            print(f"Authentication Failed: {err}")
            print(f"Response Body: {response.text}")
            raise
        except Exception as e:
            print(f"An error occurred: {e}")
            raise

    def get_headers(self):
        """
        Helper to get the Authorization header for future requests.
        """
        if not self.token:
            self.authenticate()
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
