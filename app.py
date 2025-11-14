@st.cache_data(show_spinner=False)
def geocode_city(city_name):
    """Geocoding som kun aksepterer treff i Norge."""

    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": city_name,
        "count": 10,
        "language": "nb",
        "format": "json",
    }

    r = requests.get(url, params=params, timeout=20)
    if r.status_code != 200:
        return None

    data = r.json()
    results = data.get("results") or []
    if not results:
        return None

    # Filtrer kun norske treff
    for item in results:
        if item.get("country") in ("Norway", "Norge"):
            return {
                "name": item.get("name"),
                "lat": item.get("latitude"),
                "lon": item.get("longitude"),
                "country": item.get("country"),
            }

    # Hvis ingen norske byer funnet – ignorer
    return None