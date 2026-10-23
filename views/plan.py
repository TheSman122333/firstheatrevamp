
"Plan: seven days of heat forecast, drawn like the Home chart"

import asyncio
from datetime import datetime

import flet as ft

from core.plan import fetch_week_plan
from views.brand import brand_header
from views.peak_chart import LINE_COLORS, ORDER, WINDOW_COLOR, build_peak_chart

#light background and readable text for each category
CHIP_COLORS = {
    "green": ("#E5F5E9", "#166534"),
    "yellow": ("#FFF4CC", "#795500"),
    "orange": ("#FFE4D2", "#9A3412"),
    "red": ("#FCE0E0", "#991B1B"),
    "black": ("#E2E8F0", "#0F172A")
}

DARK = "#172033"
MUTED = "#64748B"

EMPTY_SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"/>'


def time_label(when):
    return f"{when:%I %p}".lstrip("0")


def to_f(celsius):
    return celsius * 9 / 5 + 32


def card(content, padding=16):
    return ft.Container(
        bgcolor="#FFFFFF",
        border_radius=20,
        padding=padding,
        content=content
    )


def legend():
    "color key for the bars and charts"

    items = [
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
    ]

    items.append(
        ft.Row(
            controls=[
                ft.Container(
                    width=14,
                    height=10,
                    border_radius=2,
                    bgcolor=ft.Colors.with_opacity(0.16, WINDOW_COLOR),
                    border=ft.Border.all(1, WINDOW_COLOR)
                ),
                ft.Text("Lower-heat window", size=12, color=MUTED)
            ],
            spacing=4,
            tight=True
        )
    )

    return ft.Row(
        controls=items,
        spacing=12,
        run_spacing=6,
        wrap=True,
        alignment=ft.MainAxisAlignment.CENTER
    )


def week_glance(week):
    "one bar per day, height and color from the day's peak"

    peaks = [to_f(day["peak_wbgt"]) for day in week]
    low, high = min(peaks), max(peaks)
    span = max(high - low, 1)

    columns = []

    for index, (day, peak) in enumerate(zip(week, peaks)):
        level = day["peak_category"]

        columns.append(
            ft.Column(
                controls=[
                    ft.Text(
                        f"{peak:.0f}°",
                        size=13,
                        weight=ft.FontWeight.W_700,
                        color=CHIP_COLORS[level][1]
                    ),
                    ft.Container(
                        width=26,
                        height=28 + (peak - low) / span * 56,
                        bgcolor=LINE_COLORS[level],
                        border_radius=ft.BorderRadius.only(top_left=7, top_right=7),
                        tooltip=f"Peak {peak:.1f} °F WBGT · {level.title()}"
                    ),
                    ft.Text(
                        "Today" if index == 0 else f"{day['date']:%a}",
                        size=12,
                        weight=ft.FontWeight.W_600 if index == 0 else None,
                        color=DARK if index == 0 else MUTED,
                        no_wrap=True
                    ),
                    #green dot when the day has a lower-heat window
                    ft.Container(
                        width=6,
                        height=6,
                        border_radius=3,
                        bgcolor=WINDOW_COLOR if day["window"] else ft.Colors.TRANSPARENT
                    )
                ],
                spacing=4,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True
            )
        )

    return card(
        ft.Column(
            controls=[
                ft.Text(
                    "Week at a glance",
                    size=19,
                    weight=ft.FontWeight.BOLD,
                    color=DARK
                ),
                ft.Text(
                    "Daily peak estimated WBGT · green dot = lower-heat window",
                    size=12,
                    color=MUTED
                ),
                ft.Row(
                    controls=columns,
                    spacing=4,
                    vertical_alignment=ft.CrossAxisAlignment.END
                ),
                legend()
            ],
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH
        ),
        padding=ft.Padding.only(left=16, top=20, right=16, bottom=16)
    )


