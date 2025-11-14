# -*- coding: utf-8 -*-
# Sør-Norge Weather Intelligence Dashboard (Final Version with Mandal Fix)
# Streamlit + Plotly + Open-Meteo API

import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta
import plotly.express as px
import pytz  # reservert hvis vi trenger tidsone senere

# ─────────────────────────────────────────────
#   PAGE SETTINGS
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Sør-Norge Weather Intelligence Dashboard",
    page_icon="🌦️",
    layout="wide"
)

st.title("🌦️ Sør-Norge Weather Intelligence Dashboard")
st.caption("7-dagers prognose: temperatur, nedbør og vind – med interaktive grafer og kart.")


# ─────────────────────────────────────────────
#   SIDEBAR SETTINGS
# ─────────────────────────────────────────────
DEFAULT_CITIES = [
    "Kristiansand", "Arendal", "Grimstad", "Mandal", "Flekkefjord",
    "Stavanger", "Sandnes", "Egersund", "Skien", "Porsgrunn"
]

with st.sidebar:
    st.header("⚙️ Innstillinger")

    cities = st.multiselect(
        "Velg byer i Sør-Norge:",
        DEFAULT_CITIES,
        default=DEFAULT_CITIES[:5]
    )

    extra_city = st.text_input("Legg til en ekstra by:")
    if extra_city and extra_city not in cities:
        cities.append(extra_city)

    st.markdown("---")
    today = date.today()
    start_date = today
    end_date = today + timedelta(days=6)

    st.write(f"**Periode:** {start_date} → {end_date} (7 dager)")

    show_precip = st.checkbox("Vis nedbør (mm)", value=True)
    show_wind = st.checkbox("Vis vind (m/s)", value=False)


# ─────────────────────────────────────────────
#   HELPER FUNCTIONS
# ─────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def geocode_city(city_name: str):
    """
    Geocoding via Open-Meteo, men vi godtar KUN treff i Norge
    for å unngå feil som Mandal → Mandalay (Myanmar).
    """
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": city_name,
        "count": 10,         # hent flere treff
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
    norwegian_hits = [
        item for item in results
        if item.get("country") in ("Norway", "Norge")
    ]

    if not norwegian_hits:
        # hvis ingen norske treff, returner None (hopper over byen)
        return None

    # ta første norske treff
    item = norwegian_hits[0]
    return {
        "name": item.get("name"),
        "lat": item.get("latitude"),
        "lon": item.get("longitude"),
        "country": item.get("country"),
    }


@st.cache_data(show_spinner=False)
def fetch_daily(
    lat: float,
    lon: float,
    start: date,
    end: date,
    need_precip: bool = True,
    need_wind: bool = False,
):
    """Hent daglige verdier fra Open-Meteo Forecast API."""
    daily_vars = ["temperature_2m_max", "temperature_2m_min"]
    if need_precip:
        daily_vars += ["precipitation_sum", "precipitation_probability_max"]
    if need_wind:
        daily_vars += ["wind_speed_10m_max"]

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": "Europe/Oslo",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": ",".join(daily_vars),
    }

    r = requests.get(url, params=params, timeout=20)
    if r.status_code != 200:
        return None

    js = r.json()
    daily = js.get("daily") or {}
    if not daily:
        return None

    df = pd.DataFrame(daily)
    df = df.rename(
        columns={
            "time": "date",
            "temperature_2m_max": "tmax",
            "temperature_2m_min": "tmin",
            "precipitation_sum": "precip_mm",
            "precipitation_probability_max": "precip_prob",
            "wind_speed_10m_max": "wind_max",
        }
    )
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


# ─────────────────────────────────────────────
#   FETCH DATA FOR SELECTED CITIES
# ─────────────────────────────────────────────
rows = []

for city in cities:
    geo = geocode_city(city)

    if not geo:
        st.warning(f"❗ Fant ikke norske koordinater for {city} – hopper over.")
        continue

    df = fetch_daily(
        geo["lat"],
        geo["lon"],
        start_date,
        end_date,
        need_precip=show_precip,
        need_wind=show_wind,
    )

    if df is None or df.empty:
        st.warning(f"⚠️ Ingen data tilgjengelig for {city}.")
        continue

    df["city"] = geo["name"]
    df["lat"] = geo["lat"]
    df["lon"] = geo["lon"]
    rows.append(df)

if not rows:
    st.error("Ingen data å vise! Velg minst én by i sidepanelet.")
    st.stop()

data = pd.concat(rows, ignore_index=True)


