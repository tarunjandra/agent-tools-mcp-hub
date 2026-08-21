# Open-Meteo Weather API Tool

A tool to fetch current weather data using the keyless Open-Meteo REST service.

## Parameters

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `latitude` | `number` | Yes | Geographical WGS84 latitude coordinate (e.g., 51.5074) |
| `longitude` | `number` | Yes | Geographical WGS84 longitude coordinate (e.g., -0.1278) |

## Installation & Setup

```bash
pip install -r requirements.txt
```

## Usage Example

```python
from tool import run_tool

# Get weather for London, UK
response = run_tool(latitude=51.5074, longitude=-0.1278)
print(response)
```
