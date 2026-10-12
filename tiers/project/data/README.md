# data

- `raw/` — input data exactly as received. **Write-once**: never edited, never deleted.
- `processed/` — anything derived from `raw/`. Must be reproducible from `raw/` plus code in `src/`;
  say how in a README next to it.