def day_card(page, day, is_today, now):
    "day name, peak chip, hourly chart and lower-heat window"

    peak_f = to_f(day["peak_wbgt"])
    level = day["peak_category"]
    window = day["window"]
    background, ink = CHIP_COLORS[level]

    chart = ft.Image(src=EMPTY_SVG, fit=ft.BoxFit.CONTAIN, height=100)
    chart_box = ft.Container(content=chart, size_change_interval=150)

    width = 320

    def draw():
        chart.src, chart.semantics_label = build_peak_chart(
            day["hourly"],
            day["thresholds_f"],
            now if is_today else None,
            width,
            window
        )

    #redraw the chart to fill the card width
    def resize(event):
        nonlocal width

        if abs(event.width - width) < 2:
            return

        width = event.width
        draw()
        page.update()

    chart_box.on_size_change = resize

    try:
        draw()
    except (KeyError, ValueError):
        chart_box.visible = False

    title = f"{day['date']:%a, %b %d}"

    if window:
        start, end = window
        window_row = ft.Row(
            controls=[
                ft.Icon(ft.Icons.SCHEDULE, size=18, color=WINDOW_COLOR),
                ft.Text(
                    f"Lower heat {time_label(start)}–{time_label(end)}",
                    size=14,
                    weight=ft.FontWeight.W_600,
                    color=WINDOW_COLOR
                )
            ],
            spacing=6
        )
    else:
        window_row = ft.Row(
            controls=[
                ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, size=18, color="#B91C1C"),
                ft.Text(
                    "No lower-heat daytime window",
                    size=14,
                    weight=ft.FontWeight.W_600,
                    color="#B91C1C"
                )
            ],
            spacing=6
        )

    return card(
        ft.Column(
            controls=[
                ft.Container(
                    padding=ft.Padding.only(left=8, right=8),
                    content=ft.Row(
                        controls=[
                            ft.Text(
                                f"Today · {title}" if is_today else title,
                                size=17,
                                weight=ft.FontWeight.BOLD,
                                color=DARK
                            ),
                            #peak value as a colored pill
                            ft.Container(
                                bgcolor=background,
                                border_radius=999,
                                padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                                content=ft.Text(
                                    f"Peak {peak_f:.1f}°F · {level.title()}",
                                    size=13,
                                    weight=ft.FontWeight.W_700,
                                    color=ink
                                )
                            )
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        wrap=True,
                        run_spacing=6
                    )
                ),
                chart_box,
                ft.Container(
                    padding=ft.Padding.only(left=8, right=8),
                    content=window_row
                )
            ],
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH
        ),
        padding=ft.Padding.only(left=8, top=16, right=8, bottom=14)
    )


def build_plan(page, settings):

    location = ft.Text("", color=MUTED)
    spinner = ft.ProgressRing(width=20, height=20, visible=False)
    status = ft.Text("", color=MUTED)

    rows = ft.Column(
        spacing=12,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH
    )

    refresh_button = ft.Button(
        content="Refresh plan",
        icon=ft.Icons.REFRESH
    )

    busy = False

    async def refresh(_event=None):
        nonlocal busy

        if busy:
            return

        busy = True
        spinner.visible = True
        refresh_button.disabled = True
        rows.controls.clear()
        status.value = "Loading seven-day forecast..."

        location.value = (
            f"{settings['name']}, {settings['state']} "
            f"· Region {settings['region']}"
        )

        page.update()

        try:
            #fetch and calculate outside the UI thread
            week = await asyncio.to_thread(
                fetch_week_plan,
                settings.copy()
            )

            now = datetime.now(week[0]["peak_time"].tzinfo)

            rows.controls.append(week_glance(week))

            for index, day in enumerate(week):
                rows.controls.append(
                    day_card(page, day, index == 0, now)
                )

            status.value = (
                "Hours shown in local time • "
                "lower heat = Green or Yellow"
            )

        except Exception as exc:
            rows.controls.clear()
            status.value = f"Could not load the plan: {exc}"

        finally:
            busy = False
            spinner.visible = False
            refresh_button.disabled = False
            page.update()

    refresh_button.on_click = refresh

    #plan layout
    screen = ft.SafeArea(expand=True, content=ft.Column(
            controls=[
                brand_header(),
                ft.Text(
                    "7-day training plan",
                    size=22,
                    weight=ft.FontWeight.BOLD,
                    color=DARK
                ),
                location,
                ft.Text(
                    "Lower-heat windows are 6 AM–8 PM hours below "
                    "Orange, not permission to exercise.",
                    size=13,
                    color=MUTED
                ),
                ft.Row([refresh_button, spinner]),
                status,
                rows,
                ft.Text(
                    "Estimated WBGT from Open-Meteo and Liljegren. "
                    "Follow official guidance and local rules. "
                    "Heat risk also depends on activity, clothing "
                    "and acclimatization.",
                    color=MUTED,
                    size=12
                )
            ],
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH
        )
    )

    return screen, refresh
