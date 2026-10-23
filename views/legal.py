"Safety disclaimer, privacy notice, terms and credits, shown on first launch and in Settings."

import flet as ft

from views.brand import LOGO

DARK = "#172033"
MUTED = "#64748B"
BRAND_ORANGE = "#EA580C"

EFFECTIVE = "2026"

#fill these in to show a contact line and a governing-law clause
CONTACT_EMAIL = ""
GOVERNING_STATE = ""

SAFETY = (
    "FirstHeat is an educational planning tool, not medical advice. "
    "WBGT values are estimates from weather forecasts, not on-site "
    "measurements, and may be wrong. Plans and “lower-heat windows” "
    "are not a guarantee of safety or permission to exercise or work. "
    "Always follow your athletic trainer, coach, school, league, employer "
    "and official guidance (CDC, NATA/KSI, OSHA/NIOSH), which may be "
    "stricter. Stop activity and seek help if anyone shows signs of heat "
    "illness. In an emergency, call 911 first. This app does not contact "
    "emergency services."
)

PRIVACY = [
    ("What we collect", "Nothing that identifies you. There are no accounts, names or emails."),
    ("Stored on your device", "Your city, region, activity profile and the days you log. "
     "Delete them with Reset on My Plan or by clearing your browser data."),
    ("While you use the app", "What you enter is processed on our server to run the app "
     "and is not saved. The emergency log is never saved or sent anywhere."),
    ("Shared with", "Open-Meteo receives your city search and its coordinates to provide "
     "weather. Our host, Vercel, keeps standard short-term server logs (such as IP addresses)."),
    ("We don't", "Sell data, show ads, or use tracking or analytics."),
    ("Kids", "Intended for ages 13+ or use with a parent, coach or teacher. "
     "Don't enter names or health details."),
    ("Changes", "If this notice changes, the effective date below will change too.")
]

TERMS = [
    "FirstHeat is free and provided “as is,” without warranties of any kind.",
    "You use it at your own risk. FirstHeat and its creator are not liable for "
    "decisions made using the app.",
    "You are responsible for following your own safety rules, your school, league "
    "or employer policies, and official guidance.",
    "Weather data comes from Open-Meteo under CC BY 4.0. Heat guidance belongs to "
    "its publishers.",
    "The app may change or stop at any time."
]

#name, what it is, license, link
CREDITS = [
    ("Open-Meteo", "Weather data", "CC BY 4.0", "https://open-meteo.com/"),
    ("lwbgt", "WBGT calculation (Liljegren method)",
     "Apache-2.0, includes UChicago Argonne WBGT code", "https://pypi.org/project/lwbgt/"),
    ("Flet", "App framework", "Apache-2.0", "https://flet.dev/"),
    ("unDraw", "Activity illustrations", "unDraw license, free to use", "https://undraw.co/"),
    ("KSI / U.S. Soccer", "Regional heat guidelines", "Published guidance",
     "https://www.recognizetorecover.org/s/Heat-Guidelines.pdf"),
    ("NATA", "Preseason heat acclimatization", "Published guidance",
     "https://pmc.ncbi.nlm.nih.gov/articles/PMC2681206/"),
    ("CDC / NIOSH", "Worker acclimatization and heat illness", "Published guidance",
     "https://www.cdc.gov/niosh/heat-stress/recommendations/acclimatization.html"),
    ("OSHA", "Worker heat screening table", "Published guidance",
     "https://www.osha.gov/heat-exposure/hazards")
]


def terms_list():
    items = list(TERMS)

    if GOVERNING_STATE:
        items.append(f"These terms are governed by the laws of {GOVERNING_STATE}.")

    return items


def body(text, size=14, color=DARK):
    return ft.Text(text, size=size, color=color)


def bullet(text):
    return ft.Row(
        controls=[
            ft.Text("•", size=14, color=MUTED),
            ft.Text(text, size=14, color=DARK, expand=True)
        ],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.START
    )


def labeled(label, text):
    return ft.Text(
        spans=[
            ft.TextSpan(f"{label}: ", style=ft.TextStyle(weight=ft.FontWeight.BOLD)),
            ft.TextSpan(text)
        ],
        size=14,
        color=DARK
    )


def footer_lines():
    lines = [body(f"Effective {EFFECTIVE}", 12, MUTED)]

    if CONTACT_EMAIL:
        lines.insert(0, body(f"Contact: {CONTACT_EMAIL}", 12, MUTED))

    return lines


def section_tile(icon, title, controls):
    "one collapsible part of About & legal"

    return ft.ExpansionTile(
        title=ft.Text(title, size=16, weight=ft.FontWeight.W_600, color=DARK),
        leading=ft.Icon(icon, color=BRAND_ORANGE),
        controls_padding=ft.Padding.only(left=16, right=16, bottom=14),
        expanded_cross_axis_alignment=ft.CrossAxisAlignment.START,
        controls=[
            ft.Column(
                controls=controls,
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH
            )
        ]
    )


def about_section():
    "About & legal controls for the Settings screen"

    credits = [
        ft.Column(
            controls=[
                ft.TextButton(
                    content=name,
                    icon=ft.Icons.OPEN_IN_NEW,
                    url=url,
                    style=ft.ButtonStyle(padding=ft.Padding.symmetric(horizontal=4))
                ),
                body(f"{what} · {license_text}", 12, MUTED)
            ],
            spacing=0
        )
        for name, what, license_text, url in CREDITS
    ]

    return [
        ft.Text("About & legal", size=20, weight=ft.FontWeight.BOLD),
        section_tile(ft.Icons.HEALTH_AND_SAFETY_OUTLINED, "Safety disclaimer", [body(SAFETY)]),
        section_tile(
            ft.Icons.PRIVACY_TIP_OUTLINED,
            "Privacy notice",
            [labeled(label, text) for label, text in PRIVACY] + footer_lines()
        ),
        section_tile(
            ft.Icons.GAVEL,
            "Terms of use",
            [bullet(text) for text in terms_list()] + footer_lines()
        ),
        section_tile(ft.Icons.COPYRIGHT, "Licenses & credits", credits)
    ]


def disclaimer_dialog(on_accept):
    "first-launch safety notice; it stays until accepted"

    return ft.AlertDialog(
        modal=True,
        title=ft.Row(
            controls=[
                ft.Image(src=LOGO, width=36, height=36),
                ft.Text("Before you start", size=20, weight=ft.FontWeight.BOLD, color=DARK)
            ],
            spacing=10
        ),
        content=ft.Container(
            width=440,
            content=ft.Column(
                controls=[
                    body(SAFETY),
                    body(
                        "Privacy in short: no accounts, nothing that identifies you, "
                        "and your plan stays on your device. Weather requests go to "
                        "Open-Meteo.",
                        13,
                        MUTED
                    ),
                    body(
                        "The full Privacy notice and Terms of use are in "
                        "Settings, under About & legal. By continuing, you agree to them.",
                        13,
                        MUTED
                    )
                ],
                spacing=12,
                tight=True
            )
        ),
        #scrolls only when the text doesn't fit the screen
        scrollable=True,
        actions=[
            ft.FilledButton(
                content="I understand",
                icon=ft.Icons.CHECK,
                on_click=on_accept,
                style=ft.ButtonStyle(bgcolor=BRAND_ORANGE, color="#FFFFFF")
            )
        ],
        actions_alignment=ft.MainAxisAlignment.END
    )
