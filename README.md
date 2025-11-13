# 🌦️ Sør‑Norge Vær – Ukeprognose (oppgradert)

Streamlit‑dashboard som henter **7‑dagers prognose** for flere byer i Sør‑Norge:
- Temperatur **maks/min**
- (Valgfritt) **Nedbør (mm)** og **vind (m/s)**
- Interaktive grafer (Plotly), tabell og innsikt med høyeste/laveste/”våteste dag”.

## 🚀 Kjør lokalt
```bash
pip install -r requirements.txt
streamlit run app.py
```

## ☁️ Publisering på Streamlit Community Cloud
1. Last opp `app.py`, `requirements.txt`, `README.md` til et GitHub‑repo.
2. På Community Cloud: **Create app** → velg repo/branch → `app.py` → **Deploy**.
3. Du får en offentlig URL (`*.streamlit.app`). Endringer i repo → auto‑redeploy.

📖 Dokumentasjon:
- Streamlit Cloud deploy: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
- Open‑Meteo Weather API & Geocoding API: https://open-meteo.com/

## 📚 Kilder
- Open‑Meteo Weather & Geocoding API (gratis, ingen nøkkel).
- (Alternativ) MET Norway Locationforecast (krever User‑Agent) – https://api.met.no/weatherapi/locationforecast/2.0/documentation

© 2025 – Rodi Hoto.
