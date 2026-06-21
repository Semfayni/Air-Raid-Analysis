# Ukraine Air Alert Intelligence Dashboard

A Python mini project scaffold for KSE AI Agentic Summer School.

This app is framed as exploratory analysis and visualization of Ukrainian air raid alert data. It does not predict attacks or provide safety instructions. For real-time safety decisions, use official Ukrainian alert channels and local authorities.

## Planned Data Sources

- Historical alerts dataset: https://github.com/Vadimkin/ukrainian-air-raid-sirens-dataset
- Live alert status API: https://devs.alerts.in.ua/

The live API token must be provided through environment configuration and must never be hardcoded.

## Current Scaffold

- Streamlit app shell with five pages:
  - Overview
  - Live Map
  - Regional Explorer
  - Anomaly Lab
  - AI Process
- `air_alerts` source package
- dotenv-based configuration loader
- lightweight pytest smoke tests
- prompts directory for future agent prompts and analysis notes

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Then edit `.env` and set:

```text
ALERTS_API_TOKEN=your_token_here
```

## Run The App

```powershell
streamlit run streamlit_app.py
```

## Run Tests

```powershell
pytest
```

## Project Guardrails

- Keep live API tokens out of code and version control.
- Treat the dashboard as historical exploration and visualization.
- Do not present model output as attack prediction or official warning.
- Cite data sources clearly when analysis pages are implemented.
