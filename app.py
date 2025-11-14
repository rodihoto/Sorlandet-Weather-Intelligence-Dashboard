# -*- coding: utf-8 -*-
# Streamlit app: Sør‑Norge Vær – Ukeprognose (oppgradert)
# Henter 7-dagers temperaturprognose (max/min) + nedbør + vind for utvalgte byer i Sør‑Norge.
# Kilder: Open‑Meteo (vær + geokoding).

import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date, timedelta
import pytz
import plotly.express as px
import io

st.set_page_config(page_title="Sør‑Norge Vær – Ukeprognose", page_icon="🌦️", layout="wide")

st.title("🌦️ Sør‑Norge Vær – Ukeprognose")
st.caption("Daglig maks/min temperatur, nedbør og vind – neste 7 dager • Kilde: Open‑Meteo")

# Standardbyer i Sør‑Norge (kan endres i UI)
DEFAULT_CITIES = [
    "Kristiansand", "Arendal", "Grimstad", "Mandal", "Flekkefjord",
    "Stavanger", "Sandnes", "Egersund", "Skien", "Porsgrunn"
]

with st.sidebar:
    st.header("Innstillinger")
    st.markdown("**Velg byer (Sør‑Norge):**")
    cities = st.multiselect(" ", DEFAULT_CITIES, default=DEFAULT_CITIES[:5], label_visibility="collapsed")
    free_city = st.text_input("Legg til en by (skriv navn og trykk Enter)", value="")
    if free_city:
        if free_city not in cities:
            cities.append(free_city)

    st.markdown("---")
    today = date.today()
    start_date = today
    end_date = today + timedelta(days=6)  # neste 7 dager (inklusive start)
    st.write(f"Periode: **{start_date.isoformat()} → {end_date.isoformat()}** (7 dager)")

    st.markdown("---")
    st.subheader("Dataserier")
    show_precip = st.checkbox("Inkluder nedbør (mm)", value=True)
    show_wind = st.checkbox("Inkluder vind (m/s)", value=False)

@st.cache_data(show_spinner=False)
def geocode_city(city_name: str):
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": city_name, "count": 1, "language": "nb", "format": "json"}
    r = requests.get(url, params=params, timeout=30)
    if r.status_code != 200:
        return None
    data = r.json()
    results = data.get("results") or []
    if not results:
        return None
    item = results[0]
    return {
        "name": item.get("name"),
        "lat": item.get("latitude"),
        "lon": item.get("longitude"),
        "country": item.get("country"),
        "admin1": item.get("admin1"),
    }

@st.cache_data(show_spinner=False)
def fetch_daily_forecast(lat: float, lon: float, start: date, end: date, tz: str = "Europe/Oslo",
                         need_precip: bool = True, need_wind: bool = False):
    url = "https://api.open-meteo.com/v1/forecast"
    daily_vars = ["temperature_2m_max", "temperature_2m_min"]
    if need_precip:
        daily_vars += ["precipitation_sum", "precipitation_probability_max"]
    if need_wind:
        daily_vars += ["wind_speed_10m_max"]
    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": tz,
        "daily": ",".join(daily_vars),
        "start_date": start.isoformat(),
        "end_date": end.isoformat()
    }
    r = requests.get(url, params=params, timeout=30)
    if r.status_code != 200:
        return None
    js = r.json()
    daily = js.get("daily") or {}
    if not daily:
        return None
    df = pd.DataFrame(daily)
    # Sikre kolonnenavn
    rename_map = {
        "time": "date",
        "temperature_2m_max": "tmax",
        "temperature_2m_min": "tmin",
        "precipitation_sum": "precip_mm",
        "precipitation_probability_max": "precip_prob",
        "wind_speed_10m_max": "wind_max"
    }
    df = df.rename(columns=rename_map)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df

# Hent data
rows = []
geo_cache = {}

for city in cities:
    geo = geocode_city(city)
    if not geo:
        st.warning(f"Fant ikke koordinater for **{city}** – hopper over.")
        continue
    geo_cache[city] = geo
    df = fetch_daily_forecast(geo["lat"], geo["lon"], start_date, end_date,
                              need_precip=show_precip, need_wind=show_wind)
    if df is None or df.empty:
        st.warning(f"Ingen prognosedata for **{city}** i perioden.")
        continue
   df["city"] = geo["name"]
    df["lat"] = geo["lat"]      
    df["lon"] = geo["lon"]     
    rows.append(df)

if not rows:
    st.error("Ingen data å vise. Prøv andre byer eller periode.")
    st.stop()

