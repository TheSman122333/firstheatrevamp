# CLAUDE.md: FirstHeat Revamp

UI sandbox copied from `TheSman122333/firstheat` (commit 04ec278). Used for mockups and large UI edits that shift the app's focus.

## Rules
- Any file can be edited: `views/`, `main.py`, `core/`, `data/`, styling. No AI-use restrictions and no AI_LOG entries needed here.
- Never push to or change the original repo (`TheSman122333/firstheat`) or the original Vercel project `firstheat` (firstheat.vercel.app).
- Deploys: Vercel project `firstheatrevamp` -> https://firstheatrevamp.vercel.app, linked to this repo. Pushes trigger deploys.

## Stack notes
- Python 3.12, Flet 1.0.4. Use `ft.run(main)`, not the old `ft.app(target=main)`.
- `fastapi==0.144.0` is pinned: flet-web 1.0.4 passes `openapi_prefix`, which FastAPI removed in 0.145.0. Keep the pin in `requirements.txt` and `pyproject.toml`.
- Web entry for Vercel is `app.py` (`flet_web.fastapi.app(main)`); `pyproject.toml` has `[tool.vercel] entrypoint = "app:app"`.
- Weather comes from Open-Meteo (no API key).
- `core/` has no `flet` imports, so it stays testable with pytest.
- Owner works on Windows with PowerShell and the conda env `firstheat`.

## Product wording
- Heat-safety guidance defers to official sources (CDC, NATA/KSI, OSHA/NIOSH), never promises safety, and labels WBGT as an estimate.
- Emergency mode always says to call 911 first.
