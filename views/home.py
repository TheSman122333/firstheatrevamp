#Homepage: a brief display of today

import asyncio
from datetime import datetime
from pathlib import Path

import flet as ft

from core.today import fetch_today_summary
from views.brand import brand_header
from views.peak_chart import LINE_COLORS, ORDER, build_peak_chart


#colors
CARD_COLORS = {
    "green": ("#E5F5E9", "#166534"),
    "yellow": ("#FFF4CC", "#795500"),
    "orange": ("#FFE4D2", "#9A3412"),
    "red": ("#FCE0E0", "#991B1B"),
    "black": ("#E2E8F0", "#0F172A")
}

#brighter category colors for the big WBGT number
SCORE_COLORS = {
    "green": "#15803D",
    "yellow": "#A16207",
    "orange": "#C2410C",
    "red": "#B91C1C",
    "black": "#0F172A"
}

#background activity art per category: file, accent color, description
ASSETS = Path(__file__).resolve().parent.parent / "assets"
ART_DIR = ASSETS / "activity"

ACTIVITY_ART = {
    "green": ("kids-jump-rope.svg", "#16A34A", "Kids playing jump rope outside"),
    "yellow": ("runner-water.svg", "#CA8A04", "Runner holding a cup of water"),
    "orange": ("bike-ride.svg", "#EA580C", "Person riding a bike"),
    "red": ("shade-break.svg", "#DC2626", "Person resting in the shade"),
    "black": ("indoor-bike.svg", "#B91C1C", "Person exercising indoors on a bike")
}

#categories that show the emergency shortcut
DANGER = ("orange", "red", "black")

MUTED = "#64748B"
DARK = "#172033"


def activity_art(level):
    #tint the illustration with the category color
    name, accent, label = ACTIVITY_ART[level]
    svg = (ART_DIR / name).read_text(encoding="utf-8")

    return svg.replace("currentColor", accent).encode(), label


def build_home(page, settings, on_emergency, simulator=()):

    emergency_button = ft.Button(
        content="Emergency help — CALL 911 instructions",
        icon=ft.Icons.WARNING,
        color="#FFFFFF",
        bgcolor="#B91C1C",
        height=54,
        visible=False,
        on_click=on_emergency
    )

    status = ft.Text("", color=MUTED)

    loading = ft.Row(
        controls=[
            ft.ProgressRing(width=20, height=20),
            ft.Text("Loading forecast...")
        ]
    )

    error = ft.Text("", color="#991B1B", visible=False)

    #current WBGT, as bold as possible
    temperature = ft.Text(
        "--°F",
        size=72,
        weight=ft.FontWeight.W_900,
        style=ft.TextStyle(height=1.05),
        text_align=ft.TextAlign.CENTER
    )

    #when the number was last calculated
    calculated = ft.Text(
        "",
        size=16,
        weight=ft.FontWeight.W_600,
        text_align=ft.TextAlign.CENTER
    )

    advice_label = ft.Text(
        "RECOMMENDATIONS",
        size=12,
        color=MUTED
    )

    guidance = ft.Text("", size=15, color=DARK)

    #activity picture with the score on top
    art_svg, art_label = activity_art("green")

    #width cap keeps the picture phone-sized on wide screens
    art = ft.Image(
        src=art_svg,
        fit=ft.BoxFit.CONTAIN,
        width=360,
        semantics_label=art_label
    )

    #frosted panel keeps the score readable over the picture
    glass = ft.Container(
        left=14,
        right=14,
        top=14,
        padding=ft.Padding.only(left=8, top=10, right=8, bottom=10),
        border_radius=18,
        blur=ft.Blur(10, 10),
        content=ft.Column(
            controls=[
                temperature,
                calculated
            ],
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH
        )
    )

    def fit_number(event):
        #shrink the number on narrow screens so it stays on one line
        size = round(max(40, min(80, (event.width - 44) / 4.2)))

        if size != temperature.size:
            temperature.size = size
            page.update()

    hero = ft.Stack(
        height=400,
        size_change_interval=100,
        on_size_change=fit_number,
        controls=[
            ft.Container(
                left=12,
                right=12,
                top=150,
                bottom=8,
                alignment=ft.Alignment.BOTTOM_CENTER,
                content=art
            ),
            glass
        ]
    )

    current_card = ft.Container(
        bgcolor=CARD_COLORS["green"][0],
        border_radius=20,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        visible=False,
        content=ft.Column(
            controls=[
                hero,
                ft.Container(
                    padding=ft.Padding.only(left=24, right=24, bottom=24),
                    content=ft.Column(
                        controls=[
                            ft.Divider(),
                            advice_label,
                            guidance
                        ],
                        spacing=10
                    )
                )
            ],
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH
        )
    )

    #todays peak
    peak_text = ft.Text("", size=17, color=DARK)

    #hourly curve, 6 AM to 10 PM, redrawn to fill the card width
    peak_chart = ft.Image(
        src=b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"/>',
        fit=ft.BoxFit.CONTAIN,
        height=100
    )

    chart_box = ft.Container(
        content=peak_chart,
        visible=False,
        size_change_interval=150
    )

    chart_width = 320
    chart_data = None

    def draw_chart():
        peak_chart.src, peak_chart.semantics_label = build_peak_chart(
            *chart_data, width=chart_width
        )

    def resize_chart(event):
        nonlocal chart_width

        if abs(event.width - chart_width) < 2:
            return

        chart_width = event.width

        if chart_data is not None:
            draw_chart()
            page.update()

    chart_box.on_size_change = resize_chart

    #color key for the chart bands
    legend = ft.Row(
        controls=[
            ft.Row(
                controls=[
                    ft.Container(
                        width=10,
                        height=10,
                        border_radius=5,
                        bgcolor=LINE_COLORS[name]
                    ),
                    ft.Text(name.title(), size=12, color=MUTED)
                ],
                spacing=4,
                tight=True
            )
            for name in ORDER
        ],
        spacing=12,
        wrap=True,
        alignment=ft.MainAxisAlignment.CENTER,
        visible=False
    )

    peak_card = ft.Container(
        bgcolor="#FFFFFF",
        border_radius=20,
        padding=ft.Padding.only(left=8, top=22, right=8, bottom=16),
        visible=False,
        content=ft.Column(
            controls=[
                ft.Container(
                    padding=ft.Padding.only(left=14, right=14),
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
                ),
                chart_box,
                legend
            ],
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH
        )
    )

    #simulate a session, right under the chart
    simulator_card = ft.Container(
        bgcolor="#FFFFFF",
        border_radius=20,
        padding=22,
        visible=bool(simulator),
        content=ft.Column(
            controls=list(simulator),
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH
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
        nonlocal busy, chart_data

        if busy:
            return

        busy = True

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
            now = datetime.now(today["current_time"].tzinfo)
            wbgt_f = today["current_wbgt"] * 9 / 5 + 32

            temperature.value = f"{wbgt_f:.1f}°F"
            temperature.color = SCORE_COLORS[level]

            #screen readers still hear that it is an estimate and its category
            temperature.semantics_label = (
                f"Estimated WBGT {wbgt_f:.1f} degrees Fahrenheit, "
                f"{level} heat category"
            )

            calculated.value = f"WBGT @ {now:%I:%M %p}".replace("@ 0", "@ ")
            calculated.color = ink

            guidance.value = today["guidance"]

            current_card.bgcolor = background

            art.src, art.semantics_label = activity_art(level)

            glass.bgcolor = ft.Colors.with_opacity(0.72, background)
            glass.border = ft.Border.all(
                1, ft.Colors.with_opacity(0.6, "#FFFFFF")
            )

            current_card.visible = True

            #emergency shortcut only for dangerous heat
            emergency_button.visible = level in DANGER

            #peak
            peak_text.value = (
                f"{today['peak_wbgt'] * 9 / 5 + 32:.1f} °F WBGT "
                f"at {today['peak_time']:%I:%M %p} "
                f"· {today['peak_category'].title()}"
            )

            try:
                chart_data = (today["hourly"], today["thresholds_f"], now)
                draw_chart()
                chart_box.visible = True

            except (KeyError, ValueError):
                chart_data = None
                chart_box.visible = False

            legend.visible = chart_box.visible

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

            #conditions unknown, so keep the shortcut
            emergency_button.visible = True

        finally:
            busy = False
            loading.visible = False
            refresh_button.disabled = False

            page.update()

    refresh_button.on_click = refresh

    #home layout
    screen = ft.SafeArea(expand=True, content=ft.Column(
            controls=[
                brand_header(),
                emergency_button,
                status,
                loading,
                error,
                current_card,
                peak_card,
                simulator_card,
                ft.Row(controls=[refresh_button]),
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
            expand=True,
            #same width for every tile
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH
        )
    )

    return screen, refresh
