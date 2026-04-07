import os

import requests


class PropertyGuardianClient:
    def __init__(self, base_url=None):
        self.base_url = base_url or os.getenv("API_URL", "http://localhost:8000")
        self.api_v1 = f"{self.base_url}/api/v1"
        self.headers = {}
        self._token = None

    def login(self, email: str, password: str) -> dict:
        """Authenticate and store JWT token for subsequent requests."""
        try:
            resp = requests.post(
                f"{self.api_v1}/token",
                data={"username": email, "password": password},
                timeout=10,
            )
            if resp.status_code == 200:
                self._token = resp.json()["access_token"]
                self.headers = {"Authorization": f"Bearer {self._token}"}
                return {
                    "status": "success",
                    "message": "Logged in successfully.",
                    "token": self._token,
                }
            else:
                return {
                    "status": "error",
                    "message": resp.json().get("detail", "Login failed."),
                }
        except requests.RequestException as e:
            return {"status": "error", "message": str(e)}

    def set_token(self, token: str):
        """Manually set token (e.g. from cookies)."""
        self._token = token
        self.headers = {"Authorization": f"Bearer {token}"}

    def register(self, email: str, password: str) -> dict:
        """Register a new user account."""
        try:
            resp = requests.post(
                f"{self.api_v1}/users/",
                json={"email": email, "password": password},
                timeout=10,
            )
            if resp.status_code == 200:
                return {
                    "status": "success",
                    "message": "Account created. You can now log in.",
                }
            else:
                return {
                    "status": "error",
                    "message": resp.json().get("detail", "Registration failed."),
                }
        except requests.RequestException as e:
            return {"status": "error", "message": str(e)}

    def confirm_password_reset(self, email: str, new_password: str) -> dict:
        """Set new password without OTP."""
        try:
            resp = requests.post(
                f"{self.api_v1}/password-reset/confirm",
                json={"email": email, "new_password": new_password},
                timeout=10,
            )
            if resp.status_code == 200:
                return {
                    "status": "success",
                    "message": resp.json().get("message", "Password reset"),
                }
            return {
                "status": "error",
                "message": resp.json().get("detail", "Failed to reset password"),
            }
        except requests.RequestException as e:
            return {"status": "error", "message": str(e)}

    @property
    def is_authenticated(self) -> bool:
        return self._token is not None

    def health_check(self):
        """Check if backend is reachable."""
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=2)
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def ingest_files(self, files):
        """Upload multiple files to the ingestion endpoint."""
        if not self.is_authenticated:
            return {
                "status": "error",
                "message": "Not authenticated. Please log in first.",
            }

        upload_data = []
        for file in files:
            file.seek(0)
            upload_data.append(("files", (file.name, file, file.type)))

        try:
            resp = requests.post(
                f"{self.api_v1}/ingest",
                files=upload_data,
                headers=self.headers,
                timeout=120,
            )

            if resp.status_code == 401:
                self._token = None
                self.headers = {}
                return {
                    "status": "error",
                    "message": "Session expired. Please log in again.",
                }

            return resp.json()
        except requests.RequestException as e:
            return {"status": "error", "message": str(e)}

    def check_fraud(self):
        """Trigger fraud detection analysis."""
        if not self.is_authenticated:
            return []
        try:
            resp = requests.get(
                f"{self.api_v1}/fraud-check", headers=self.headers, timeout=30
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"Fraud Check Error: {e}")
            return []

    def get_properties(self):
        """Fetch all properties from the database."""
        try:
            resp = requests.get(
                f"{self.api_v1}/properties", headers=self.headers, timeout=10
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException:
            return []

    def get_transactions(self):
        """Fetch all transactions from the database."""
        try:
            resp = requests.get(
                f"{self.api_v1}/transactions", headers=self.headers, timeout=10
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException:
            return []

    def chat(self, query, session_id=None):
        """Send a natural language query via GET to FastAPI."""
        try:
            params = {"q": query}
            if session_id:
                params["session_id"] = session_id
            resp = requests.get(
                f"{self.api_v1}/query/natural_language",
                params=params,
                headers=self.headers,
                timeout=120,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            return {"answer": f"Backend Error: {e}", "sources": [], "error": str(e)}

    def execute_sql(self, query: str):
        """Execute a raw SQL SELECT query via POST."""
        if not self.is_authenticated:
            return {"status": "error", "message": "Not authenticated."}
        try:
            resp = requests.post(
                f"{self.api_v1}/query/direct_sql",
                json={"query": query},
                headers=self.headers,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            detail = str(e)
            if hasattr(e, "response") and e.response is not None:
                try:
                    detail = e.response.json().get("detail", str(e))
                except:
                    pass
            return {"status": "error", "message": detail}

    def sync_neo4j(self):
        """Trigger syncing of Postgres data into Neo4j graph database."""
        if not self.is_authenticated:
            return {"status": "error", "message": "Not authenticated."}
        try:
            resp = requests.post(
                f"{self.api_v1}/graph/sync",
                headers=self.headers,
                timeout=120,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            return {"status": "error", "message": str(e)}

    def get_graph_chain(self, property_id: int):
        """Fetch chain of title for a property from Neo4j."""
        if not self.is_authenticated:
            return {"chain": [], "count": 0}
        try:
            resp = requests.get(
                f"{self.api_v1}/graph/chain/{property_id}",
                headers=self.headers,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            return {"chain": [], "count": 0, "error": str(e)}

    def get_graph_network(self):
        """Fetch the full property transaction network from Neo4j."""
        if not self.is_authenticated:
            return {"nodes": [], "edges": []}
        try:
            resp = requests.get(
                f"{self.api_v1}/graph/network",
                headers=self.headers,
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            return {"nodes": [], "edges": [], "error": str(e)}
