"""Plan Page: attendance and seven-day heat plan"""

import asyncio
from datetime import date

import flet as ft

from core.plan import fetch_week_plan
from core.planner import project_week
from views.brand import brand_header
from views.peak_chart import LINE_COLORS, WINDOW_COLOR
from views.sliders import side_gradient, slider_block


DARK = "#172033"
MUTED = "#64748B"
BRAND_ORANGE = "#EA580C"

ROLES = [("athlete", "Athlete"), ("worker", "Outdoor worker")]
EXPERIENCE = ["New to the heat", "Experienced"]

#usual shift slider, 2 to 12 hours in half-hour steps
SHIFT_MIN, SHIFT_MAX, SHIFT_STEP = 120, 720, 30

#new to the heat carries more risk; longer shifts mean more exposure
EXPERIENCE_COLORS = ["#F97316", "#16A34A"]
SHIFT_COLORS = ["#16A34A", "#EAB308", "#F97316"]

#light background and readable text for each heat category
CHIP_COLORS = {
    "green": ("#E5F5E9", "#166534"),
    "yellow": ("#FFF4CC", "#795500"),
    "orange": ("#FFE4D2", "#9A3412"),
    "red": ("#FCE0E0", "#991B1B"),
    "black": ("#E2E8F0", "#0F172A")
}

#alert banner styles: background, text and icon color, icon
ALERTS = {
    "caution": ("#FFF7ED", "#9A3412", ft.Icons.LOCAL_FIRE_DEPARTMENT),
    "danger": ("#FEF2F2", "#991B1B", ft.Icons.WARNING_AMBER_ROUNDED),
    "rest": ("#EFF6FF", "#1E40AF", ft.Icons.HOTEL),
    "info": ("#F1F5F9", "#334155", ft.Icons.INFO_OUTLINE),
    "done": ("#ECFDF5", "#166534", ft.Icons.CHECK_CIRCLE)
}

#quick picks for logging minutes
QUICK_MINUTES = [15, 30, 45, 60, 90]

#athletes: NATA 14-day preseason; most practice allowed in one day
PRESEASON_DAYS = 14
ATHLETE_MAX_MINUTES = 300


def role_index(role):
    return [key for key, _ in ROLES].index(role)


def shift_label(minutes):
    return f"{minutes / 60:g} h · {minutes} min"


def time_label(when):
    return f"{when:%I %p}".lstrip("0")


def window_text(window):
    if not window:
        return "No lower-heat daytime window"

    start, end = window
    return f"Lower heat {time_label(start)}–{time_label(end)}"


def card(controls, spacing=12):
    return ft.Container(
        bgcolor="#FFFFFF",
        border_radius=20,
        padding=20,
        content=ft.Column(
            controls=controls,
            spacing=spacing,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH
        )
    )


def heading(text):
    return ft.Text(text, size=19, weight=ft.FontWeight.BOLD, color=DARK)


def pill(text, background, color, icon=None):
    controls = [ft.Text(text, size=13, weight=ft.FontWeight.W_600, color=color)]

    if icon:
        controls.insert(0, ft.Icon(icon, size=16, color=color))

    return ft.Container(
        bgcolor=background,
        border_radius=999,
        padding=ft.Padding.symmetric(horizontal=10, vertical=5),
        content=ft.Row(controls=controls, spacing=4, tight=True)
    )


