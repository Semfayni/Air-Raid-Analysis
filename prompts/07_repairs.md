# 07 Repairs

Documented repair examples:

- Streamlit navigation duplicate paths: multiple pages used callables named `render`; fixed with explicit `url_path` values.
- Datetime dtype test brittleness: test expected exact nanosecond precision; fixed by checking timezone-aware UTC datetime semantics.
- Anomaly backend missing region: pandas `groupby.apply` dropped `region`; fixed with an explicit per-region scoring loop.
- Map layer optional schema issue: code expected `oblast_index`; fixed unmatched detection to use missing status after join.
- Map missing value issue: unmatched GeoJSON status code became `NaN`; fixed by assigning Python `None` with object dtype.

Repair evidence placeholder:

```text
Paste relevant failing test output, screenshots, or final passing test output here.
```
