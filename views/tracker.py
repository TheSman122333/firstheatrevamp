"Activity tracker: times today's activity and reminds about breaks with a sound."

import asyncio
import math
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import flet as ft

from core.rules import break_schedule
from views.demo_reminders import demo_timing  #demo reminders, remove later
from storage import load_tracker, save_tracker

DARK = "#172033"
MUTED = "#64748B"
BRAND_ORANGE = "#EA580C"
DONE_GREEN = "#16A34A"
MISSED_RED = "#DC2626"

#each reminder stays up this long before it counts as missed
REMINDER_SECONDS = 30

#reminder-sound.js chimes while the page title starts with the alarm clock
APP_TITLE = "FirstHeat"
ALARM_TITLE = "⏰ Break time · FirstHeat"


def clock_text(seconds):
    seconds = int(seconds)
    return f"{seconds // 3600}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def interval_text(minutes):
    "20 minutes, 1 minute or 30 seconds"

    seconds = round(minutes * 60)

    if seconds % 60:
        return f"{seconds} seconds"

    return "1 minute" if seconds == 60 else f"{seconds // 60} minutes"


def reminder_dots(done, missed, size=9):
    "one green dot per break taken, one red dot per reminder missed"

    return ft.Row(
        controls=[
            ft.Container(
                width=size,
                height=size,
                border_radius=size / 2,
                bgcolor=DONE_GREEN if index < done else MISSED_RED
            )
            for index in range(done + missed)
        ],
        spacing=3,
        run_spacing=3,
        wrap=True,
        alignment=ft.MainAxisAlignment.CENTER
    )


