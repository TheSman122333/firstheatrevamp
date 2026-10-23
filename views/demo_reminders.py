"""Demo-only reminder timing for the activity tracker, set on the Settings page.

Temporary, for showing reminders without waiting 20 minutes. To remove it:
delete this file and the lines marking demo reminders in views/settings.py
and views/tracker.py.
"""

import flet as ft

from views.sliders import side_gradient, slider_block

DARK = "#172033"
MUTED = "#64748B"
DEMO_INK = "#92400E"

#seconds between reminders, with slider labels
EVERY = [(15, "15s"), (30, "30s"), (60, "1m"), (120, "2m"), (300, "5m"), (600, "10m"), (1200, "20m")]

#break length in minutes, shown in the reminder text
BREAKS = [1, 2, 3, 4, 5]

#seconds each reminder stays up before it counts as missed
WINDOWS = [10, 15, 20, 30]

DEFAULTS = {"custom": False, "every_seconds": 30, "break_minutes": 1, "window_seconds": 30}


def saved_reminders(settings):
    "the saved demo settings, falling back to defaults for anything missing or invalid"

    saved = settings.get("reminders")
    current = dict(DEFAULTS)

    if not isinstance(saved, dict):
        return current

    if isinstance(saved.get("custom"), bool):
        current["custom"] = saved["custom"]

    choices = {
        "every_seconds": [seconds for seconds, _ in EVERY],
        "break_minutes": BREAKS,
        "window_seconds": WINDOWS
    }

    for key, allowed in choices.items():
        if saved.get(key) in allowed and not isinstance(saved.get(key), bool):
            current[key] = saved[key]

    return current


def demo_timing(settings):
    "demo timing for the tracker, or None to follow today's heat"

    current = saved_reminders(settings)

    if not current["custom"]:
        return None

    del current["custom"]
    return current


def every_text(seconds):
    if seconds < 60:
        return f"{seconds} s"

    return f"{seconds // 60} min"


def demo_reminder_section(page, settings, on_save):
    "Settings card for the demo reminder timing"

    current = saved_reminders(settings)
    every_values = [seconds for seconds, _ in EVERY]

    switch = ft.Switch(value=current["custom"])

    every = ft.Slider(
        min=0,
        max=len(EVERY) - 1,
        divisions=len(EVERY) - 1,
        value=every_values.index(current["every_seconds"])
    )

    break_length = ft.Slider(
        min=BREAKS[0],
        max=BREAKS[-1],
        divisions=len(BREAKS) - 1,
        value=current["break_minutes"]
    )

    window = ft.Slider(
        min=0,
        max=len(WINDOWS) - 1,
        divisions=len(WINDOWS) - 1,
        value=WINDOWS.index(current["window_seconds"])
    )

    every_block, every_value, _ = slider_block(
        "Remind me every",
        every,
        [label for _, label in EVERY],
        side_gradient(["#FDBA74", "#FED7AA", "#E2E8F0"])
    )

    break_block, break_value, _ = slider_block(
        "Break length",
        break_length,
        [f"{minutes}m" for minutes in BREAKS]
    )

    window_block, window_value, _ = slider_block(
        "Reminder stays up",
        window,
        [f"{seconds}s" for seconds in WINDOWS]
    )

    timing = ft.Column(
        controls=[every_block, break_block, window_block],
        spacing=14,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH
    )

    note = ft.Text("", size=12, color=MUTED, visible=False)

    def chosen():
        return {
            "custom": bool(switch.value),
            "every_seconds": every_values[round(every.value)],
            "break_minutes": round(break_length.value),
            "window_seconds": WINDOWS[round(window.value)]
        }

    def show():
        values = chosen()

        every_value.value = every_text(values["every_seconds"])
        break_value.value = f"{values['break_minutes']} min"
        window_value.value = f"{values['window_seconds']} s"

        for slider in (every, break_length, window):
            slider.disabled = not values["custom"]

        timing.opacity = 1 if values["custom"] else 0.45

    async def save(_event=None):
        values = chosen()
        show()

        try:
            await on_save({**settings, "reminders": values})

            if values["custom"]:
                note.value = (
                    f"Saved. My Plan's activity tracker now reminds you every "
                    f"{every_text(values['every_seconds'])} of activity."
                )
            else:
                note.value = "Saved. The tracker follows today's heat schedule again."

        except Exception as error:
            note.value = f"Could not save reminder settings: {error}"

        note.visible = True
        page.update()

    def preview(_event=None):
        show()
        page.update()

    switch.on_change = save

    for slider in (every, break_length, window):
        slider.on_change = preview
        slider.on_change_end = save

    show()

    return ft.Container(
        bgcolor="#FFFBEB",
        border=ft.Border.all(1, "#FCD34D"),
        border_radius=16,
        padding=16,
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED, color=DEMO_INK),
                        ft.Text(
                            "Reminder settings",
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color=DARK
                        ),
                        ft.Container(
                            bgcolor="#FDE68A",
                            border_radius=999,
                            padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                            content=ft.Text("DEMO", size=11, weight=ft.FontWeight.W_800, color=DEMO_INK)
                        )
                    ],
                    spacing=8
                ),
                ft.Row(
                    controls=[
                        ft.Text(
                            "Use my own reminder timing",
                            size=15,
                            weight=ft.FontWeight.W_600,
                            color=DARK,
                            expand=True
                        ),
                        switch
                    ]
                ),
                ft.Text(
                    "For demos. Replaces the heat-based break schedule "
                    "(a break every 15–20 minutes) on My Plan's activity tracker. "
                    "Turn it off to go back.",
                    size=12,
                    color=MUTED
                ),
                timing,
                note
            ],
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH
        )
    )