def alert(kind, text):
    background, color, icon = ALERTS[kind]

    return ft.Container(
        bgcolor=background,
        border_radius=12,
        padding=ft.Padding.symmetric(horizontal=12, vertical=10),
        content=ft.Row(
            controls=[
                ft.Icon(icon, size=18, color=color),
                ft.Text(text, size=13, color=color, expand=True)
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.START
        )
    )


def fact(icon, text, color=DARK):
    return ft.Row(
        controls=[
            ft.Icon(icon, size=18, color=MUTED),
            ft.Text(text, size=14, color=color, expand=True)
        ],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.START
    )


def day_alerts(day, role):
    "warnings for one day as colored banners"

    banners = []
    plan = day["plan"]

    if day["limit_minutes"] == 0:
        if plan.get("rest_required"):
            banners.append(alert("rest", "Rest day under NATA guidance."))
        elif day["category"] == "black":
            banners.append(alert("danger", "No outdoor practice under these guidelines."))
        else:
            banners.append(alert("danger", "No practice under this day's plan."))

    if day["heat_wave_proxy"]:
        banners.append(alert(
            "caution",
            "Orange+ peak: cautious heat-wave planning applied."
        ))

    screening = plan.get("screening")

    if screening and screening["category"] == "review":
        banners.append(alert(
            "danger",
            "OSHA/NIOSH screening reached. Review worksite conditions."
        ))

    if role == "athlete" and plan.get("max_practices") == 2 and plan.get("min_cool_rest_hours"):
        banners.append(alert(
            "info",
            "Allow at least three hours of cool rest between two practices."
        ))

    return banners


def build_my_plan(page, settings, profile, on_save):

    #personal settings as sliders
    role = ft.Slider(min=0, max=1, divisions=1, value=role_index(profile["role"]))

    experienced = ft.Slider(
        min=0, max=1, divisions=1, value=1 if profile["experienced"] else 0
    )

    shift = ft.Slider(
        min=SHIFT_MIN,
        max=SHIFT_MAX,
        divisions=(SHIFT_MAX - SHIFT_MIN) // SHIFT_STEP,
        value=min(max(profile["normal_minutes"], SHIFT_MIN), SHIFT_MAX)
    )

    role_block, role_value, _ = slider_block(
        "Activity",
        role,
        [name for _, name in ROLES]
    )

    experienced_block, experienced_value, _ = slider_block(
        "Heat experience",
        experienced,
        EXPERIENCE,
        side_gradient(EXPERIENCE_COLORS)
    )

    shift_block, shift_value, _ = slider_block(
        "Usual shift",
        shift,
        [f"{hours} h" for hours in range(2, 13, 2)],
        side_gradient(SHIFT_COLORS)
    )

    status = ft.Text("", color=MUTED)
    progress = ft.ProgressRing(width=20, height=20, visible=False)

    #filled in by display()
    profile_summary = ft.Row(spacing=6, run_spacing=6, wrap=True)
    plan_area = ft.Column(spacing=12, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
    log_area = ft.Column(spacing=12, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
    history_area = ft.Column(spacing=12, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    generate_button = ft.FilledButton(
        content="Generate Personalized Plan",
        icon=ft.Icons.AUTO_AWESOME,
        style=ft.ButtonStyle(bgcolor=BRAND_ORANGE, color="#FFFFFF")
    )

    edit_button = ft.TextButton(content="Edit", icon=ft.Icons.EDIT_OUTLINED)

    cached_week = None
    busy = False

    #state for the interactive parts
    editing = not profile["sessions"]
    selected = 0
    log_minutes = 60

    def chosen_minutes():
        return int(round(shift.value / SHIFT_STEP) * SHIFT_STEP)

    def is_worker():
        return profile["role"] == "worker"

    #show what each slider is set to
    def show_values():
        slider_role = ROLES[int(round(role.value))][0]

        role_value.value = ROLES[int(round(role.value))][1]
        experienced_value.value = EXPERIENCE[int(round(experienced.value))]
        shift_value.value = shift_label(chosen_minutes())

        experienced_block.visible = editing and slider_role == "worker"
        shift_block.visible = editing and slider_role == "worker"
        role_block.visible = editing

    #chips that sum up the profile when the sliders are folded away
    def show_summary():
        chips = [
            pill(
                dict(ROLES)[profile["role"]],
                "#F1F5F9",
                DARK,
                ft.Icons.ENGINEERING if is_worker() else ft.Icons.DIRECTIONS_RUN
            )
        ]

        if is_worker():
            chips.append(pill(
                EXPERIENCE[1] if profile["experienced"] else EXPERIENCE[0],
                "#F1F5F9",
                DARK,
                ft.Icons.TRENDING_UP
            ))
            chips.append(pill(
                f"{profile['normal_minutes'] / 60:g} h shift",
                "#F1F5F9",
                DARK,
                ft.Icons.WORK_OUTLINE
            ))

        profile_summary.controls = chips
        profile_summary.visible = not editing
        edit_button.content = "Done" if editing else "Edit"
        edit_button.icon = ft.Icons.CHECK if editing else ft.Icons.EDIT_OUTLINED

    def toggle_edit(_event=None):
        nonlocal editing

        editing = not editing
        show_values()
        show_summary()
        page.update()

    edit_button.on_click = toggle_edit

    def select_day(index):
        nonlocal selected

        selected = index
        display()

    def set_minutes(minutes):
        nonlocal log_minutes

        log_minutes = min(max(minutes, 5), 1440)
        display()

    #tap a bar to see that day
    def week_bars(days):
        columns = []

        for index, day in enumerate(days):
            plan = day["plan"]
            limit = day["limit_minutes"]

            if is_worker():
                share = plan["percent"] / 100
            else:
                share = limit / ATHLETE_MAX_MINUTES

            chosen = index == selected

            columns.append(
                ft.Container(
                    expand=True,
                    border_radius=10,
                    padding=ft.Padding.symmetric(vertical=6),
                    bgcolor="#FFEDD5" if chosen else None,
                    ink=True,
                    on_click=lambda e, i=index: select_day(i),
                    tooltip=f"{day['date']:%a %b %d}: {day['summary']}",
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                f"{limit}m" if limit else "—",
                                size=12,
                                weight=ft.FontWeight.W_700,
                                color=DARK if limit else MUTED,
                                no_wrap=True
                            ),
                            ft.Container(
                                width=22,
                                height=max(6, 70 * min(share, 1)),
                                border_radius=ft.BorderRadius.only(top_left=6, top_right=6),
                                bgcolor=LINE_COLORS[day["category"]] if limit else "#CBD5E1"
                            ),
                            ft.Text(
                                "Today" if index == 0 else f"{day['date']:%a}",
                                size=11,
                                weight=ft.FontWeight.W_700 if chosen else None,
                                color=BRAND_ORANGE if chosen else MUTED,
                                no_wrap=True
                            ),
                            ft.Icon(
                                ft.Icons.CHECK_CIRCLE,
                                size=14,
                                color=WINDOW_COLOR if day["completed"] else ft.Colors.TRANSPARENT
                            )
                        ],
                        spacing=4,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER
                    )
                )
            )

        return ft.Row(
            controls=columns,
            spacing=2,
            vertical_alignment=ft.CrossAxisAlignment.END
        )

    #ring and key facts for the chosen day
    def day_detail(day):
        plan = day["plan"]
        limit = day["limit_minutes"]
        day_number = plan["day"]
        background, ink = CHIP_COLORS[day["category"]]

        if is_worker():
            ring_value = plan["percent"] / 100
            ring_big = f"{plan['percent']}%"
            ring_small = "of your shift"
            facts = [
                fact(ft.Icons.EVENT_REPEAT, f"Day {day_number} in the heat"),
                fact(ft.Icons.TIMER_OUTLINED, f"Up to {limit} min of heat exposure")
            ]
        else:
            ring_value = min(day_number, PRESEASON_DAYS) / PRESEASON_DAYS
            ring_big = f"Day {day_number}"
            ring_small = f"of {PRESEASON_DAYS}"

            if limit:
                count = plan["max_practices"]
                noun = "practice" if count == 1 else "practices"
                limit_text = f"{count} {noun} · up to {limit} min"
            else:
                limit_text = day["summary"]

            facts = [
                fact(ft.Icons.EVENT_REPEAT, f"Day {day_number} of the preseason"),
                fact(ft.Icons.TIMER_OUTLINED, limit_text)
            ]

        facts.append(fact(
            ft.Icons.SCHEDULE,
            window_text(day["window"]),
            WINDOW_COLOR if day["window"] else "#B91C1C"
        ))

        title = f"{day['date']:%a, %b %d}"

        ring = ft.Stack(
            width=104,
            height=104,
            alignment=ft.Alignment.CENTER,
            controls=[
                ft.ProgressRing(
                    value=ring_value,
                    width=104,
                    height=104,
                    stroke_width=10,
                    color=BRAND_ORANGE,
                    bgcolor="#F1F5F9",
                    stroke_cap=ft.StrokeCap.ROUND
                ),
                ft.Column(
                    controls=[
                        ft.Text(ring_big, size=22, weight=ft.FontWeight.W_900, color=DARK),
                        ft.Text(ring_small, size=11, color=MUTED)
                    ],
                    spacing=0,
                    tight=True,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER
                )
            ]
        )

        controls = [
            ft.Row(
                controls=[
                    ft.Text(
                        f"Today · {title}" if selected == 0 else title,
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=DARK
                    ),
                    pill(
                        f"Peak {day['peak_wbgt'] * 9 / 5 + 32:.1f}°F · {day['category'].title()}",
                        background,
                        ink
                    )
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                wrap=True,
                run_spacing=6
            ),
            ft.Row(
                controls=[
                    ring,
                    ft.Column(controls=facts, spacing=8, expand=True)
                ],
                spacing=16
            )
        ]

        controls += day_alerts(day, profile["role"])

        if day["projected"]:
            controls.append(ft.Text(
                "Projected: assumes you complete each earlier day "
                "with the activity allowed.",
                size=12,
                color=MUTED
            ))

        return controls

    #log today's minutes with quick picks and a stepper
    def log_controls(today):
        limit = today["limit_minutes"]
        noun = "work" if is_worker() else "practice"

        if today["completed"]:
            done = sum(
                item["minutes"] for item in profile["sessions"]
                if item["day"] == today["date"].isoformat()
            )
            return [alert("done", f"Today is logged: {done} min of {noun}. See you tomorrow.")]

        if limit == 0:
            return [alert("rest", "Nothing to log today. Your plan has no activity planned.")]

        chips = []

        for minutes in [m for m in QUICK_MINUTES if m < limit] + [limit]:
            chosen = minutes == log_minutes
            label = f"Max {minutes}" if minutes == limit else f"{minutes}"

            chips.append(
                ft.Container(
                    bgcolor=BRAND_ORANGE if chosen else "#F1F5F9",
                    border_radius=999,
                    padding=ft.Padding.symmetric(horizontal=12, vertical=7),
                    ink=True,
                    on_click=lambda e, m=minutes: set_minutes(m),
                    content=ft.Text(
                        label,
                        size=13,
                        weight=ft.FontWeight.W_600,
                        color="#FFFFFF" if chosen else DARK
                    )
                )
            )

        controls = [
            ft.Text(
                f"How long did you {noun} in the heat today?",
                size=14,
                color=MUTED
            ),
            ft.Row(
                controls=[
                    ft.IconButton(
                        icon=ft.Icons.REMOVE,
                        bgcolor="#F1F5F9",
                        on_click=lambda e: set_minutes(log_minutes - 5),
                        tooltip="5 minutes less"
                    ),
                    ft.Text(
                        f"{log_minutes} min",
                        size=30,
                        weight=ft.FontWeight.W_900,
                        color=DARK,
                        text_align=ft.TextAlign.CENTER,
                        expand=True
                    ),
                    ft.IconButton(
                        icon=ft.Icons.ADD,
                        bgcolor="#F1F5F9",
                        on_click=lambda e: set_minutes(log_minutes + 5),
                        tooltip="5 minutes more"
                    )
                ]
            ),
            ft.Row(
                controls=chips,
                spacing=6,
                run_spacing=6,
                wrap=True,
                alignment=ft.MainAxisAlignment.CENTER
            )
        ]

        if log_minutes > limit:
            controls.append(alert(
                "caution",
                f"That is over today's {limit}-minute limit. "
                "Review your heat precautions."
            ))

        controls.append(
            ft.FilledButton(
                content="Mark today done",
                icon=ft.Icons.CHECK,
                on_click=mark_done,
                style=ft.ButtonStyle(bgcolor=WINDOW_COLOR, color="#FFFFFF")
            )
        )

        return controls

    #recent attendance and the reset option
    def history_controls():
        sessions = sorted(profile["sessions"], key=lambda item: item["day"], reverse=True)

        if not sessions:
            body = [ft.Text(
                "No sessions logged yet. Each day you log moves your plan forward.",
                size=13,
                color=MUTED
            )]
        else:
            chips = [
                pill(
                    f"{date.fromisoformat(item['day']):%b %d} · {item['minutes']} min",
                    "#ECFDF5",
                    "#166534",
                    ft.Icons.CHECK
                )
                for item in sessions[:8]
            ]

            if len(sessions) > 8:
                chips.append(pill(f"+{len(sessions) - 8} more", "#F1F5F9", MUTED))

            body = [ft.Row(controls=chips, spacing=6, run_spacing=6, wrap=True)]

        return [
            ft.Row(
                controls=[
                    heading("Your sessions"),
                    ft.TextButton(
                        content="Reset",
                        icon=ft.Icons.RESTART_ALT,
                        disabled=not sessions,
                        style=ft.ButtonStyle(color="#B91C1C"),
                        on_click=lambda e: page.show_dialog(reset_dialog)
                    )
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            )
        ] + body

    #display current and future plans
    def display():

        show_summary()
        history_area.controls = history_controls()

        plan_card.visible = log_card.visible = cached_week is not None

        if cached_week is None:
            plan_area.controls = []
            log_area.controls = []
            page.update()
            return

        days = project_week(
            profile,
            cached_week,
            settings["region"]
        )

        plan_area.controls = [
            ft.Row(
                controls=[
                    heading("Your 7-day plan"),
                    ft.Text("Tap a day", size=12, color=MUTED)
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            ),
            week_bars(days),
            ft.Divider(height=1, color="#E2E8F0")
        ] + day_detail(days[selected])

        log_area.controls = [heading("Log today")] + log_controls(days[0])

        page.update()

    #save personal settings
    async def save_form(_event=None):

        try:
            chosen_role = ROLES[int(round(role.value))][0]

            if profile["sessions"] and chosen_role != profile["role"]:
                role.value = role_index(profile["role"])
                show_values()
                raise ValueError(
                    "Reset attendance before changing activity."
                )

            #shift only matters for workers
            if chosen_role == "worker":
                minutes = chosen_minutes()
            else:
                minutes = profile["normal_minutes"]

            updated = {
                **profile,
                "role": chosen_role,
                "experienced": int(round(experienced.value)) == 1,
                "normal_minutes": minutes
            }

            await on_save(updated)

            show_values()
            status.value = "Preferences saved"
            display()

        except (ValueError, RuntimeError) as error:
            status.value = str(error)

        page.update()

    #mark todays attendance
    async def mark_done(_event=None):

        if cached_week is None:
            status.value = "Generate your plan first."
            page.update()
            return

        try:
            minutes = log_minutes

            if not 1 <= minutes <= 1440:
                raise ValueError(
                    "Enter a duration between 1 and 1440 minutes."
                )

            today = project_week(
                profile,
                cached_week,
                settings["region"]
            )[0]

            if today["completed"]:
                raise ValueError("Today has already been recorded.")

            if today["limit_minutes"] == 0:
                raise ValueError("No activity is planned for today.")

            record = {
                "day": today["date"].isoformat(),
                "minutes": minutes,
                "kind": (
                    "work" if profile["role"] == "worker"
                    else "practice"
                ),
                "heat_wave": today["heat_wave_proxy"]
            }

            await on_save({
                **profile,
                "sessions": profile["sessions"] + [record]
            })

            status.value = "Today's attendance saved."

            if minutes > today["limit_minutes"]:
                status.value += (
                    " You exceeded the planning limit. "
                    "Review your heat precautions."
                )

            display()

        except (ValueError, RuntimeError) as error:
            status.value = str(error)

        page.update()

    #reset saved attendance
    async def reset_attendance(_event=None):

        try:
            await on_save({
                **profile,
                "sessions": []
            })

            page.pop_dialog()

            status.value = "Attendance history reset."

            display()

        except (ValueError, RuntimeError) as error:
            status.value = f"Could not reset attendance: {error}"

        page.update()

    #confirm before resetting
    reset_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Reset attendance?"),
        content=ft.Text(
            "This will permanently delete your attendance history "
            "and restart your acclimatization progress."
        ),
        actions=[
            ft.TextButton(
                content="Cancel",
                on_click=lambda e: page.pop_dialog()
            ),
            ft.TextButton(
                content="Reset",
                on_click=reset_attendance
            )
        ]
    )

    #load forecast without freezing the app
    async def refresh(_event=None):
        nonlocal cached_week, busy, editing, log_minutes

        if busy:
            return

        busy = True
        progress.visible = True
        generate_button.disabled = True
        status.value = "Building your plan..."

        page.update()

        try:
            cached_week = await asyncio.to_thread(
                fetch_week_plan,
                settings.copy()
            )

            #fold the profile away once the plan is ready
            if _event is not None:
                editing = False
                show_values()

            today_limit = project_week(profile, cached_week, settings["region"])[0]["limit_minutes"]
            log_minutes = min(60, today_limit) if today_limit else 60

            display()
            status.value = "Plan updated with the latest forecast"

        except Exception as error:
            cached_week = None
            plan_card.visible = log_card.visible = False
            status.value = f"Could not load your plan: {error}"

        finally:
            busy = False
            progress.visible = False
            generate_button.disabled = False
            page.update()

    #slider actions
    def slide(_event=None):
        show_values()
        page.update()

    for slider in (role, experienced, shift):
        slider.on_change = slide
        slider.on_change_end = save_form

    generate_button.on_click = refresh

    show_values()
    show_summary()
    history_area.controls = history_controls()

    profile_card = card(
        [
            ft.Row(
                controls=[heading("Your profile"), edit_button],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            ),
            profile_summary,
            role_block,
            experienced_block,
            shift_block,
            ft.Row(controls=[generate_button, progress], wrap=True)
        ],
        spacing=14
    )

    plan_card = card([plan_area])
    log_card = card([log_area])
    plan_card.visible = log_card.visible = False

    #page layout
    screen = ft.SafeArea(
        expand=True,
        content=ft.Column(
            controls=[
                brand_header(),
                ft.Text(
                    "My Acclimation Planner",
                    size=22,
                    weight=ft.FontWeight.BOLD,
                    color=DARK
                ),
                ft.Text(
                    "Build up heat time day by day. Log each day you "
                    "train or work and the plan adjusts.",
                    size=13,
                    color=MUTED
                ),
                profile_card,
                status,
                plan_card,
                log_card,
                card([history_area]),
                ft.Text(
                    "Estimated WBGT, not an on-site measurement. "
                    "Orange+ is an app-defined heat-wave flag, "
                    "not an official NIOSH threshold. "
                    "Follow local heat policies.",
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
