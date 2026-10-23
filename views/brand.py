"FirstHeat logo, name and tagline for the top of a screen."

from pathlib import Path

import flet as ft

LOGO = (
    Path(__file__).resolve().parent.parent / "assets" / "logo" / "firstheat-mark.svg"
).read_bytes()

DARK = "#172033"
MUTED = "#64748B"
BRAND_ORANGE = "#EA580C"


def brand_header():
    "logo: sun with a '1' for First, heartbeat line for safety"

    return ft.Row(
        controls=[
            ft.Image(
                src=LOGO,
                width=56,
                height=56,
                semantics_label="FirstHeat logo"
            ),
            ft.Column(
                controls=[
                    ft.Text(
                        spans=[
                            ft.TextSpan(
                                "First",
                                style=ft.TextStyle(color=DARK)
                            ),
                            ft.TextSpan(
                                "Heat",
                                style=ft.TextStyle(color=BRAND_ORANGE)
                            )
                        ],
                        size=36,
                        weight=ft.FontWeight.W_900,
                        style=ft.TextStyle(
                            height=1.05,
                            letter_spacing=-0.5
                        )
                    ),
                    ft.Container(
                        padding=ft.Padding.only(left=12),
                        content=ft.Text(
                            "Your adaptive heat-safety planner",
                            size=15,
                            color=MUTED,
                            italic=True
                        )
                    )
                ],
                spacing=0,
                expand=True
            )
        ],
        spacing=12
    )
