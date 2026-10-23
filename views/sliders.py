"Sliders drawn over a colored bar, shared by the simulator and the plan screen."

import flet as ft

DARK = "#172033"
MUTED = "#64748B"

#space between the slider ends and the edge of the colored bar
TRACK_INSET = 12


def side_gradient(colors, stops=None):
    return ft.LinearGradient(
        begin=ft.Alignment.CENTER_LEFT,
        end=ft.Alignment.CENTER_RIGHT,
        colors=colors,
        stops=stops
    )


def slider_block(title, slider, ticks, gradient=None):
    "title and value, the slider over a colored bar, and labels under it"

    value = ft.Text("", size=14, weight=ft.FontWeight.BOLD, color=DARK)

    bar = ft.Container(
        height=10,
        border_radius=5,
        margin=ft.Margin.symmetric(horizontal=TRACK_INSET),
        bgcolor="#E2E8F0" if gradient is None else None,
        gradient=gradient
    )

    #the bar shows through the see-through track
    slider.active_color = ft.Colors.TRANSPARENT
    slider.inactive_color = ft.Colors.TRANSPARENT
    slider.thumb_color = "#FFFFFF"
    slider.year_2023 = True
    slider.padding = ft.Padding.symmetric(horizontal=TRACK_INSET)

    block = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.Text(title, size=14, color=MUTED),
                    value
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                wrap=True
            ),
            ft.Stack(
                controls=[bar, slider],
                alignment=ft.Alignment.CENTER
            ),
            ft.Container(
                padding=ft.Padding.symmetric(horizontal=TRACK_INSET - 6),
                content=ft.Row(
                    controls=[
                        ft.Text(tick, size=11, color=MUTED)
                        for tick in ticks
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                )
            )
        ],
        spacing=4,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH
    )

    return block, value, bar
