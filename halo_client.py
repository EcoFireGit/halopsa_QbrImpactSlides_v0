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
            response.raise_for_status()
            self.token = response.json().get("access_token")
            return self.token
        except Exception as e:
            print(f"Authentication Failed: {e}")
            raise

    def get_headers(self):
        """
        Helper to get the Authorization header for future requests.
        """
        if not self.token:
            self.authenticate()
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _get_request(self, endpoint, params=None):
        """
        Internal helper to handle GET requests to any Halo endpoint.
        """
        url = f"{self.host}/api/{endpoint}"
        try:
            response = requests.get(url, headers=self.get_headers(), params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as err:
            print(f"Request to {endpoint} failed: {err}")
            print(f"Response: {response.text}")
            return None

    def get_tickets(self, start_date=None, end_date=None, page_size=10):
        """
        Fetches tickets from HaloPSA.
        """
        params = {
            "page_size": page_size,
            "order": "id desc",  # Get newest first
            # "include_details": True # Uncomment if you need full body text
        }

        # HaloPSA typically filters dates via specific parameters or OData.
        # For simplicity in this step, we fetch recent tickets and will filter in Python
        # if the API doesn't support strict date params in your version.
        # However, standard Halo params for date often look like this:
        if start_date:
            params["startdate"] = start_date
        if end_date:
            params["enddate"] = end_date

        return self._get_request("Tickets", params)
