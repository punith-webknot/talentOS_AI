import atexit
import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP

_SOURCE_DIR = Path(__file__).resolve().parents[1]
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_env_file() -> None:
    for candidate in (_REPO_ROOT / ".env", _SOURCE_DIR / ".env"):
        if candidate.is_file():
            load_dotenv(candidate)
            return
    load_dotenv(_REPO_ROOT / ".env")


_load_env_file()

TALENTOS_API_BASE_URL = os.environ.get("TALENTOS_API_BASE_URL", "").rstrip("/")
API_TIMEOUT = int(os.environ.get("TALENTOS_API_TIMEOUT", "30"))
CONFIG_ERROR = (
    "TALENTOS_API_BASE_URL is not set "
)


mcp = FastMCP("TalentOS")
_client: httpx.Client | None = None
if TALENTOS_API_BASE_URL:
    _client = httpx.Client(
        base_url=f"{TALENTOS_API_BASE_URL}/api/v1",
        timeout=API_TIMEOUT,
    )
    atexit.register(_client.close)


def _error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
        if isinstance(body, dict):
            return body.get("message") or body.get("detail") or str(body)
    except ValueError:
        pass
    return response.text or f"HTTP {response.status_code}"


def api_request(
    method: str,
    path: str,
    *,
    params: dict | None = None,
    json_data: dict | None = None,
) -> dict[str, Any]:
    if _client is None:
        return {"status": "error", "message": CONFIG_ERROR}
    try:
        response = _client.request(method, path, params=params, json=json_data)
        response.raise_for_status()
        if response.status_code == 204 or not response.content:
            return {"status": "success"}
        return response.json()
    except httpx.HTTPStatusError as exc:
        return {
            "status": "error",
            "http_status": exc.response.status_code,
            "message": _error_message(exc.response),
        }
    except httpx.RequestError as exc:
        return {"status": "error", "message": f"Failed to reach talentOS Backend API: {exc}"}


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


@mcp.tool()
def get_benched_candidates(designation: str) -> dict[str, Any]:
    """Fetch employees currently on the bench for a given designation."""
    return api_request("GET", "/users/benched", params={"designation": designation})


# ---------------------------------------------------------------------------
# Designations
# ---------------------------------------------------------------------------


@mcp.tool()
def get_all_designations() -> dict[str, Any]:
    """List all unique designation names in the organization."""
    result = api_request("GET", "/designations")
    if result.get("status") == "error":
        return result
    return {"status": "success", "designations": result}


@mcp.tool()
def get_designation_detail(name: str) -> dict[str, Any]:
    """Get designation details including band level and KPIs."""
    return api_request("GET", "/designation", params={"name": name})


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------


@mcp.tool()
def get_all_jobs() -> dict[str, Any]:
    """Fetch all job listings."""
    return api_request("GET", "/jobs/")


@mcp.tool()
def get_job_by_id(job_id: str) -> dict[str, Any]:
    """Fetch a single job listing by UUID."""
    return api_request("GET", f"/jobs/{job_id}")


@mcp.tool()
def create_job(
    title: str,
    department: str,
    location: str,
    type: str,
    description: str,
    requirements: list[str],
    benefits: list[str],
    is_active: bool,
) -> dict[str, Any]:
    """Create a new job posting."""
    payload = {
        "title": title,
        "department": department,
        "location": location,
        "type": type,
        "description": description,
        "requirements": requirements,
        "benefits": benefits,
        "is_active": is_active,
    }
    return api_request("POST", "/jobs/", json_data=payload)


@mcp.tool()
def update_job(
    job_id: str,
    title: str,
    department: str,
    location: str,
    type: str,
    description: str,
    requirements: list[str],
    benefits: list[str],
    is_active: bool,
) -> dict[str, Any]:
    """Update an existing job posting."""
    payload = {
        "title": title,
        "department": department,
        "location": location,
        "type": type,
        "description": description,
        "requirements": requirements,
        "benefits": benefits,
        "is_active": is_active,
    }
    return api_request("PUT", f"/jobs/{job_id}", json_data=payload)


@mcp.tool()
def delete_job(job_id: str) -> dict[str, Any]:
    """Delete a job posting by UUID."""
    return api_request("DELETE", f"/jobs/{job_id}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"TalentOS MCP server starting on port {port}")

    if TALENTOS_API_BASE_URL:
        print(f"Calling talentOS Backend API at {TALENTOS_API_BASE_URL}/api/v1")
    else:
        print(f"WARNING: {CONFIG_ERROR}")

    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
