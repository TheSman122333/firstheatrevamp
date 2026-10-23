
"Simulate a session with sliders. Never changes real forecasts or attendance"
"ASSISTED BY AI"

from datetime import date

import flet as ft

from core.acclim import Person, worker_plan, athlete_plan
from core.rules import get_category, load_rules
from views.peak_chart import LINE_COLORS, ORDER
from views.sliders import side_gradient, slider_block

DARK = "#172033"
MUTED = "#64748B"

#readable text colors for each WBGT category
TEXT_COLORS = {
    "green": "#15803D",
    "yellow": "#A16207",
    "orange": "#C2410C",
    "red": "#B91C1C",
    "black": "#0F172A"
}

WBGT_MIN, WBGT_MAX = 60, 100

REGIONS = [(1, "Cooler"), (2, "Moderate"), (3, "Warmer")]
REGION_COLORS = ["#60A5FA", "#FBBF24", "#F97316"]

ROLES = [("athlete", "Athlete"), ("worker", "Worker")]

#OSHA/NIOSH workload levels
INTENSITY = [
    ("light", "Light"),
    ("moderate", "Moderate"),
    ("heavy", "Heavy"),
    ("very_heavy", "Very heavy")
]
INTENSITY_COLORS = ["#16A34A", "#EAB308", "#EA580C", "#DC2626"]

def wbgt_gradient(region):
    "hard color bands at the region's category cutoffs"

    minimums = load_rules()["sports"]["regions"][str(region)]["minimums"]
    edges = [WBGT_MIN] + [minimums[name] for name in ORDER[1:]] + [WBGT_MAX]

    colors, stops = [], []

    for index, name in enumerate(ORDER):
        start = (edges[index] - WBGT_MIN) / (WBGT_MAX - WBGT_MIN)
        end = (edges[index + 1] - WBGT_MIN) / (WBGT_MAX - WBGT_MIN)

        colors += [LINE_COLORS[name]] * 2
        stops += [start, end]

    return side_gradient(colors, stops)


#light tile background for each WBGT category
TILE_COLORS = {
    "green": "#E5F5E9",
    "yellow": "#FFF4CC",
    "orange": "#FFE4D2",
    "red": "#FCE0E0",
    "black": "#E2E8F0"
}

#short headline for each sports guidance level
HEADLINES = {
    "green": "Normal activity with breaks",
    "yellow": "Add more breaks",
    "orange": "Shorten practice, more breaks",
    "red": "One hour at most",
    "black": "No outdoor training"
}

#athletes can be allowed up to 300 practice minutes in a day
ATHLETE_MAX_MINUTES = 300

#half the marker width, so the marker tip lines up with the bar ends
MARKER_HALF = 13


def pill(text, background, color, icon=None):
    controls = [ft.Text(text, size=12, weight=ft.FontWeight.W_600, color=color)]

    if icon:
        controls.insert(0, ft.Icon(icon, size=14, color=color))

    return ft.Container(
        bgcolor=background,
        border_radius=999,
        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
        content=ft.Row(controls=controls, spacing=4, tight=True)
    )


def status_pill(text, ok):
    if ok:
        return pill(text, "#DCFCE7", "#166534", ft.Icons.CHECK_CIRCLE)

    return pill(text, "#FEE2E2", "#991B1B", ft.Icons.WARNING_AMBER_ROUNDED)


def section(icon, title, controls):
    "small titled block inside the result"

    return ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.Icon(icon, size=18, color=MUTED),
                    ft.Text(title, size=13, weight=ft.FontWeight.W_600, color=MUTED)
                ],
                spacing=6
            )
        ] + controls,
        spacing=6,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH
    )


def heat_scale(value, region):
    "region's color bands with a marker at the simulated WBGT"

    share = (min(max(value, WBGT_MIN), WBGT_MAX) - WBGT_MIN) / (WBGT_MAX - WBGT_MIN)
    before = max(1, round(share * 1000))
    after = max(1, 1000 - before)

    return ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.Container(expand=before),
                    ft.Icon(ft.Icons.ARROW_DROP_DOWN, size=MARKER_HALF * 2, color=DARK),
                    ft.Container(expand=after)
                ],
                spacing=0
            ),
            ft.Container(
                height=12,
                border_radius=6,
                margin=ft.Margin.symmetric(horizontal=MARKER_HALF),
                gradient=wbgt_gradient(region)
            ),
            ft.Container(
                padding=ft.Padding.symmetric(horizontal=MARKER_HALF - 6),
                content=ft.Row(
                    controls=[
                        ft.Text(tick, size=11, color=MUTED)
                        for tick in ("60°", "70°", "80°", "90°", "100°")
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                )
            )
        ],
        spacing=0,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH
    )


