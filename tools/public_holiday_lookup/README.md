# Public Holiday Lookup

Fetches public holiday data for a country and year from the free Nager.Date API. No API key is required.

## Parameters

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `country_code` | `string` | Yes | Two-letter ISO 3166-1 alpha-2 country code, such as `US` or `CA`. |
| `year` | `integer` | No | Calendar year to query. Defaults to the current year. |
| `include_subdivisions` | `boolean` | No | Include ISO 3166-2 subdivision codes. Defaults to `true`. |

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```python
from tool import run_tool

response = run_tool(country_code="CA", year=2026)
print(response)
```

The returned data includes the holiday date, English name, country code, national-holiday flag, and holiday types. It also includes subdivision codes unless `include_subdivisions=False` is passed.

## Data source

This tool uses the Nager.Date Community API endpoint `GET /api/v4/Holidays/{CountryCode}/{Year}`.
