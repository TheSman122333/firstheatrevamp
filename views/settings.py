"Settings: select city and sports region"

import asyncio
import flet as ft

from core.geocoding import search_cities
from views.brand import brand_header


KSI_MAP = "https://www.recognizetorecover.org/s/Heat-Guidelines.pdf"


def build_settings(page, settings, on_save):

    #current location
    selected = ft.Text("", size=15)

    #city search
    search_box = ft.TextField(
        label="City or ZIP code",
        hint_text="Detroit or 48226"
    )

    message = ft.Text("", color="#64748B")
    spinner = ft.ProgressRing(width=20, height=20, visible=False)
    results = ft.Column(spacing=5)

    search_button = ft.Button(
        content="Search",
        icon=ft.Icons.SEARCH
    )

    #sports region
    region = ft.Dropdown(
        label="Sports climate region",
        value=str(settings["region"]),
        options=[
            ft.DropdownOption(
                key=str(i),
                text=f"Region {i}"
            )
            for i in (1, 2, 3)
        ]
    )

    def update_location():

        selected.value = (
            f"Selected: {settings['name']}, {settings['state']}"
        )

        region.value = str(settings["region"])

    #save city and default to region 1
    async def choose_city(city):

        try:
            await on_save({
                **settings,
                **city,
                "region": 1
            })

            update_location()

            message.value = (
                "Location saved. Using Region 1 (most cautious) "
                "until you choose your region from the map."
            )

            results.controls.clear()

        except Exception as error:
            message.value = f"Could not save location: {error}"

        page.update()

    #search for cities
    async def search(_event=None):

        search_button.disabled = True
        spinner.visible = True
        message.value = "Searching cities..."
        results.controls.clear()

        page.update()

        try:
            #fetch city results without freezing the app
            cities = await asyncio.to_thread(
                search_cities,
                search_box.value or "",
                10
            )

            message.value = (
                f"{len(cities)} cities found"
                if cities else "No matching cities found"
            )

            for city in cities:

                async def pick(event, place=city):
                    await choose_city(place)

                results.controls.append(
                    ft.ListTile(
                        title=ft.Text(
                            f"{city['name']}, {city['state']}"
                        ),
                        subtitle=ft.Text(city["timezone"]),
                        trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT),
                        on_click=pick
                    )
                )

        except Exception as exc:
            message.value = f"Search failed: {exc}"

        finally:
            spinner.visible = False
            search_button.disabled = False
            page.update()

    #save chosen sports region
    async def select_region(_event=None):

        try:
            await on_save({
                **settings,
                "region": int(region.value)
            })

            message.value = "Sports region saved"

        except Exception as exc:
            message.value = f"Could not save region: {exc}"
            region.value = str(settings["region"])

        page.update()

    search_button.on_click = search
    search_box.on_submit = search
    region.on_select = select_region

    update_location()

    #settings layout
    screen = ft.SafeArea(
        expand=True,
        content=ft.Column(
            controls=[
                brand_header(),
                ft.Text(
                    "Settings",
                    size=22,
                    weight=ft.FontWeight.BOLD,
                    color="#172033"
                ),
                selected,
                ft.Text(
                    "Location",
                    size=20,
                    weight=ft.FontWeight.BOLD
                ),
                search_box,
                ft.Row([search_button, spinner]),
                message,
                results,
                ft.Divider(),
                ft.Text(
                    "Regional sports guidelines",
                    size=20,
                    weight=ft.FontWeight.BOLD
                ),
                region,
                ft.TextButton(
                    content="See the KSI / U.S. Soccer region map",
                    url=KSI_MAP
                ),
                ft.Text(
                    "New locations default to Region 1. "
                    "Check the map to find your actual region. "
                    "School and state rules may be stricter.",
                    color="#64748B",
                    size=12
                )
            ],
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
    )

    return screen
