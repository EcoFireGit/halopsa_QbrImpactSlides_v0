"""
BEA API Client — GDP by Industry
Thin HTTP wrapper around the Bureau of Economic Analysis REST API.
Auth uses a UserID query parameter (no OAuth2).

Usage:
    from bea_client import BEAClient
    client = BEAClient(api_key="your-key")
    rows = client.get_gdp_by_industry("51", num_quarters=8)
"""

import requests
from datetime import date


class BEAClient:
    BASE_URL = "https://apps.bea.gov/api/data"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_gdp_by_industry(
        self,
        industry_code: str,
        num_quarters: int = 8,
    ) -> list[dict]:
        """
        Fetch quarterly GDP-by-Industry data for the given BEA industry code.

        Args:
            industry_code: BEA industry code, e.g. "51", "62", "31-33"
            num_quarters:  How many most-recent quarters to return (default 8)

        Returns:
            List of row dicts sorted chronologically, trimmed to num_quarters.

        Raises:
            ValueError: If the BEA API returns an error body or no data rows.
            requests.HTTPError: On non-2xx HTTP responses.
        """
        # Request the last 3 calendar years to ensure we get enough quarters
        current_year = date.today().year
        years = ",".join(str(y) for y in range(current_year - 3, current_year + 1))

        params = {
            "UserID": self.api_key,
            "method": "GetData",
            "datasetname": "GDPbyIndustry",
            "TableID": "1",
            "Frequency": "Q",
            "Industry": industry_code,
            "Year": years,
            "ResultFormat": "json",
        }

        response = requests.get(self.BASE_URL, params=params, timeout=15)
        response.raise_for_status()

        payload = response.json()

        results = payload.get("BEAAPI", {}).get("Results")

        # BEA-level errors: Results is a dict containing an "Error" key
        if isinstance(results, dict) and results.get("Error"):
            raise ValueError(f"BEA API error: {results['Error']}")

        # Success path: Results is a non-empty list; first element holds "Data"
        if not isinstance(results, list) or not results:
            raise ValueError(
                f"Unexpected BEA response structure: Results={type(results)}"
            )

        data_rows = results[0].get("Data", [])

        if not data_rows:
            raise ValueError(
                f"No data rows returned for industry code '{industry_code}'."
            )

        # Sort chronologically; BEA returns Year + Quarter (Roman: "I"–"IV") separately.
        # Roman numerals sort correctly lexicographically: I < II < III < IV.
        sorted_rows = sorted(
            data_rows, key=lambda r: (r.get("Year", ""), r.get("Quarter", ""))
        )

        # Trim to the most recent num_quarters
        return sorted_rows[-num_quarters:]


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("BEA_API_KEY", "")
    if not api_key:
        print("Set BEA_API_KEY in your .env file to test.")
    else:
        client = BEAClient(api_key=api_key)
        rows = client.get_gdp_by_industry("51", num_quarters=8)
        print(f"Fetched {len(rows)} rows for industry '51':")
        for row in rows:
            period = f"{row.get('Year')} {row.get('Quarter')}"
            print(f"  {period}  DataValue={row.get('DataValue')}")
