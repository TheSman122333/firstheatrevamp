
"Emergency heat-stroke guidance, timer, and temporary EMS event log"
"ASSISTED BY AI"


import asyncio
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import flet as ft

from views.brand import brand_header


CDC_SOURCE = "https://www.cdc.gov/niosh/heat-stress/about/illnesses.html"
KSI_SOURCE = "https://koreystringer.institute.uconn.edu/heat-stroke/"


def build_emergency(page, settings):

    #everything stays in memory until this app session closes
    events = []
    running = False
    started = 0.0
    elapsed = 0
    timer_id = 0

    clock = ft.Text("00:00", size=44, weight=ft.FontWeight.BOLD)
    note = ft.TextField(label="Optional note for next event", max_length=160)
    log = ft.Text("No events recorded yet.", selectable=True, size=13)
    message = ft.Text("Times use the city selected in Settings.", size=12)

    start_button = ft.Button(content="Start timer", height=52)
    stop_button = ft.Button(content="Stop timer", height=52, disabled=True)
    copy_button = ft.Button(
        content="Copy log",
        icon=ft.Icons.CONTENT_COPY,
        action=ft.CopyToClipboard("No events recorded yet.")
    )

    wake = ft.Wakelock()
    haptic = ft.HapticFeedback()

    #timestamp for EMS
    def timestamp():
        local = datetime.now(timezone.utc).astimezone(
            ZoneInfo(settings["timezone"])
        )
        return local.strftime("%Y-%m-%d %I:%M:%S %p %Z")

    def show_time(seconds):
        minutes, seconds = divmod(seconds, 60)
        clock.value = f"{minutes:02d}:{seconds:02d}"

    #keep copied text up to date
    def update_log():
        text = "FirstHeat EMS event log\n" + "\n".join(events)
        log.value = "\n".join(events) if events else "No events recorded yet."
        copy_button.action = ft.CopyToClipboard(text)
        page.update()

    async def record(label):

        entry = f"{timestamp()} — {label}"

        if note.value and note.value.strip():
            entry += f" — {note.value.strip()[:160]}"
            note.value = ""

        events.append(entry)

        try:
            await haptic.heavy_impact()
        except Exception:
            pass  #some devices don't support vibration

        update_log()

    #timer
    async def tick(this_timer):
        while running and this_timer == timer_id:
            show_time(elapsed + int(time.monotonic() - started))
            page.update()
            await asyncio.sleep(1)

    async def start_timer(_event=None):
        nonlocal running, started, timer_id

        if running:
            return

        running = True
        started = time.monotonic()
        timer_id += 1

        start_button.disabled = True
        stop_button.disabled = False

        try:
            await wake.enable()
        except Exception:
            message.value = "Wake lock unavailable. Keep the screen awake."

        await record("Timer started")
        page.run_task(tick, timer_id)

    async def stop_timer(_event=None):
        nonlocal running, elapsed, timer_id

        if not running:
            return

        elapsed += int(time.monotonic() - started)
        running = False
        timer_id += 1

        show_time(elapsed)
        start_button.disabled = False
        stop_button.disabled = True

        try:
            await wake.disable()
        except Exception:
            pass

        await record("Timer stopped")

    #quick log buttons
    def event_button(label):
        return ft.Button(
            content=label,
            height=52,
            on_click=lambda e: page.run_task(record, label)
        )

    start_button.on_click = start_timer
    stop_button.on_click = stop_timer

    #opening the dialer does not confirm a completed call
    call_button = ft.Button(
        content="CALL 911",
        icon=ft.Icons.PHONE,
        color="#FFFFFF",
        bgcolor="#B91C1C",
        height=68,
        expand=True,
        style=ft.ButtonStyle(
            text_style=ft.TextStyle(size=20, weight=ft.FontWeight.BOLD),
            icon_size=26
        ),
        action=ft.OpenUrl("tel:911"),
        on_click=lambda e: page.run_task(
            record, "911 button pressed — call not confirmed"
        )
    )

    #emergency screen
    screen = ft.SafeArea(
        expand=True,
        content=ft.Column(
            controls=[
                brand_header(),
                ft.Text(
                    "Emergency",
                    size=26,
                    weight=ft.FontWeight.BOLD,
                    color="#991B1B"
                ),
                #full width so it is the easiest thing to tap
                ft.Row(controls=[call_button]),
                ft.Text(
                    "If the dialer doesn't open, call 911 directly. "
                    "Don't wait for this app. This app does not contact "
                    "emergency services."
                ),
                ft.Text(
                    "If you suspect heat stroke",
                    size=21,
                    weight=ft.FontWeight.BOLD
                ),
                ft.Text(
                    "Warning signs can include confusion, slurred speech, "
                    "unconsciousness, seizures, and very high body temperature. "
                    "Sweating may still occur."
                ),
                ft.Text(
                    "Call 911. Move the person into shade or a cooler area, "
                    "remove outer clothing, and begin cooling immediately. "
                    "Use cold water or an ice bath where safe and available; "
                    "otherwise wet the skin and apply cold, wet cloths. "
                    "Stay with them."
                ),
                ft.Text(
                    "KSI guidance for suspected exertional heat stroke: "
                    "trained responders with proper cooling equipment should "
                    "'cool first, transport second' while coordinating with EMS. "
                    "Never delay calling emergency services."
                ),
                ft.Row([
                    ft.TextButton(content="CDC first aid", url=CDC_SOURCE),
                    ft.TextButton(content="KSI guidance", url=KSI_SOURCE)
                ], wrap=True),

                ft.Divider(),

                ft.Text(
                    "Event timer",
                    size=21,
                    weight=ft.FontWeight.BOLD
                ),
                clock,
                ft.Row([start_button, stop_button], wrap=True),
                message,

                ft.Divider(),

                ft.Text(
                    "EMS event log",
                    size=21,
                    weight=ft.FontWeight.BOLD
                ),
                ft.Text(
                    "Only log events you confirmed. "
                    "The 911 button only opens a dialer."
                ),
                ft.Row([
                    event_button("911 called"),
                    event_button("Cooling started")
                ], wrap=True),
                ft.Row([
                    event_button("Moved to shade"),
                    event_button("EMS arrived")
                ], wrap=True),
                note,
                log,
                copy_button,
                ft.Text(
                    "The log is not saved or transmitted. "
                    "Times follow your selected city's timezone; "
                    "verify this if you're elsewhere.",
                    size=12,
                    color="#64748B"
                )
            ],
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
    )

    return screen
