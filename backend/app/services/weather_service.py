from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import get_settings


class WeatherService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def forecast(self, latitude: float, longitude: float, days: int = 5) -> dict[str, Any]:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum",
            "forecast_days": min(max(days, 1), 10),
            "timezone": "auto",
        }
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            response = client.get(self.settings.weather_base_url, params=params)
            response.raise_for_status()
            payload = response.json()
        current = payload.get("current") or {}
        daily = payload.get("daily") or {}
        dates = daily.get("time") or []
        output = []
        for idx, day in enumerate(dates):
            output.append(
                {
                    "date": day,
                    "weather_code": int((daily.get("weather_code") or [0] * len(dates))[idx] or 0),
                    "minimum_temperature": float((daily.get("temperature_2m_min") or [0] * len(dates))[idx] or 0),
                    "maximum_temperature": float((daily.get("temperature_2m_max") or [0] * len(dates))[idx] or 0),
                    "precipitation_probability": float((daily.get("precipitation_probability_max") or [0] * len(dates))[idx] or 0),
                    "precipitation_mm": float((daily.get("precipitation_sum") or [0] * len(dates))[idx] or 0),
                }
            )
        return {
            "latitude": float(payload.get("latitude", latitude)),
            "longitude": float(payload.get("longitude", longitude)),
            "timezone": str(payload.get("timezone", "auto")),
            "current_temperature": current.get("temperature_2m"),
            "current_humidity": current.get("relative_humidity_2m"),
            "current_wind_speed": current.get("wind_speed_10m"),
            "current_weather_code": current.get("weather_code"),
            "daily": output,
            "fetched_at": datetime.now(timezone.utc),
            "source": "Open-Meteo",
        }
