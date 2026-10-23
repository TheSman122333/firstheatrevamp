
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

    result = ft.Text(
        "SIMULATED — no real records will change.",
        selectable=True
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

    #calculate using existing rules
    def calculate(_event=None):

        try:
            value, region_number, role_key, workload, intensity_label = chosen()
            celsius = (value - 32) * 5 / 9

            #empty attendance keeps the simulation separate
            person = Person("Simulation", role_key, False, [])

            exertion_line = ""

            if role_key == "athlete":

                category = get_category(
                    celsius,
                    f"sports_{region_number}"
                )

                plan = athlete_plan(
                    person,
                    date.today(),
                    wbgt_c=celsius,
                    sports_region=region_number
                )

                if plan["rest_required"]:
                    limit = "Rest day"
                elif plan["max_practices"] == 0:
                    limit = "No outdoor practice"
                else:
                    limit = (
                        f"{plan['max_practices']} practice(s), "
                        f"up to {plan['max_total_practice_minutes']} minutes"
                    )

                #intensity uses the OSHA/NIOSH workload table
                exertion = get_category(
                    celsius,
                    f"workers_{workload}_unacclimatized"
                )

                exertion_line = (
                    f"SIMULATED exertion check ({intensity_label}, "
                    f"OSHA/NIOSH workload table): {exertion['label']}\n"
                )

            else:
                plan = worker_plan(
                    person,
                    date.today(),
                    profile["normal_minutes"],
                    wbgt_c=celsius,
                    workload=workload
                )

                category = plan["screening"]

                limit = (
                    f"Day {plan['day']}: {plan['percent']}%, "
                    f"up to {plan['max_heat_minutes']} min"
                )

            result.value = (
                f"SIMULATED WBGT: {value:.0f} °F\n"
                f"SIMULATED intensity: {intensity_label}\n"
                f"SIMULATED risk: {category['label']}\n"
                f"SIMULATED guidance: {category['guidance']}\n"
                f"{exertion_line}"
                f"SIMULATED limit: {limit}\n"
                "Not live weather or a real attendance record."
            )

        except (ValueError, TypeError, KeyError):
            result.value = "SIMULATED — could not run this simulation."

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
            result
        ],
        spacing=14,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        visible=False
    )

    def toggle(_event=None):
        panel.visible = enabled.value
        page.update()

    enabled.on_change = toggle

    return header, panel
