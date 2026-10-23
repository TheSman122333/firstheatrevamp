#Homepage: a brief display of today

import asyncio
import re
from datetime import datetime
from pathlib import Path

import flet as ft

from core.conditions import fetch_conditions
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

#text colors for UV index and air quality levels
LEVEL_COLORS = {
    "low": "#15803D",
    "good": "#15803D",
    "moderate": "#A16207",
    "high": "#C2410C",
    "sensitive": "#C2410C",
    "very_high": "#B91C1C",
    "unhealthy": "#B91C1C",
    "extreme": "#7E22CE",
    "very_unhealthy": "#7E22CE",
    "hazardous": "#7F1D1D"
}

#short labels that fit a small tile
SHORT_LABELS = {"sensitive": "Sensitive groups", "very_unhealthy": "Very unhealthy"}

#tallest the activity picture gets, and its widest
ART_HEIGHT = 242
ART_WIDTH = 360

#conditions tiles: four across when each gets at least this much room
TILE_MIN_WIDTH = 120
TILE_GAP = 8

#on-site meter readings count for this long, and must look like real WBGT
READING_MINUTES = 60
READING_MIN_F, READING_MAX_F = 32, 120


def activity_art(level):
    #tint the illustration with the category color
    name, accent, label = ACTIVITY_ART[level]
    svg = (ART_DIR / name).read_text(encoding="utf-8")

    #width / height from the viewBox, to size the space for it
    _, _, width, height = map(float, re.search(r'viewBox="([^"]+)"', svg).group(1).split())

    return svg.replace("currentColor", accent).encode(), label, width / height


