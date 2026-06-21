# 02 Historical Data

Summary:

- Added the historical loader for `official_data_en.csv` and `volunteer_data_en.csv`.
- Loader checks `data/raw` first, then downloads from the dataset repository if files are missing.
- Added schema validation, UTC datetime parsing, source labels, and tests.

Reasoning:

- Historical analysis uses the CSV dataset because it is reproducible and appropriate for time-series work.
- The live API is reserved for current status.

Prompt placeholder:

```text
Paste historical data loading prompts or screenshots here.
```
