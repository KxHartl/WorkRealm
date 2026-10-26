# data

- `raw/` — input data exactly as received. **Write-once**: never edited, never deleted.
- `processed/` — anything derived from `raw/`. Must be reproducible from `raw/` plus code in `src/`;
  say how in a README next to it.

Names (R-NAMES): a received file gets a standard name before its first commit (ASCII, lowercase
kebab-case, lowercase extension), with its original name noted in this README. A derived file
keeps the stem of the file it comes from and adds what was done:
`raw/survey-2026.csv` → `processed/survey-2026-cleaned.csv`.