def condition_tile(icon, icon_color, name):
    "small tile: icon, value, what it is, and a short note"

    symbol = ft.Icon(icon, size=18, color=icon_color)
    value = ft.Text("--", size=17, weight=ft.FontWeight.W_800, color=DARK, no_wrap=True)
    note = ft.Text("", size=11, weight=ft.FontWeight.W_600, color=MUTED)

    tile = ft.Container(
        width=140,
        bgcolor=ft.Colors.with_opacity(0.6, "#FFFFFF"),
        border_radius=12,
        padding=ft.Padding.only(left=10, top=8, right=8, bottom=8),
        content=ft.Row(
            controls=[
                symbol,
                ft.Column(
                    controls=[
                        value,
                        ft.Text(name, size=11, color=MUTED, no_wrap=True),
                        note
                    ],
                    spacing=0,
                    tight=True,
                    expand=True
                )
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.START
        )
    )

    return tile, symbol, value, note


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

    loading = ft.Row(
        controls=[
            ft.ProgressRing(width=20, height=20),
            ft.Text("Loading forecast...")
        ]
    )

    error = ft.Text("", color="#991B1B", expand=True)

    #the refresh icon lives in the score panel, so offer a retry here
    retry_button = ft.TextButton(content="Try again", icon=ft.Icons.REFRESH)

    error_row = ft.Row(
        controls=[error, retry_button],
        spacing=8,
        visible=False
    )

    #chosen city, top left of the score panel
    city_icon = ft.Icon(ft.Icons.PLACE_OUTLINED, size=16, color=DARK)
    city = ft.Text(
        "",
        size=14,
        color=DARK,
        no_wrap=True,
        overflow=ft.TextOverflow.ELLIPSIS,
        expand=True
    )

    refresh_button = ft.IconButton(
        icon=ft.Icons.REFRESH,
        icon_size=18,
        icon_color=DARK,
        tooltip="Refresh",
        visual_density=ft.VisualDensity.COMPACT
    )

    #current WBGT, as bold as possible
    temperature = ft.Text(
        "--°F",
        size=72,
        weight=ft.FontWeight.W_900,
        style=ft.TextStyle(height=1.05),
        text_align=ft.TextAlign.CENTER
    )

    #what the number is, when it was calculated, and the city's time zone
    calculated = ft.Text(
        "",
        size=15,
        color=DARK,
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
    art_svg, art_label, art_ratio = activity_art("green")

    #width cap keeps the picture phone-sized on wide screens
    art = ft.Image(
        src=art_svg,
        fit=ft.BoxFit.CONTAIN,
        width=ART_WIDTH,
        semantics_label=art_label
    )

    #current conditions under the score
    air_tile, _, air_value, air_note = condition_tile(ft.Icons.THERMOSTAT, "#EA580C", "Air temp")
    humidity_tile, _, humidity_value, humidity_note = condition_tile(
        ft.Icons.WATER_DROP_OUTLINED, "#0284C7", "Humidity"
    )
    uv_tile, uv_icon, uv_value, uv_note = condition_tile(ft.Icons.WB_SUNNY_OUTLINED, MUTED, "UV index")
    aqi_tile, aqi_icon, aqi_value, aqi_note = condition_tile(ft.Icons.AIR, MUTED, "Air quality")

    tiles = [air_tile, humidity_tile, uv_tile, aqi_tile]

    conditions = ft.Container(
        margin=ft.Margin.only(top=10),
        visible=False,
        content=ft.Row(
            controls=tiles,
            spacing=TILE_GAP,
            run_spacing=TILE_GAP,
            wrap=True,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.START
        )
    )

    #frosted panel keeps the score readable over the picture
    glass = ft.Container(
        margin=ft.Margin.only(left=14, top=14, right=14),
        padding=ft.Padding.only(left=8, top=10, right=8, bottom=10),
        border_radius=18,
        blur=ft.Blur(10, 10),
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[city_icon, city, refresh_button],
                    spacing=4,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                ),
                temperature,
                calculated,
                conditions
            ],
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH
        )
    )

    #the picture sits under the panel, and the space for it matches its height
    art_box = ft.Container(
        left=12,
        right=12,
        bottom=8,
        height=ART_HEIGHT,
        alignment=ft.Alignment.BOTTOM_CENTER,
        content=art
    )

    art_space = ft.Container(height=ART_HEIGHT + 24)
    hero_width = None

    def size_art():
        if hero_width is None:
            return

        drawn = round(min(ART_HEIGHT, min(hero_width - 24, ART_WIDTH) / art_ratio))
        art_box.height = drawn
        art_space.height = drawn + 24

    def fit_number(event):
        nonlocal hero_width

        hero_width = event.width

        #shrink the number on narrow screens so it stays on one line
        temperature.size = round(max(40, min(80, (event.width - 44) / 4.2)))

        #tiles: four across on wide screens, two by two on phones
        #(room inside the panel's margins, padding and border)
        room = event.width - 28 - 16 - 2 - 1
        columns = 4 if room >= 4 * TILE_MIN_WIDTH + 3 * TILE_GAP else 2
        width = int((room - (columns - 1) * TILE_GAP) / columns)

        for tile in tiles:
            tile.width = width

        size_art()
        page.update()

    #the panel sets the height, and the picture fills the space under it
    hero = ft.Stack(
        size_change_interval=100,
        on_size_change=fit_number,
        controls=[
            art_box,
            ft.Column(
                controls=[glass, art_space],
                spacing=0,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH
            )
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
                "of the estimate. It also adjusts today's chart, and applies for "
                f"{READING_MINUTES} minutes.",
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

    #shown while an on-site reading recolors the chart
    adjust_text = ft.Text("", size=13, color="#166534", expand=True)

    adjust_note = ft.Row(
        controls=[ft.Icon(ft.Icons.TUNE, size=16, color="#166534"), adjust_text],
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.START,
        visible=False
    )

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
                                "Today's WBGT index",
                                size=19,
                                weight=ft.FontWeight.BOLD,
                                color=DARK
                            ),
                            peak_text,
                            adjust_note
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

    busy = False

    #air temperature, humidity, UV and air quality tiles
    def show_conditions(now):
        conditions.visible = now is not None

        if now is None:
            return

        air_value.value = "--" if now["temperature_f"] is None else f"{now['temperature_f']:.0f}°F"
        air_note.value = "" if now["high_f"] is None else f"High {now['high_f']:.0f}°"

        humidity_value.value = "--" if now["humidity"] is None else f"{now['humidity']:.0f}%"
        humidity_note.value = "" if now["dew_point_f"] is None else f"Dew pt {now['dew_point_f']:.0f}°"

        if now["uv_index"] is None:
            uv_value.value, uv_note.value = "--", "Unavailable"
            uv_value.color = uv_note.color = uv_icon.color = MUTED
        else:
            color = LEVEL_COLORS[now["uv_level"]]
            uv_value.value = f"{int(now['uv_index'] + 0.5)}"
            uv_note.value = now["uv_label"]
            uv_value.color = uv_note.color = uv_icon.color = color

        if now["aqi"] is None:
            aqi_value.value, aqi_note.value = "--", "Unavailable"
            aqi_value.color = aqi_note.color = aqi_icon.color = MUTED
            aqi_tile.tooltip = None
        else:
            color = LEVEL_COLORS[now["aqi_level"]]
            aqi_value.value = f"{int(now['aqi'] + 0.5)}"
            aqi_note.value = SHORT_LABELS.get(now["aqi_level"], now["aqi_label"])
            aqi_value.color = aqi_note.color = aqi_icon.color = color
            aqi_tile.tooltip = f"US AQI {int(now['aqi'] + 0.5)}: {now['aqi_label']}" + (
                f" · PM2.5 {now['pm2_5']:.0f} µg/m³" if now["pm2_5"] is not None else ""
            )

    async def load_conditions():
        try:
            return await asyncio.to_thread(fetch_conditions, settings.copy())
        except Exception:
            return None

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

    #peak and chart; an on-site reading shifts every hour by its difference
    def show_peak(offset_f):
        nonlocal chart_data

        rule_set = f"sports_{last_today['region']}"
        measured = reading is not None

        def level_at(wbgt_f):
            return get_category(wbgt_f, rule_set, unit="F")["category"]

        peak_f = last_today["peak_wbgt"] * 9 / 5 + 32 + offset_f

        #flagged when it sits just under the next category; estimates only
        upper = None if measured else next_category_if_close(peak_f, rule_set, unit="F")

        peak_text.value = (
            f"{peak_f:.1f} °F WBGT at {last_today['peak_time']:%I:%M %p} "
            f"· {level_at(peak_f).title()}"
            + (f" · could be {upper.title()}" if upper else "")
        )

        adjust_note.visible = measured

        if measured:
            adjust_text.value = (
                f"Adjusted {offset_f:+.1f}°F to match your on-site reading "
                f"from {time_text(reading['at'])}."
            )

            hourly = [
                {
                    **item,
                    "wbgt": item["wbgt"] + offset_f * 5 / 9,
                    "category": level_at(item["wbgt"] * 9 / 5 + 32 + offset_f)
                }
                for item in last_today["hourly"]
            ]
        else:
            hourly = last_today["hourly"]

        try:
            chart_data = (
                hourly,
                last_today["thresholds_f"],
                datetime.now(calculated_at.tzinfo)
            )
            draw_chart()
            chart_box.visible = True

        except (KeyError, ValueError):
            chart_data = None
            chart_box.visible = False

        legend.visible = chart_box.visible

    #score tile, guidance and alerts from the reading or the estimate
    def show_current():
        nonlocal art_ratio

        region = last_today["region"]
        measured = reading is not None

        estimate_f = last_today["current_wbgt"] * 9 / 5 + 32

        #time and the city's zone (EST/EDT, CST/CDT, PST/PDT) stay on one line
        def stamp(when):
            return "\u00a0".join(["@", *time_text(when).split(), *([when.tzname()] if when.tzname() else [])])

        if measured:
            wbgt_f = reading["value_f"]
            label = f"On-site reading {stamp(reading['at'])}"
        else:
            wbgt_f = estimate_f
            label = f"Heat stress (WBGT) {stamp(calculated_at)}"

        info = get_category(wbgt_f, f"sports_{region}", unit="F")
        level = info["category"]
        background = CARD_COLORS[level][0]

        temperature.value = f"{wbgt_f:.1f}°F"
        temperature.color = SCORE_COLORS[level]

        #screen readers hear whether it is measured or estimated
        temperature.semantics_label = (
            f"{'Measured' if measured else 'Estimated'} heat stress, WBGT {wbgt_f:.1f} "
            f"degrees Fahrenheit, {level} heat category"
        )

        calculated.value = label
        city.value = ", ".join(part for part in (settings["name"], settings["state"]) if part)

        guidance.value = info["guidance"]
        current_card.bgcolor = background
        art.src, art.semantics_label, art_ratio = activity_art(level)
        size_art()

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

        show_peak(wbgt_f - estimate_f)

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
        nonlocal busy, last_today, calculated_at, reading

        if busy:
            return

        busy = True

        loading.visible = True
        error_row.visible = False
        current_card.visible = False
        reading_card.visible = False
        peak_card.visible = False
        source.visible = False
        refresh_button.disabled = True

        page.update()

        try:
            #fetch without freezing the app; conditions are optional
            today, now_conditions = await asyncio.gather(
                asyncio.to_thread(fetch_today_summary, settings.copy()),
                load_conditions()
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
            show_conditions(now_conditions)
            current_card.visible = True
            reading_card.visible = True
            peak_card.visible = True

            #sources
            source.value = (
                f"{today['weather_source']} · Liljegren estimate"
                + (" · Air quality: CAMS via Open-Meteo"
                   if now_conditions and now_conditions["aqi"] is not None else "")
            )

            source.visible = True

        except Exception as exc:
            error.value = f"Could not load forecast: {exc}"
            error_row.visible = True

            #conditions unknown, so keep the shortcut
            emergency_button.visible = True

        finally:
            busy = False
            loading.visible = False
            refresh_button.disabled = False

            page.update()

    refresh_button.on_click = refresh
    retry_button.on_click = refresh

    #home layout
    screen = ft.SafeArea(expand=True, content=ft.Column(
            controls=[
                brand_header(),
                emergency_button,
                loading,
                error_row,
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