data = pd.concat(rows, ignore_index=True)

# Temperatur-plot (maks/min)
st.subheader("Temperatur (°C) – Maks/Min per dag")
long_temp = data.melt(id_vars=["date", "city"], value_vars=["tmax", "tmin"],
                      var_name="type", value_name="temp_c")
type_labels = {"tmax": "Maks temp (°C)", "tmin": "Min temp (°C)"}
long_temp["type"] = long_temp["type"].map(type_labels)
fig_temp = px.line(long_temp, x="date", y="temp_c", color="city", line_dash="type",
                   markers=True, labels={"date": "Dato", "temp_c": "Temperatur (°C)", "city": "By"})
st.plotly_chart(fig_temp, use_container_width=True)

# Ekstra plot: nedbør
if show_precip and all(col in data.columns for col in ["precip_mm"]):
    st.subheader("Nedbør (mm) – Daglig sum")
    fig_p = px.bar(data, x="date", y="precip_mm", color="city",
                   labels={"date": "Dato", "precip_mm": "Nedbør (mm)", "city": "By"})
    st.plotly_chart(fig_p, use_container_width=True)

# Ekstra plot: vind
if show_wind and "wind_max" in data.columns:
    st.subheader("Vind (m/s) – Maks per dag")
    fig_w = px.line(data, x="date", y="wind_max", color="city", markers=True,
                    labels={"date": "Dato", "wind_max": "Vind maks (m/s)", "city": "By"})
    st.plotly_chart(fig_w, use_container_width=True)
# ─────────────────────────────────────────────
# 🌍 Interaktivt kart – Plotly Mapbox
# ─────────────────────────────────────────────
st.subheader("📍 Interaktivt kart – temperatur, nedbør og vind")

map_df = data.copy()

# Hvis nedbør ikke valgt, sett nedbør = 0 for kartet
if "precip_mm" not in map_df.columns:
    map_df["precip_mm"] = 0.0

# Hvis vind ikke valgt, sett vind = 0
if "wind_max" not in map_df.columns:
    map_df["wind_max"] = 0.0

# Bruke siste dato i perioden (den ferskeste prognosen)
latest = map_df["date"].max()
latest_df = map_df[map_df["date"] == latest]

fig_map = px.scatter_mapbox(
    latest_df,
    lat="lat",
    lon="lon",
    color="tmax",
    size="precip_mm",
    hover_name="city",
    hover_data={
        "tmax": True,
        "tmin": True,
        "precip_mm": True,
        "wind_max": True,
        "lat": False,
        "lon": False,
    },
    color_continuous_scale="Turbo",
    size_max=25,
    zoom=5,
    height=500,
)

fig_map.update_layout(
    mapbox_style="open-street-map",
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
)

st.plotly_chart(fig_map, use_container_width=True)


# Tabell
st.subheader("Tabell – daglige verdier")
st.dataframe(data.sort_values(["city", "date"]).reset_index(drop=True))

# Eksport-knapper
csv_bytes = data.sort_values(["city", "date"]).to_csv(index=False).encode("utf-8")
st.download_button("📥 Last ned CSV", data=csv_bytes, file_name="var_ukeprognose_sor-norge.csv", mime="text/csv")

# Innsikt
st.subheader("Innsikt (per by)")
insights = []
for city, dfc in data.groupby("city"):
    mx = dfc["tmax"].max()
    mn = dfc["tmin"].min()
    coldest = dfc.loc[dfc["tmin"].idxmin(), "date"]
    warmest = dfc.loc[dfc["tmax"].idxmax(), "date"]
    msg = f"• **{city}** – høyeste maks: **{mx:.1f}°C** ({warmest}), laveste min: **{mn:.1f}°C** ({coldest})"
    if "precip_mm" in dfc.columns:
        wet = dfc.loc[dfc["precip_mm"].idxmax(), "date"]
        wet_mm = dfc["precip_mm"].max()
        msg += f", våteste dag: **{wet} ({wet_mm:.1f} mm)**"
    if "wind_max" in dfc.columns:
        wday = dfc.loc[dfc["wind_max"].idxmax(), "date"]
        wval = dfc["wind_max"].max()
        msg += f", mest vind: **{wday} ({wval:.1f} m/s)**"
    msg += "."
    insights.append(msg)
st.markdown("\n".join(insights))

st.caption("Kilder: Open‑Meteo Weather Forecast API og Geocoding API (ingen API‑nøkkel kreves).")
