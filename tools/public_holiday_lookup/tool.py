"""Public holiday lookup tool backed by the Nager.Date API."""

from datetime import date
from typing import Any, Dict, Optional

import requests


API_URL = "https://date.nager.at/api/v4/Holidays/{country_code}/{year}"


def run_tool(
    country_code: str,
    year: Optional[int] = None,
    include_subdivisions: bool = True,
    **_: Any,
) -> Dict[str, Any]:
    """Return public holidays for an ISO 3166-1 alpha-2 country code and year."""
    normalized_country_code = (country_code or "").strip().upper()
    if len(normalized_country_code) != 2 or not normalized_country_code.isalpha():
        return {
            "success": False,
            "error": "country_code must be a two-letter ISO 3166-1 alpha-2 code, such as US or CA.",
        }

    requested_year = date.today().year if year is None else year
    if not isinstance(requested_year, int) or not 1900 <= requested_year <= 2100:
        return {
            "success": False,
            "error": "year must be an integer between 1900 and 2100.",
        }

    try:
        response = requests.get(
            API_URL.format(country_code=normalized_country_code, year=requested_year),
            headers={"Accept": "application/json", "User-Agent": "agent-tools-mcp-hub"},
            timeout=15,
        )
    except requests.RequestException as exc:
        return {"success": False, "error": f"Network error contacting Nager.Date: {exc}"}

    if response.status_code == 404:
        return {
            "success": False,
            "error": f"No holiday data was found for {normalized_country_code} in {requested_year}.",
        }
    if response.status_code != 200:
        return {
            "success": False,
            "error": f"Nager.Date returned status {response.status_code}.",
        }

    try:
        holidays = response.json()
    except ValueError:
        return {"success": False, "error": "Nager.Date returned invalid JSON."}

    if not isinstance(holidays, list):
        return {"success": False, "error": "Nager.Date returned an unexpected response format."}

    result = []
    for holiday in holidays:
        if not isinstance(holiday, dict):
            continue
        item = {
            "date": holiday.get("date"),
            "name": holiday.get("name"),
            "country_code": holiday.get("countryCode"),
            "national_holiday": holiday.get("nationalHoliday"),
            "holiday_types": holiday.get("holidayTypes", []),
        }
        if include_subdivisions:
            item["subdivision_codes"] = holiday.get("subdivisionCodes")
        result.append(item)

    return {
        "success": True,
        "data": {
            "country_code": normalized_country_code,
            "year": requested_year,
            "count": len(result),
            "holidays": result,
        },
    }


if __name__ == "__main__":
    print(run_tool(country_code="US", year=date.today().year))
