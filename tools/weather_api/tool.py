"""
Open-Meteo Weather API Tool
"""
from typing import Dict, Any
import requests

def run_tool(latitude: float, longitude: float, **kwargs: Any) -> Dict[str, Any]:
    """
    Executes the weather API logic using Open-Meteo.
    
    Args:
        latitude (float): Geographical WGS84 coordinate of the location.
        longitude (float): Geographical WGS84 coordinate of the location.
        
    Returns:
        Dict[str, Any]: Result dictionary containing status and weather data.
    """
    if latitude is None or longitude is None:
        return {
            "success": False,
            "error": "latitude and longitude parameters are required."
        }
    
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current_weather": True
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return {
            "success": True,
            "data": data.get("current_weather", {})
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Failed to fetch data from Open-Meteo API: {str(e)}"
        }

if __name__ == "__main__":
    # Test with coordinates for London, UK (51.5074, -0.1278)
    test_output = run_tool(latitude=51.5074, longitude=-0.1278)
    print("Test execution output:", test_output)
