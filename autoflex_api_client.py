"""
Autoflex10 API Client Module.

This module provides a client class for interacting with the Autoflex10 API,
handling authentication and API requests.
"""

import os
import time
from typing import Optional, Dict, Any, List
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class AutoflexAPIClient:
    """
    Client for interacting with the Autoflex10 API.

    Handles authentication token management and provides methods
    for making authenticated API requests.
    """

    # Authentication base URL (different from API URL)
    AUTH_BASE_URL = "https://api.autoflex10.work/v2"

    def __init__(
        self,
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        organization_name: Optional[str] = None
    ):
        """
        Initialize the Autoflex10 API client.

        Args:
            api_key: API key for authentication (defaults to env var)
            username: Username for authentication (defaults to env var)
            password: Password for authentication (defaults to env var)
            organization_name: Organization name (defaults to env var or empty)
        """
        self.api_key = api_key or os.getenv('AUTOFLEX_API_KEY', '')
        self.username = username or os.getenv('AUTOFLEX_USERNAME', '')
        self.password = password or os.getenv('AUTOFLEX_PASSWORD', '')
        self.organization_name = (
            organization_name or
            os.getenv('AUTOFLEX_ORGANIZATION_NAME', '')
        )

        self.token: Optional[str] = None
        self.token_expiry: Optional[float] = None
        self.token_validity_duration = 1800  # 30 minutes in seconds
        self.api_url: Optional[str] = None  # Dynamic API URL from authentication
        self.user_id: Optional[str] = None

    def authenticate(self) -> bool:
        """
        Authenticate with the Autoflex10 API and obtain a token.

        Uses GET request with query parameters as per API specification.
        Returns dynamic API URL for subsequent requests.

        Returns:
            True if authentication successful, False otherwise
        """
        auth_url = f"{self.AUTH_BASE_URL}/authenticate"
        params = {
            'api_key': self.api_key,
            'username': self.username,
            'password': self.password
        }

        if self.organization_name:
            params['organization_name'] = self.organization_name

        try:
            response = requests.get(auth_url, params=params, timeout=15)

            if response.status_code == 200:
                data = response.json()

                # Check for token in response
                if 'token' in data:
                    self.token = data['token']
                    self.token_expiry = time.time() + self.token_validity_duration

                    # Get dynamic API URL
                    if 'api_url' in data:
                        self.api_url = data['api_url']

                    # Get user ID
                    if 'user_id' in data:
                        self.user_id = data['user_id']

                    print(f"Authentication successful!")
                    print(f"  Token: {self.token[:20]}...")
                    print(f"  API URL: {self.api_url}")
                    return True

                print(f"Unexpected response structure: {data}")
                return False

            elif response.status_code == 401:
                print("Authentication failed: Invalid credentials")
                return False

            elif response.status_code == 202:
                # Retry required
                data = response.json()
                retry_ms = data.get('retry', 5000)
                print(f"Rate limited. Retry in {retry_ms}ms")
                return False

            else:
                print(f"Authentication failed with status {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error: {error_data}")
                except ValueError:
                    print(f"Response: {response.text}")
                return False

        except requests.exceptions.RequestException as error:
            print(f"Authentication request failed: {error}")
            return False

    def _ensure_authenticated(self) -> bool:
        """
        Ensure we have a valid authentication token.

        Returns:
            True if authenticated, False otherwise
        """
        current_time = time.time()

        if (self.token is None or
                self.token_expiry is None or
                current_time >= self.token_expiry):
            return self.authenticate()

        return True

    def _get_headers(self) -> Dict[str, str]:
        """
        Get headers for API requests including authentication token.

        Returns:
            Dictionary of HTTP headers
        """
        if not self._ensure_authenticated():
            raise ValueError("Authentication failed. Cannot make API request.")

        return {
            'token': self.token,
            'Content-Type': 'application/json'
        }

    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Make a GET request to the API.

        Args:
            endpoint: API endpoint path (relative to api_url)
            params: Optional query parameters

        Returns:
            JSON response data or None if request failed
        """
        if not self.api_url:
            if not self._ensure_authenticated():
                return None

        url = f"{self.api_url}{endpoint}"
        headers = self._get_headers()

        try:
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=15
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as error:
            print(f"GET request failed for {endpoint}: {error}")
            if hasattr(error, 'response') and error.response is not None:
                try:
                    error_data = error.response.json()
                    print(f"Error details: {error_data}")
                except ValueError:
                    print(f"Error response: {error.response.text[:200]}")
            return None

    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Make a POST request to the API.

        Args:
            endpoint: API endpoint path (relative to api_url)
            data: Optional request body data

        Returns:
            JSON response data or None if request failed
        """
        if not self.api_url:
            if not self._ensure_authenticated():
                return None

        url = f"{self.api_url}{endpoint}"
        headers = self._get_headers()

        try:
            response = requests.post(
                url,
                headers=headers,
                json=data,
                timeout=15
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as error:
            print(f"POST request failed for {endpoint}: {error}")
            if hasattr(error, 'response') and error.response is not None:
                try:
                    error_data = error.response.json()
                    print(f"Error details: {error_data}")
                except ValueError:
                    print(f"Error response: {error.response.text[:200]}")
            return None

    def get_vehicles(
        self,
        fields: Optional[List[str]] = None,
        page: int = 1
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve list of vehicles from Autoflex10.

        Args:
            fields: List of fields to include in response
            page: Page number for pagination

        Returns:
            Dictionary with vehicle data or None if request failed
        """
        default_fields = [
            'vehicle_id',
            'license_plate',
            'purchase_price',
            'brand',
            'model',
            'color',
            'purchase_date',
            'sell_price',
            'is_sold'  # 1 = sold, 0 = not sold (read-only, set by Autoflex)
        ]

        params = {
            'fields': ','.join(fields or default_fields),
            'page': page
        }

        return self.get('/vehicle', params=params)

    def get_all_vehicles(
        self,
        fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all vehicles from Autoflex10 (handles pagination).

        Args:
            fields: List of fields to include in response

        Returns:
            List of vehicle dictionaries
        """
        all_vehicles = []
        page = 1
        has_next_page = True

        while has_next_page:
            result = self.get_vehicles(fields=fields, page=page)

            if result is None:
                break

            vehicles = result.get('data', [])
            all_vehicles.extend(vehicles)

            has_next_page = result.get('nextpage', False)
            page += 1

            # Safety limit
            if page > 100:
                print("Warning: Reached page limit of 100")
                break

        return all_vehicles

    def get_vehicle(self, vehicle_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific vehicle by ID.

        Args:
            vehicle_id: The vehicle identifier

        Returns:
            Vehicle data dictionary or None if request failed
        """
        return self.get(f'/vehicle/{vehicle_id}')