def build_tracker(page, prefs, settings, on_use_minutes, on_change):
    """Card that times today's activity and shows break reminders.

    Returns the card and a dict of functions My Plan uses:
    set_today, counts, minutes, clear and restore.
    """

    wake = ft.Wakelock()
    haptic = ft.HapticFeedback()

    def today():
        return datetime.now(ZoneInfo(settings["timezone"])).date().isoformat()

    def fresh_state():
        return {
            "day": today(),
            "elapsed": 0,
            "started": None,
            "every": 20,
            "break": 3,
            "next": 1,
            "done": 0,
            "missed": 0,
            #demo reminders, remove later: the Settings timing in use, if any
            "demo": None
        }

    state = fresh_state()

    #from My Plan: today's limit, heat category and whether it is logged
    limit = None
    category = None
    logged = False

    loop_task = None
    reminder = None
    reminder_opened = None

    switch = ft.Switch(value=False)

    intro = ft.Text("", size=13, color=MUTED)
    black_warning = ft.Text(
        "Today's heat is Black: outdoor training is not recommended. "
        "Use the tracker only for indoor or essential activity.",
        size=13,
        color="#991B1B",
        visible=False
    )

    clock = ft.Text("0:00:00", size=36, weight=ft.FontWeight.W_900, color=DARK)
    state_label = ft.Text("", size=12, weight=ft.FontWeight.W_600, color=MUTED)
    progress = ft.ProgressBar(value=0, bar_height=10, color=DONE_GREEN, bgcolor="#E2E8F0", border_radius=5)
    progress_text = ft.Text("", size=13, color=MUTED)
    next_text = ft.Text("", size=14, color=DARK)
    dots = ft.Row()
    counts_text = ft.Text("", size=13, color=MUTED)

    use_button = ft.FilledTonalButton(content="", icon=ft.Icons.EDIT_CALENDAR)

    live = ft.Column(
        controls=[
            ft.Row(
                controls=[clock, state_label],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.END
            ),
            progress,
            progress_text,
            ft.Row(
                controls=[ft.Icon(ft.Icons.WATER_DROP_OUTLINED, size=18, color="#0284C7"), next_text],
                spacing=6
            ),
            ft.Column(controls=[dots, counts_text], spacing=4),
            ft.Row(controls=[use_button])
        ],
        spacing=8,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        visible=False
    )

    def total_seconds():
        if state["started"] is None:
            return state["elapsed"]

        return state["elapsed"] + time.time() - state["started"]

    def tracked_minutes():
        return round(total_seconds() / 60)

    async def persist():
        try:
            await save_tracker(prefs, state)
        except (RuntimeError, ValueError):
            pass

    #redraw the card from the current state
    def render():
        running = state["started"] is not None
        total = total_seconds()

        switch.value = running
        switch.disabled = logged

        if logged:
            intro.value = "Today is logged. The tracker is ready again tomorrow."
        else:
            intro.value = (
                f"Turn on to time today's activity. You'll get a break reminder "
                f"every {interval_text(state['every'])} of activity ({state['break']}-minute "
                "breaks: water and shade), with a sound. Keep this page open."
            )

            if state.get("demo"):
                intro.value += " Demo timing from Settings."

        black_warning.visible = category == "black" and not logged
        live.visible = total > 0 or running

        clock.value = clock_text(total)
        state_label.value = "TRACKING" if running else "PAUSED"
        state_label.color = DONE_GREEN if running else MUTED

        if limit:
            progress.value = min(total / 60 / limit, 1)
            progress.color = MISSED_RED if total / 60 > limit else DONE_GREEN
            progress_text.value = f"{total / 60:.0f} of {limit} min planned today"
        else:
            progress.value = 0
            progress_text.value = "Create your plan to compare with today's limit."

        due = state["next"] * state["every"] * 60
        left = max(due - total, 0)

        if running:
            next_text.value = f"Next break in {clock_text(left)[2:]}"
        else:
            next_text.value = f"Next break after {clock_text(left)[2:]} more of activity"

        done, missed = state["done"], state["missed"]
        dots.controls = [reminder_dots(done, missed)]
        counts_text.value = (
            f"{done} break{'s' if done != 1 else ''} taken · {missed} missed"
            if done + missed else "No reminders yet"
        )

        minutes = tracked_minutes()
        use_button.content = f"Use {minutes} min for today's log"
        use_button.visible = minutes > 0 and not logged

    #how long a reminder stays up
    def window():
        demo = demo_timing(settings)
        return demo["window_seconds"] if demo else REMINDER_SECONDS

    #break reminder with a countdown, 30 seconds unless the demo timing says otherwise
    def open_reminder():
        nonlocal reminder, reminder_opened

        reminder_opened = time.time()
        seconds = window()

        #advance now so a reconnect doesn't repeat this reminder
        state["next"] += 1

        left_text = ft.Text(f"Closes in {seconds} s", size=12, color=MUTED)
        left_bar = ft.ProgressBar(value=1, bar_height=6, color=BRAND_ORANGE, bgcolor="#E2E8F0", border_radius=3)

        reminder = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.WATER_DROP, color="#0284C7"),
                    ft.Text("Break time", size=20, weight=ft.FontWeight.BOLD, color=DARK)
                ],
                spacing=8
            ),
            content=ft.Column(
                controls=[
                    ft.Text(
                        f"Take a {state['break']}-minute break: drink water and "
                        "rest in the shade. Check in with how you feel.",
                        size=15,
                        color=DARK
                    ),
                    left_bar,
                    left_text
                ],
                spacing=10,
                tight=True
            ),
            actions=[
                ft.FilledButton(
                    content="I took my break",
                    icon=ft.Icons.CHECK,
                    style=ft.ButtonStyle(bgcolor=DONE_GREEN, color="#FFFFFF"),
                    on_click=lambda e: page.run_task(close_reminder, True)
                )
            ]
        )

        #keep these to update the countdown
        reminder.data = (left_text, left_bar, seconds)

        page.title = ALARM_TITLE
        page.show_dialog(reminder)
        page.run_task(buzz)

    async def buzz():
        try:
            await haptic.heavy_impact()
        except Exception:
            pass

    async def close_reminder(taken):
        nonlocal reminder, reminder_opened

        if reminder is None:
            return

        state["done" if taken else "missed"] += 1

        if reminder.open:
            reminder.open = False
            reminder.update()

        reminder = None
        reminder_opened = None
        page.title = APP_TITLE

        await persist()
        render()
        on_change()
        page.update()

    #once a second while tracking or while a reminder is up
    async def tick():
        if state["day"] != today():
            await stop_for_new_day()
            return

        if reminder is None and follow_settings():
            await persist()

        if state["started"] is not None and reminder is None:
            total = total_seconds()
            every = state["every"] * 60
            due = state["next"] * every

            if total >= due:
                if total - due > window():
                    #reminders that came due while the app was closed never showed
                    state["next"] = int(total // every) + 1
                    await persist()
                else:
                    open_reminder()
                    await persist()

        if reminder is not None:
            left_text, left_bar, seconds = reminder.data
            left = seconds - (time.time() - reminder_opened)

            if left <= 0:
                await close_reminder(False)
            else:
                left_text.value = f"Closes in {math.ceil(left)} s"
                left_bar.value = left / seconds

        render()
        page.update()

    async def run_loop():
        nonlocal loop_task

        try:
            while state["started"] is not None or reminder is not None:
                await tick()
                await asyncio.sleep(1)
        finally:
            loop_task = None

    def ensure_loop():
        nonlocal loop_task

        if loop_task is None:
            loop_task = page.run_task(run_loop)

    async def keep_awake(on):
        try:
            if on:
                await wake.enable()
            else:
                await wake.disable()
        except Exception:
            pass

    async def start():
        state["started"] = time.time()
        await persist()
        await keep_awake(True)
        ensure_loop()

    async def pause():
        state["elapsed"] = total_seconds()
        state["started"] = None
        await persist()
        await keep_awake(False)

    async def stop_for_new_day():
        nonlocal state

        if reminder is not None:
            await close_reminder(False)

        state = fresh_state()
        apply_schedule()
        await persist()
        await keep_awake(False)
        render()
        on_change()

    async def toggle(_event=None):
        if switch.value:
            await start()
        else:
            await pause()

        render()
        page.update()

    switch.on_change = toggle

    def use_minutes(_event=None):
        on_use_minutes(max(1, tracked_minutes()))

    use_button.on_click = use_minutes

    def apply_schedule():
        demo = demo_timing(settings)
        state["demo"] = demo

        if demo:
            seconds = demo["every_seconds"]
            state["every"] = seconds // 60 if seconds % 60 == 0 else seconds / 60
            state["break"] = demo["break_minutes"]
        elif category:
            schedule = break_schedule(category)
            state["every"] = schedule["every_minutes"]
            state["break"] = schedule["break_minutes"]
        else:
            state["every"], state["break"] = 20, 3

    #demo reminders, remove later: switch timing as soon as Settings changes
    def follow_settings():
        if demo_timing(settings) == state.get("demo"):
            return False

        apply_schedule()

        #next reminder at the next full interval of activity
        state["next"] = int(total_seconds() // (state["every"] * 60)) + 1
        return True

    #My Plan passes today's numbers whenever it redraws
    def set_today(today_limit, today_category, today_logged):
        nonlocal limit, category, logged

        limit, category, logged = today_limit, today_category, today_logged

        #schedule follows today's heat until the first reminder
        if state["next"] == 1:
            apply_schedule()
        elif reminder is None and follow_settings():
            page.run_task(persist)

        render()

    def counts():
        return state["done"], state["missed"]

    #after today is logged: stop and start fresh, keeping nothing
    async def clear():
        nonlocal state

        if reminder is not None:
            await close_reminder(False)

        state = fresh_state()
        apply_schedule()
        await persist()
        await keep_awake(False)
        render()

    #pick up a session that was running before a reconnect
    async def restore():
        nonlocal state

        saved = await load_tracker(prefs)

        if saved and saved["day"] == today():
            state = saved

            if state["started"] is not None:
                await keep_awake(True)
                ensure_loop()

        render()
        on_change()
        page.update()

    card = ft.Container(
        bgcolor="#FFFFFF",
        border_radius=20,
        padding=20,
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.TIMER_OUTLINED, color=BRAND_ORANGE),
                        ft.Text(
                            "Activity tracker",
                            size=19,
                            weight=ft.FontWeight.BOLD,
                            color=DARK,
                            expand=True
                        ),
                        switch
                    ],
                    spacing=8
                ),
                intro,
                black_warning,
                live
            ],
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH
        )
    )

    render()

    return card, {
        "set_today": set_today,
        "counts": counts,
        "minutes": tracked_minutes,
        "clear": clear,
        "restore": restore
    }