def time_bar(share, color):
    return ft.ProgressBar(
        value=min(max(share, 0), 1),
        bar_height=10,
        color=color,
        bgcolor="#E2E8F0",
        border_radius=5
    )


def build_developer_mode(page, settings, profile):

    #hidden until enabled
    enabled = ft.Switch(value=False)

    header = ft.Row(
        controls=[
            ft.Text(
                "Simulate a Session",
                size=19,
                weight=ft.FontWeight.BOLD,
                color=DARK
            ),
            enabled
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
    )

    wbgt = ft.Slider(min=WBGT_MIN, max=WBGT_MAX, divisions=WBGT_MAX - WBGT_MIN, value=95)
    region = ft.Slider(min=1, max=3, divisions=2, value=settings["region"])
    role = ft.Slider(min=0, max=1, divisions=1, value=0)
    intensity = ft.Slider(min=0, max=3, divisions=3, value=1)

    wbgt_block, wbgt_value, wbgt_bar = slider_block(
        "SIMULATED WBGT",
        wbgt,
        ["60°", "70°", "80°", "90°", "100°"],
        wbgt_gradient(settings["region"])
    )

    region_block, region_value, _ = slider_block(
        "SIMULATED region",
        region,
        [f"{number} {name}" for number, name in REGIONS],
        side_gradient(REGION_COLORS)
    )

    role_block, role_value, _ = slider_block(
        "SIMULATED role",
        role,
        [name for _, name in ROLES]
    )

    intensity_block, intensity_value, _ = slider_block(
        "SIMULATED intensity",
        intensity,
        [name for _, name in INTENSITY],
        side_gradient(INTENSITY_COLORS)
    )

    #simulation report, filled in by calculate()
    result = ft.Column(
        controls=[
            ft.Text(
                "Move a slider or tap Run simulation to see the result.",
                size=13,
                color=MUTED
            )
        ],
        spacing=14,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH
    )

    result_box = ft.Container(
        border=ft.Border.all(1, "#E2E8F0"),
        border_radius=16,
        padding=14,
        content=result
    )

    def chosen():
        region_number = int(round(region.value))
        role_key = ROLES[int(round(role.value))][0]
        workload, intensity_label = INTENSITY[int(round(intensity.value))]

        return float(wbgt.value), region_number, role_key, workload, intensity_label

    #show what each slider is set to
    def show_values():
        value, region_number, role_key, _, intensity_label = chosen()
        category = get_category(value, f"sports_{region_number}", unit="F")["category"]

        wbgt_value.value = f"{value:.0f} °F · {category.title()}"
        wbgt_value.color = TEXT_COLORS[category]
        wbgt_bar.gradient = wbgt_gradient(region_number)

        region_value.value = f"Region {region_number} · {REGIONS[region_number - 1][1]}"
        role_value.value = dict(ROLES)[role_key]
        intensity_value.value = intensity_label

    #calculate using existing rules and lay out the report
    def calculate(_event=None):

        try:
            value, region_number, role_key, workload, intensity_label = chosen()
            celsius = (value - 32) * 5 / 9

            #heat level on the region's sports scale
            heat = get_category(celsius, f"sports_{region_number}")
            level = heat["category"]

            #empty attendance keeps the simulation separate
            person = Person("Simulation", role_key, False, [])

            heat_tile = ft.Container(
                bgcolor=TILE_COLORS[level],
                border_radius=14,
                padding=14,
                content=ft.Row(
                    controls=[
                        ft.Column(
                            controls=[
                                ft.Text(
                                    f"{value:.0f}°F",
                                    size=38,
                                    weight=ft.FontWeight.W_900,
                                    color=TEXT_COLORS[level],
                                    style=ft.TextStyle(height=1.0)
                                ),
                                ft.Text("WBGT", size=12, color=MUTED)
                            ],
                            spacing=2,
                            tight=True
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(
                                    f"{level.title()} heat level",
                                    size=18,
                                    weight=ft.FontWeight.BOLD,
                                    color=TEXT_COLORS[level]
                                ),
                                ft.Text(
                                    f"Region {region_number} "
                                    f"({REGIONS[region_number - 1][1].lower()} climate) cutoffs",
                                    size=12,
                                    color=MUTED
                                )
                            ],
                            spacing=2,
                            expand=True
                        )
                    ],
                    spacing=16
                )
            )

            if role_key == "athlete":

                plan = athlete_plan(
                    person,
                    date.today(),
                    wbgt_c=celsius,
                    sports_region=region_number
                )

                minutes = plan["max_total_practice_minutes"]
                count = plan["max_practices"]

                if plan["rest_required"]:
                    limit_text = "Rest day"
                elif count == 0:
                    limit_text = "No outdoor practice"
                else:
                    noun = "practice" if count == 1 else "practices"
                    limit_text = f"Up to {minutes} min · {count} {noun}"

                verdict = [
                    ft.Row(
                        controls=[status_pill(HEADLINES[level], level in ("green", "yellow"))],
                        wrap=True
                    ),
                    ft.Text(heat["guidance"], size=14, color=DARK)
                ]

                limit_section = section(ft.Icons.TIMER_OUTLINED, "Allowed today", [
                    ft.Text(limit_text, size=17, weight=ft.FontWeight.BOLD, color=DARK),
                    time_bar(minutes / ATHLETE_MAX_MINUTES, LINE_COLORS[level]),
                    ft.Text(
                        "Assumes day 1 of the 14-day preseason for someone new to the heat.",
                        size=12,
                        color=MUTED
                    )
                ])

                #intensity uses the OSHA/NIOSH workload table
                exertion = get_category(
                    celsius,
                    f"workers_{workload}_unacclimatized"
                )

                extra = [section(ft.Icons.FITNESS_CENTER, f"Exertion check · {intensity_label} intensity", [
                    ft.Row(
                        controls=[status_pill(exertion["label"], exertion["category"] != "review")],
                        wrap=True
                    ),
                    ft.Text(
                        f"OSHA/NIOSH workload table: limit {exertion['limit_c'] * 9 / 5 + 32:.0f}°F "
                        f"for {intensity_label.lower()} work when new to the heat.",
                        size=12,
                        color=MUTED
                    )
                ])]

            else:
                plan = worker_plan(
                    person,
                    date.today(),
                    profile["normal_minutes"],
                    wbgt_c=celsius,
                    workload=workload
                )

                screening = plan["screening"]
                minutes = plan["max_heat_minutes"]
                hours = profile["normal_minutes"] / 60

                verdict = [
                    ft.Row(
                        controls=[status_pill(screening["label"], screening["category"] != "review")],
                        wrap=True
                    ),
                    ft.Text(screening["guidance"], size=14, color=DARK),
                    ft.Text(
                        f"OSHA/NIOSH limit for {intensity_label.lower()} work when new "
                        f"to the heat: {screening['limit_c'] * 9 / 5 + 32:.0f}°F WBGT.",
                        size=12,
                        color=MUTED
                    )
                ]

                limit_section = section(ft.Icons.TIMER_OUTLINED, "Allowed today", [
                    ft.Text(
                        f"Up to {minutes} min · {plan['percent']}% of your {hours:g} h shift",
                        size=17,
                        weight=ft.FontWeight.BOLD,
                        color=DARK
                    ),
                    time_bar(plan["percent"] / 100, LINE_COLORS[level]),
                    ft.Text(
                        "Assumes day 1 for a new worker: start at 20% and add "
                        "no more than 20% a day (NIOSH).",
                        size=12,
                        color=MUTED
                    )
                ])

                extra = []

            result.controls = [
                ft.Row(
                    controls=[
                        ft.Text("Result", size=16, weight=ft.FontWeight.BOLD, color=DARK),
                        pill("SIMULATED", "#F1F5F9", MUTED, ft.Icons.SCIENCE_OUTLINED)
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                heat_tile,
                heat_scale(value, region_number),
                section(ft.Icons.LIGHTBULB_OUTLINE, "What it means", verdict),
                limit_section
            ] + extra + [
                ft.Row(
                    controls=[
                        pill(dict(ROLES)[role_key], "#F1F5F9", DARK, ft.Icons.PERSON_OUTLINE),
                        pill(f"Region {region_number}", "#F1F5F9", DARK, ft.Icons.PLACE_OUTLINED),
                        pill(f"{intensity_label} intensity", "#F1F5F9", DARK, ft.Icons.FITNESS_CENTER)
                    ],
                    spacing=6,
                    run_spacing=6,
                    wrap=True
                ),
                ft.Text(
                    "Simulation only. Not live weather or a real attendance record.",
                    size=12,
                    color=MUTED
                )
            ]

        except (ValueError, TypeError, KeyError):
            result.controls = [ft.Text(
                "Could not run this simulation.",
                size=13,
                color="#991B1B"
            )]

        page.update()

    def slide(_event=None):
        show_values()
        page.update()

    for slider in (wbgt, region, role, intensity):
        slider.on_change = slide
        slider.on_change_end = calculate

    show_values()

    #simulation panel
    panel = ft.Column(
        controls=[
            wbgt_block,
            region_block,
            role_block,
            intensity_block,
            ft.Row(
                controls=[
                    ft.Button(
                        content="Run simulation",
                        on_click=calculate
                    )
                ]
            ),
            result_box
        ],
        spacing=14,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        visible=False
    )

    #show a result as soon as the simulator opens
    def toggle(_event=None):
        panel.visible = enabled.value

        if enabled.value:
            calculate()
        else:
            page.update()

    enabled.on_change = toggle

    return header, panel
