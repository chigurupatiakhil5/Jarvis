import os
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

_LAT = os.environ.get("LOCATION_LAT", "30.26715")
_LON = os.environ.get("LOCATION_LON", "-97.74306")
_TIMEZONE = os.environ.get("LOCATION_TIMEZONE", "America/Chicago")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
def get_weather() -> dict:
    response = httpx.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": _LAT,
            "longitude": _LON,
            "current": "temperature_2m,wind_speed_10m,precipitation,cloud_cover",
            "daily": "sunset",
            "timezone": _TIMEZONE,
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
        },
        timeout=10.0,
    )
    response.raise_for_status()
    data = response.json()
    current = data["current"]
    return {
        "temperature_f": current["temperature_2m"],
        "wind_speed_mph": current["wind_speed_10m"],
        "precipitation_in": current["precipitation"],
        "cloud_cover_pct": current["cloud_cover"],
        "sunset_today": data["daily"]["sunset"][0],
    }
