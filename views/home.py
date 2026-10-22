#Homepage: a brief display of today

import asyncio
import flet as ft

from core.today import fetch_today_summary


#colors
CARD_COLORS = {
    "green": ("#E5F5E9", "#166534"),
    "yellow": ("#FFF4CC", "#795500"),
    "orange": ("#FFE4D2", "#9A3412"),
    "red": ("#FCE0E0", "#991B1B"),
    "black": ("#273244", "#FFFFFF")
}

MUTED = "#64748B"
DARK = "#172033"


def build_home(page, settings):

    location = ft.Text("", size=15, color=MUTED)
    status = ft.Text("", color=MUTED)

    loading = ft.Row(
        controls=[
            ft.ProgressRing(width=20, height=20),
            ft.Text("Loading forecast...")
        ]
    )

    error = ft.Text("", color="#991B1B", visible=False)

    #current WBGT
    hour = ft.Text("CURRENT HOUR", size=13)

    temperature = ft.Text(
        "-- °F WBGT ",
        size=48,
        weight=ft.FontWeight.BOLD
    )

    category = ft.Text(
        "",
        size=20,
        weight=ft.FontWeight.BOLD
    )

    advice_label = ft.Text(
        "RECOMMENDATIONS",
        size=12,
        color=MUTED
    )

    guidance = ft.Text("", size=15)

    current_card = ft.Container(
        bgcolor=CARD_COLORS["green"][0],
        border_radius=20,
        padding=24,
        visible=False,
        content=ft.Column(
            controls=[
                hour,
                temperature,
                category,
                ft.Divider(),
                advice_label,
                guidance
            ],
            spacing=10
        )
    )

    #todays peak
    peak_text = ft.Text("", size=17, color=DARK)

    peak_card = ft.Container(
        bgcolor="#FFFFFF",
        border_radius=20,
        padding=22,
        visible=False,
        content=ft.Column(
            controls=[
                ft.Text(
                    "Today's peak",
                    size=19,
                    weight=ft.FontWeight.BOLD,
                    color=DARK
                ),
                peak_text
            ]
        )
    )

    source = ft.Text("", size=12, color=MUTED, visible=False)

    guideline_link = ft.TextButton(
        content="Regional heat guidelines",
        visible=False
    )

    weather_link = ft.TextButton(
        content="Open-Meteo",
        url="https://open-meteo.com/"
    )

    refresh_button = ft.Button(
        content="Refresh",
        icon=ft.Icons.REFRESH
    )

    busy = False

    async def refresh(_event=None):
        nonlocal busy

        if busy:
            return

        busy = True

        location.value = (
            f"{settings['name']}, {settings['state']} "
            f"· Sports region {settings['region']}"
        )

        loading.visible = True
        status.value = ""
        error.visible = False
        current_card.visible = False
        peak_card.visible = False
        source.visible = False
        guideline_link.visible = False
        refresh_button.disabled = True

        page.update()

        try:
            #fetch without freezing the app
            today = await asyncio.to_thread(
                fetch_today_summary,
                settings.copy()
            )

            level = today["category"]
            background, ink = CARD_COLORS[level]

            hour.value = (
                f"ESTIMATED WBGT · {today['current_time']:%I:%M %p}"
            )

            temperature.value = (
                f"{today['current_wbgt'] * 9 / 5 + 32:.1f} °F WBGT "
            )

            category.value = f"{level.title()} heat category"
            guidance.value = today["guidance"]

            current_card.bgcolor = background

            for item in (hour, temperature, category):
                item.color = ink

            guidance.color = (
                "#FFFFFF" if level == "black" else DARK
            )

            advice_label.color = (
                "#E2E8F0" if level == "black" else MUTED
            )

            current_card.visible = True

            #peak
            peak_text.value = (
                f"{today['peak_wbgt'] * 9 / 5 + 32:.1f} °F WBGT "
                f"at {today['peak_time']:%I:%M %p} "
                f"· {today['peak_category'].title()}"
            )

            peak_card.visible = True

            #sources
            source.value = (
                f"{today['weather_source']} · Liljegren estimate"
            )

            source.visible = True
            guideline_link.url = today["rule_source"]
            guideline_link.visible = True
            status.value = "Updated · times shown locally"

        except Exception as exc:
            error.value = f"Could not load forecast: {exc}"
            error.visible = True

        finally:
            busy = False
            loading.visible = False
            refresh_button.disabled = False

            page.update()

    refresh_button.on_click = refresh

    #home layout
    screen = ft.SafeArea(expand=True, content=ft.Column(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text(
                            "FirstHeat",
                            size=30,
                            color=DARK,
                            weight=ft.FontWeight.BOLD
                        ),
                        ft.Text(
                            "Adaptive heat-safety planner",
                            size=15,
                            color=MUTED
                        )
                    ],
                    spacing=0
                ),
                location,
                status,
                loading,
                error,
                current_card,
                peak_card,
                refresh_button,
                source,
                ft.Row(
                    controls=[
                        weather_link,
                        guideline_link
                    ],
                    wrap=True
                ),
                ft.Text(
                    "Estimated WBGT, not an on-site measurement. "
                    "WBGT combines temperature, humidity, sun and wind. It uses a different scale than air temperature or a weather app's 'feels like', so don't compare them. "
                    "Follow official guidance "
                    "(NATA/KSI, OSHA/NIOSH).",
                    size=12,
                    color=MUTED
                )
            ],
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
    )

    return screen, refresh
