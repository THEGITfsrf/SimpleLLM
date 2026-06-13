import requests

description = "Get current weather and short forecast for a city using wttr.in."
args = {
    "location": {"type": "string", "description": "City or location, e.g. Denver or New York"},
    "days": {"type": "integer", "description": "Forecast days 1-3"},
}
required = ["location"]


def main(location, days=1):
    try:
        d = max(1, min(int(days or 1), 3))
        loc = (location or "").strip()
        if not loc:
            return {"error": "location is required"}

        url = f"https://wttr.in/{loc}"
        params = {"format": "j1"}
        resp = requests.get(url, params=params, timeout=8)
        resp.raise_for_status()
        data = resp.json()

        current = (data.get("current_condition") or [{}])[0]
        weather = data.get("weather") or []

        out = {
            "location": loc,
            "current": {
                "temp_c": current.get("temp_C"),
                "temp_f": current.get("temp_F"),
                "feels_like_c": current.get("FeelsLikeC"),
                "feels_like_f": current.get("FeelsLikeF"),
                "humidity": current.get("humidity"),
                "wind_kmph": current.get("windspeedKmph"),
                "description": ((current.get("weatherDesc") or [{}])[0]).get("value"),
            },
            "forecast": [],
        }

        for day in weather[:d]:
            out["forecast"].append({
                "date": day.get("date"),
                "max_c": day.get("maxtempC"),
                "max_f": day.get("maxtempF"),
                "min_c": day.get("mintempC"),
                "min_f": day.get("mintempF"),
                "avg_humidity": day.get("avghumidity"),
                "sunrise": ((day.get("astronomy") or [{}])[0]).get("sunrise"),
                "sunset": ((day.get("astronomy") or [{}])[0]).get("sunset"),
            })

        return out
    except Exception as e:
        return {"error": f"weather tool failed: {e}"}
