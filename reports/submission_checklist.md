# Submission Checklist

- [ ] Run `python -m pytest -q`.
- [ ] Run `streamlit run streamlit_app.py`.
- [ ] Confirm Overview loads historical CSV metrics.
- [ ] Confirm Regional Explorer filters work.
- [ ] Confirm Live Map shows either a choropleth or the expected GeoJSON fallback table.
- [ ] Confirm Anomaly Lab shows scoring controls and exploratory warning.
- [ ] Confirm the external AI log and `reports/reflection.md` explain architecture, mistakes, and repairs.
- [ ] Add screenshots to the README section or submission materials.
- [ ] Do not commit `.env` or any real alerts.in.ua token.
- [ ] If using the map, place GeoJSON at `data/geo/ukraine_oblasts.geojson`.