# ─────────────────────────────────────────────
#   TEMPERATURE PLOT
# ─────────────────────────────────────────────
st.subheader("🌡️ Temperatur – maks/min")

temp_long = data.melt(
    id_vars=["date", "city"],
    value_vars=["tmax", "tmin"],
    var_name="type",
    value_name="temp",
)

temp_long["type"] = temp_long["type"].map(
    {
        "tmax": "Maks temperatur (°C)",
        "tmin": "Min temperatur (°C)",
    }
)

fig_temp = px.line(
    temp_long,
    x="date",
    y="temp",
    color="city",
    line_dash="type",
    markers=True,
    labels={"date": "Dato", "temp": "Temperatur (°C)", "city": "By"},
)

st.plotly_chart(fig_temp, use_container_width=True)


# ─────────────────────────────────────────────
#   PRECIPITATION PLOT
# ─────────────────────────────────────────────
if show_precip and "precip_mm" in data.columns:
    st.subheader("🌧️ Nedbør (mm)")

    fig_p = px.bar(
        data,
        x="date",
        y="precip_mm",
        color="city",
        labels={"date": "Dato", "precip_mm": "Nedbør (mm)", "city": "By"},
    )

    st.plotly_chart(fig_p, use_container_width=True)


# ─────────────────────────────────────────────
#   WIND PLOT
# ─────────────────────────────────────────────
if show_wind and "wind_max" in data.columns:
    st.subheader("💨 Vind – maks per dag")

    fig_w = px.line(
        data,
        x="date",
        y="wind_max",
        color="city",
        markers=True,
        labels={"date": "Dato", "wind_max": "Vind maks (m/s)", "city": "By"},
    )

    st.plotly_chart(fig_w, use_container_width=True)


# ─────────────────────────────────────────────
#   INTERACTIVE MAP (FIXED MARKER SIZE)
# ─────────────────────────────────────────────
st.subheader("📍 Interaktivt kart – temperatur / nedbør / vind")

map_df = data.copy()

# Fallback-verdier hvis kolonner mangler
if "precip_mm" not in map_df.columns:
    map_df["precip_mm"] = 0.0
if "wind_max" not in map_df.columns:
    map_df["wind_max"] = 0.0

# Vi bruker første dag i perioden som kart-snitt (kan byttes til alle dager)
first_day = map_df["date"].min()
day_df = map_df[map_df["date"] == first_day]

# Hvis du heller vil vise alle dagene på kartet, bruk:
# day_df = map_df

fig_map = px.scatter_mapbox(
    day_df,
    lat="lat",
    lon="lon",
    color="tmax",  # farge = temperatur
    hover_name="city",
    hover_data={
        "date": True,
        "tmax": True,
        "tmin": True,
        "precip_mm": True,
        "wind_max": True,
        "lat": False,
        "lon": False,
    },
    color_continuous_scale="Turbo",
    zoom=5,
    height=550,
)

# Fast punktstørrelse slik at de alltid er synlige
fig_map.update_traces(marker=dict(size=18))

fig_map.update_layout(
    mapbox_style="open-street-map",
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
)

st.plotly_chart(fig_map, use_container_width=True)


# ─────────────────────────────────────────────
#   TABLE
# ─────────────────────────────────────────────
st.subheader("📄 Datatabell")
st.dataframe(data.sort_values(["city", "date"]).reset_index(drop=True))


# ─────────────────────────────────────────────
#   INSIGHTS
# ─────────────────────────────────────────────
st.subheader("🧠 Innsikt per by")

ins_lines = []
for city, dfc in data.groupby("city"):
    warmest = dfc.loc[dfc["tmax"].idxmax()]
    coldest = dfc.loc[dfc["tmin"].idxmin()]

    msg = (
        f"• **{city}** → "
        f"Varmest: **{warmest['tmax']}°C ({warmest['date']})**, "
        f"Kaldest: **{coldest['tmin']}°C ({coldest['date']})**"
    )

    if "precip_mm" in dfc.columns:
        wettest = dfc.loc[dfc["precip_mm"].idxmax()]
        msg += f", Mest nedbør: **{wettest['precip_mm']} mm ({wettest['date']})**"

    if "wind_max" in dfc.columns:
        w = dfc.loc[dfc["wind_max"].idxmax()]
        msg += f", Mest vind: **{w['wind_max']} m/s ({w['date']})**"

    ins_lines.append(msg)

st.markdown("\n".join(ins_lines))

st.caption("Kilder: Open-Meteo Weather Forecast API og Geocoding API.")
