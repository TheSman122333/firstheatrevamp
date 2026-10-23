#FIRSTHEAT LAUNCHER

import flet as ft

from storage import (
    load_settings, save_settings, load_person, save_person,
    load_disclaimer, save_disclaimer
)
from views.home import build_home
from views.plan import build_plan
from views.my_plan import build_my_plan
from views.settings import build_settings
from views.emergency import build_emergency
from views.developer_mode import build_developer_mode
from views.legal import disclaimer_dialog


async def main(page: ft.Page):

    page.title = "FirstHeat"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = "#F8FAFC"
    page.padding = 20

    #load settings and attendance
    prefs = ft.SharedPreferences()
    settings = await load_settings(prefs)

    try:
        person = await load_person(prefs)
    except ValueError as error:
        page.add(ft.Text(str(error), color="#991B1B"))
        return

    #save changes
    async def update_settings(changes):
        await save_settings(prefs, changes)
        settings.update(changes)

    async def update_person(changes):
        await save_person(prefs, changes)
        person.update(changes)

    #simulate a session panel for Home
    simulator = build_developer_mode(page, settings, person)

    #build all screens
    home, refresh_home = build_home(
        page, settings, lambda e: go(3), simulator
    )
    weekly, refresh_weekly = build_plan(page, settings)
    my_plan, refresh_my_plan = build_my_plan(
        page, settings, person, update_person, prefs
    )

    emergency = build_emergency(page, settings)
    settings_screen = build_settings(page, settings, update_settings)

    screens = [
        home,
        weekly,
        my_plan,
        emergency,
        settings_screen
    ]

    refreshers = {
        0: refresh_home,
        1: refresh_weekly,
        2: refresh_my_plan
    }

    #navigation
    def go(index):

        page.navigation_bar.selected_index = index

        page.controls.clear()
        page.add(screens[index])

        if index in refreshers:
            page.run_task(refreshers[index])

    def navigate(event):
        go(event.control.selected_index)

    #bottom navigation
    page.navigation_bar = ft.NavigationBar(
        selected_index=0,
        destinations=[
            ft.NavigationBarDestination(
                icon=ft.Icons.HOME_OUTLINED,
                label="Home"
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.CALENDAR_MONTH,
                label="Forecast"
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.EVENT_NOTE_OUTLINED,
                label="My Plan"
            ),
            ft.NavigationBarDestination(
                icon=ft.Icon(
                    ft.Icons.WARNING,
                    color="#B91C1C"
                ),
                label="Emergency"
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.SETTINGS_OUTLINED,
                label="Settings"
            )
        ],
        on_change=navigate
    )

    page.add(home)
    page.run_task(refresh_home)

    #safety disclaimer on first launch
    if not await load_disclaimer(prefs):

        async def accept(_event=None):
            try:
                await save_disclaimer(prefs)
            except RuntimeError:
                pass

            page.pop_dialog()

        page.show_dialog(disclaimer_dialog(accept))


if __name__ == "__main__":
    ft.run(main)
