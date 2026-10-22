"""Web entry point for hosting FirstHeat (used by Vercel).
The desktop app still starts from main.py with ft.run(main)."""
from pathlib import Path

import flet_web.fastapi as flet_fastapi

from main import main

#assets/ holds the FirstHeat logo, browser icons and manifest
app = flet_fastapi.app(
    main,
    assets_dir=str(Path(__file__).resolve().parent / "assets"),
    app_name="FirstHeat",
    app_description="Your adaptive heat-safety planner"
)
