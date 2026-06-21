# Ukraine Air Alert Intelligence Dashboard

Exploratory Streamlit dashboard for analyzing Ukrainian air raid alert history, viewing current live alert status, and inspecting unusual daily alert activity near Ukrainian holidays and important dates.

This project is for analysis and visualization only. It is not an attack prediction tool, operational warning system, or substitute for official Ukrainian safety channels.

## Main Features

- Historical overview with total alerts, alert hours, daily trends, and top regions.
- Regional explorer with date/source filters, daily trends, hourly-weekday heatmap, and monthly summaries.
- Live map page using alerts.in.ua current oblast status, with a safe fallback table when map geometry is unavailable.
- Anomaly lab with transparent rolling anomaly scores and nearby holiday/date context.
- AI process page documenting architecture, prompt stages, test failures, and repairs.

## Data Sources

- Historical CSV dataset: [Vadimkin Ukrainian Air Raid Sirens Dataset](https://github.com/Vadimkin/ukrainian-air-raid-sirens-dataset)
  - `official_data_en.csv`
  - `volunteer_data_en.csv`
- Live status only: [alerts.in.ua API](https://devs.alerts.in.ua/)

Historical analysis uses the CSV dataset for reproducibility. The alerts.in.ua API is used only for current live status and future live-map workflows.

## Safety Disclaimer

The dashboard may help explore historical patterns, but it does not make predictions or provide safety guidance. For real-time decisions, use official alerts, local authorities, and trusted emergency channels.

## Run Locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
streamlit run streamlit_app.py
```

Then open the local Streamlit URL shown in the terminal.

## API Token

The live map status client reads the alerts.in.ua token from `.env`:

```text
ALERTS_API_TOKEN=your_token_here
```

Do not commit a real token. Historical pages do not need this token.

## Tests

```powershell
python -m pytest -q
```

Tests use mocked live API calls and do not contact alerts.in.ua.

## Project Structure

```text
src/air_alerts/
  app.py                 Streamlit navigation
  data/                  Historical CSV loader and source metadata
  features.py            Kyiv timezone, duration, date, and region features
  holidays.py            Public holiday and important-date proximity features
  anomalies.py           Rolling anomaly scoring backend
  live_api.py            Token-safe alerts.in.ua live status client
  map_viz.py             Live map data preparation and Plotly choropleth helper
  dashboard.py           Pure helpers for overview and regional pages
  anomaly_view.py        Pure helpers for anomaly lab tables/summaries
  pages/                 Streamlit pages
prompts/                 AI-assisted development prompt log placeholders
reports/                 Submission reflection and checklist
tests/                   Unit tests
```

## Methodology

- Kyiv timezone conversion: source timestamps are parsed as UTC, then Kyiv-local columns are added for calendar and daily analysis.
- Daily aggregations: alert counts and durations are aggregated by Kyiv-local date; unfinished alerts are excluded from default historical summaries.
- Holiday proximity: Ukrainian public holidays and selected important dates are added as nearby context for daily rows.
- Rolling anomaly score: daily region-level alert count and duration are combined into a transparent activity score and compared with a rolling regional baseline.
- Live map status: compact alerts.in.ua oblast statuses are normalized into `active`, `partial`, `no_alert`, or `unknown`.

## Limitations

- The anomaly lab highlights unusual activity for inspection; it does not explain why activity occurred.
- Holiday proximity is context, not proof of a relationship.
- Historical results depend on source dataset coverage and schema stability.
- The live API requires a valid local token and network access.
- The live map needs a GeoJSON file at `data/geo/ukraine_oblasts.geojson` for map geometry. Without it, the app shows a fallback status table.

## AI-Assisted Development Process

The AI Process page and `prompts/` directory document how the project was built with iterative prompts, tests, and repairs. The log is intentionally a concise support artifact, not a fake full chat export.

Notable repairs included:

- Explicit Streamlit `url_path` values after duplicate inferred page routes.
- Semantic datetime tests instead of exact pandas timestamp precision.
- Explicit per-region anomaly scoring after `groupby.apply` dropped `region`.
- Schema-tolerant map joins and missing-value normalization for unmatched GeoJSON rows.

## Screenshots

Add final screenshots here before submission:

- Overview page:
- Regional Explorer:
- Live Map fallback or map:
- Anomaly Lab:
- AI Process:
