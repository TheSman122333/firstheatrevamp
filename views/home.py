#Homepage: a brief display of today

import asyncio
from datetime import datetime
from pathlib import Path

import flet as ft

from core.rules import get_category, next_category_if_close
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

#on-site meter readings count for this long, and must look like real WBGT
READING_MINUTES = 60
READING_MIN_F, READING_MAX_F = 32, 120


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

    #estimate is close to the next category
    near_text = ft.Text("", size=14, color="#9A3412", expand=True)

    near_banner = ft.Container(
        bgcolor="#FFF7ED",
        border=ft.Border.all(1, "#FDBA74"),
        border_radius=12,
        padding=ft.Padding.symmetric(horizontal=12, vertical=10),
        visible=False,
        content=ft.Row(
            controls=[ft.Icon(ft.Icons.TRENDING_UP, size=20, color="#C2410C"), near_text],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.START
        )
    )

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
                            near_banner,
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

    #on-site WBGT meter reading that overrides the estimate
    reading_field = ft.TextField(
        label="WBGT °F",
        hint_text="e.g. 84.5",
        keyboard_type=ft.KeyboardType.NUMBER,
        input_filter=ft.InputFilter(regex_string=r"[0-9.]", allow=True),
        width=150,
        dense=True
    )

    reading_message = ft.Text("", size=12, visible=False)

    use_button = ft.FilledButton(
        content="Use reading",
        icon=ft.Icons.THERMOSTAT,
        style=ft.ButtonStyle(bgcolor="#EA580C", color="#FFFFFF")
    )

    reading_input = ft.Column(
        controls=[
            ft.Text(
                "Have a WBGT meter? Enter an on-site reading to use it instead "
                f"of the estimate. It applies for {READING_MINUTES} minutes.",
                size=13,
                color=MUTED
            ),
            ft.Row(
                controls=[reading_field, use_button],
                spacing=10,
                run_spacing=8,
                wrap=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            )
        ],
        spacing=10
    )

    reading_status = ft.Text("", size=14, color="#166534", expand=True)

    clear_button = ft.TextButton(content="Clear", icon=ft.Icons.CLOSE)

    reading_active = ft.Row(
        controls=[
            ft.Icon(ft.Icons.CHECK_CIRCLE, size=20, color="#166534"),
            reading_status,
            clear_button
        ],
        spacing=8,
        visible=False
    )

    reading_card = ft.Container(
        bgcolor="#FFFFFF",
        border_radius=20,
        padding=ft.Padding.only(left=22, top=18, right=22, bottom=18),
        visible=False,
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.THERMOSTAT, size=22, color="#EA580C"),
                        ft.Text("On-site reading", size=19, weight=ft.FontWeight.BOLD, color=DARK)
                    ],
                    spacing=8
                ),
                reading_input,
                reading_active,
                reading_message
            ],
            spacing=10
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

    #small refresh icon beside the update time
    refresh_button = ft.IconButton(
        icon=ft.Icons.REFRESH,
        icon_size=20,
        icon_color=MUTED,
        tooltip="Refresh"
    )

    busy = False

    #latest forecast summary, when it was calculated, and any meter reading
    last_today = None
    calculated_at = None
    reading = None

    def time_text(when):
        return f"{when:%I:%M %p}".lstrip("0")

    def show_message(text, color=MUTED):
        reading_message.value = text
        reading_message.color = color
        reading_message.visible = bool(text)

    #score tile, guidance and alerts from the reading or the estimate
    def show_current():
        region = last_today["region"]
        measured = reading is not None

        if measured:
            wbgt_f = reading["value_f"]
            label = f"On-site reading @ {time_text(reading['at'])}"
        else:
            wbgt_f = last_today["current_wbgt"] * 9 / 5 + 32
            label = f"WBGT @ {time_text(calculated_at)}"

        info = get_category(wbgt_f, f"sports_{region}", unit="F")
        level = info["category"]
        background, ink = CARD_COLORS[level]

        temperature.value = f"{wbgt_f:.1f}°F"
        temperature.color = SCORE_COLORS[level]

        #screen readers hear whether it is measured or estimated
        temperature.semantics_label = (
            f"{'Measured' if measured else 'Estimated'} WBGT {wbgt_f:.1f} "
            f"degrees Fahrenheit, {level} heat category"
        )

        calculated.value = label
        calculated.color = ink

        guidance.value = info["guidance"]
        current_card.bgcolor = background
        art.src, art.semantics_label = activity_art(level)

        glass.bgcolor = ft.Colors.with_opacity(0.72, background)
        glass.border = ft.Border.all(
            1, ft.Colors.with_opacity(0.6, "#FFFFFF")
        )

        #only estimates get the could-be-higher flag
        upper = None if measured else next_category_if_close(
            wbgt_f, f"sports_{region}", unit="F"
        )

        near_banner.visible = upper is not None

        if upper:
            near_text.value = (
                f"Could be higher: this estimate is within about 1°F of "
                f"{upper.title()}. Estimates can be off, so consider "
                f"{upper.title()} precautions."
            )

        #emergency shortcut only for dangerous heat
        emergency_button.visible = level in DANGER

        reading_input.visible = not measured
        reading_active.visible = measured

        if measured:
            reading_status.value = (
                f"Using your reading of {wbgt_f:.1f}°F from "
                f"{time_text(reading['at'])} instead of the estimate."
            )

    async def apply_reading(_event=None):
        nonlocal reading

        if last_today is None:
            return

        text = (reading_field.value or "").strip()

        try:
            value = float(text)

            if not READING_MIN_F <= value <= READING_MAX_F:
                raise ValueError()

        except ValueError:
            show_message(
                f"Enter a WBGT between {READING_MIN_F} and {READING_MAX_F} °F.",
                "#991B1B"
            )
            page.update()
            return

        reading = {
            "value_f": value,
            "at": datetime.now(last_today["current_time"].tzinfo)
        }

        reading_field.value = ""
        show_message("")
        show_current()
        page.update()

    def clear_reading(_event=None):
        nonlocal reading

        reading = None
        show_message("Back to the estimate.")
        show_current()
        page.update()

    use_button.on_click = apply_reading
    reading_field.on_submit = apply_reading
    clear_button.on_click = clear_reading

    async def refresh(_event=None):
        nonlocal busy, chart_data, last_today, calculated_at, reading

        if busy:
            return

        busy = True

        loading.visible = True
        status.value = ""
        error.visible = False
        current_card.visible = False
        reading_card.visible = False
        peak_card.visible = False
        source.visible = False
        refresh_button.disabled = True

        page.update()

        try:
            #fetch without freezing the app
            today = await asyncio.to_thread(
                fetch_today_summary,
                settings.copy()
            )

            now = datetime.now(today["current_time"].tzinfo)
            last_today, calculated_at = today, now

            show_message("")

            #meter readings go stale
            if reading and (now - reading["at"]).total_seconds() > READING_MINUTES * 60:
                reading = None
                show_message(
                    f"Your on-site reading is over {READING_MINUTES} minutes old, "
                    "so the estimate is back. Enter a new reading if you have one."
                )

            show_current()
            current_card.visible = True
            reading_card.visible = True

            #peak, flagged when it sits just under the next category
            upper = next_category_if_close(
                today["peak_wbgt"], f"sports_{today['region']}"
            )

            peak_text.value = (
                f"{today['peak_wbgt'] * 9 / 5 + 32:.1f} °F WBGT "
                f"at {today['peak_time']:%I:%M %p} "
                f"· {today['peak_category'].title()}"
                + (f" · could be {upper.title()}" if upper else "")
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
            #zone of the chosen city, e.g. EST/EDT, CST/CDT, PST/PDT
            status.value = f"Times shown in {now.tzname() or 'local time'}"

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
                ft.Row(
                    controls=[status, refresh_button],
                    spacing=0,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                ),
                loading,
                error,
                current_card,
                reading_card,
                peak_card,
                simulator_card,
                source,
                ft.Text(
                    "Estimated WBGT, not an on-site measurement, unless you "
                    "enter your own meter reading. "
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
