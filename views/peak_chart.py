"Today's WBGT as a smooth curve from 6 AM to 10 PM, drawn as SVG."

from math import ceil, floor

START_HOUR = 6
END_HOUR = 22

ORDER = ("green", "yellow", "orange", "red", "black")

#light band behind each category
BAND_COLORS = {
    "green": "#E5F5E9",
    "yellow": "#FFF4CC",
    "orange": "#FFE4D2",
    "red": "#FCE0E0",
    "black": "#D5DBE5"
}

#line, dot and label color for each category
LINE_COLORS = {
    "green": "#16A34A",
    "yellow": "#CA8A04",
    "orange": "#EA580C",
    "red": "#DC2626",
    "black": "#111827"
}

MUTED = "#64748B"

#drawing area inside the SVG, about one inch tall on screen
WIDTH, HEIGHT = 320, 100
LEFT, RIGHT, TOP, BOTTOM = 28, 306, 18, 80


def to_f(celsius):
    return celsius * 9 / 5 + 32


def hour_label(hour):
    suffix = "am" if hour < 12 else "pm"
    return f"{hour % 12 or 12}{suffix}"


def sign(value):
    return (value > 0) - (value < 0)


def smooth_path(points):
    "monotone cubic curve through the points, so it never overshoots a reading"

    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    count = len(points)

    gaps = [xs[i + 1] - xs[i] for i in range(count - 1)]
    slopes = [(ys[i + 1] - ys[i]) / gaps[i] for i in range(count - 1)]

    tangents = [0.0] * count

    for i in range(1, count - 1):
        before, after = slopes[i - 1], slopes[i]
        blend = (before * gaps[i] + after * gaps[i - 1]) / (gaps[i - 1] + gaps[i])
        tangents[i] = (sign(before) + sign(after)) * min(
            abs(before), abs(after), 0.5 * abs(blend)
        )

    tangents[0] = (3 * slopes[0] - tangents[1]) / 2 if count > 2 else slopes[0]
    tangents[-1] = (3 * slopes[-1] - tangents[-2]) / 2 if count > 2 else slopes[-1]

    path = [f"M{xs[0]:.1f},{ys[0]:.1f}"]

    for i in range(count - 1):
        step = gaps[i] / 3
        path.append(
            f"C{xs[i] + step:.1f},{ys[i] + tangents[i] * step:.1f} "
            f"{xs[i + 1] - step:.1f},{ys[i + 1] - tangents[i + 1] * step:.1f} "
            f"{xs[i + 1]:.1f},{ys[i + 1]:.1f}"
        )

    return " ".join(path)


def build_peak_chart(hourly, thresholds_f, now=None):
    "return SVG bytes and a short description of today's curve"

    points = [
        (item["time"].hour, to_f(item["wbgt"]), item["category"])
        for item in hourly
        if START_HOUR <= item["time"].hour <= END_HOUR
    ]

    if len(points) < 2:
        raise ValueError("Not enough hours to draw today's chart")

    values = [value for _, value, _ in points]

    #pad the range so the curve never touches the edges
    low = min(values) - 2
    high = max(values) + 2

    if high - low < 10:
        middle = (high + low) / 2
        low, high = middle - 5, middle + 5

    low, high = floor(low), ceil(high)

    def x_at(hour):
        return LEFT + (hour - START_HOUR) / (END_HOUR - START_HOUR) * (RIGHT - LEFT)

    def y_at(value):
        return BOTTOM - (value - low) / (high - low) * (BOTTOM - TOP)

    #category ranges in °F, clipped to the chart
    bands = []

    for index, name in enumerate(ORDER):
        start = thresholds_f[name] if name != "green" else float("-inf")
        end = (
            thresholds_f[ORDER[index + 1]]
            if index + 1 < len(ORDER) else float("inf")
        )

        start, end = max(start, low), min(end, high)

        if start < end:
            bands.append((name, start, end))

    shapes = []

    for name, start, end in bands:
        top, bottom = y_at(end), y_at(start)

        shapes.append(
            f'<rect x="{LEFT}" y="{top:.1f}" width="{RIGHT - LEFT}" '
            f'height="{bottom - top:.1f}" fill="{BAND_COLORS[name]}"/>'
        )

    #time grid every two hours
    for hour in range(START_HOUR, END_HOUR + 1, 2):
        x = x_at(hour)

        shapes.append(
            f'<line x1="{x:.1f}" y1="{TOP}" x2="{x:.1f}" y2="{BOTTOM}" '
            f'stroke="#FFFFFF" stroke-width="1"/>'
        )
        shapes.append(
            f'<text x="{x:.1f}" y="{BOTTOM + 13}" font-size="9" '
            f'text-anchor="middle" fill="{MUTED}">{hour_label(hour)}</text>'
        )

    #temperature labels at the category cutoffs
    labels = [low, high] + [
        cutoff for cutoff in thresholds_f.values() if low < cutoff < high
    ]
    placed = []

    for value in sorted(labels, key=lambda v: v in (low, high)):
        y = y_at(value)

        if any(abs(y - other) < 10 for other in placed):
            continue

        placed.append(y)
        shapes.append(
            f'<text x="{LEFT - 3}" y="{y + 3:.1f}" font-size="9" '
            f'text-anchor="end" fill="{MUTED}">{value:.0f}°</text>'
        )

    #line color changes exactly where the curve crosses a cutoff
    stops = []

    for name, start, end in bands:
        color = LINE_COLORS[name]
        stops.append(f'<stop offset="{(start - low) / (high - low):.4f}" stop-color="{color}"/>')
        stops.append(f'<stop offset="{(end - low) / (high - low):.4f}" stop-color="{color}"/>')

    coords = [(x_at(hour), y_at(value)) for hour, value, _ in points]
    curve = smooth_path(coords)

    shapes.append(
        f'<path d="{curve}" fill="none" stroke="url(#heat)" '
        f'stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>'
    )

    for (x, y), (_, _, name) in zip(coords, points):
        shapes.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.2" fill="{LINE_COLORS[name]}" '
            f'stroke="#FFFFFF" stroke-width="1"/>'
        )

    #current time marker
    if now is not None:
        hour_now = now.hour + now.minute / 60

        if START_HOUR <= hour_now <= END_HOUR:
            x = x_at(hour_now)

            shapes.append(
                f'<line x1="{x:.1f}" y1="{TOP}" x2="{x:.1f}" y2="{BOTTOM}" '
                f'stroke="#334155" stroke-width="1.2" stroke-dasharray="4 3"/>'
            )
            shapes.append(
                f'<text x="{x + 3:.1f}" y="{BOTTOM - 3}" font-size="8.5" '
                f'fill="#334155">Now</text>'
            )

    #peak marker and label
    peak_index = max(range(len(points)), key=lambda i: points[i][1])
    peak_hour, peak_value, peak_name = points[peak_index]
    peak_x, peak_y = coords[peak_index]
    label_x = min(max(peak_x, LEFT + 46), RIGHT - 46)

    shapes.append(
        f'<circle cx="{peak_x:.1f}" cy="{peak_y:.1f}" r="4.5" '
        f'fill="{LINE_COLORS[peak_name]}" stroke="#FFFFFF" stroke-width="1.5"/>'
    )
    shapes.append(
        f'<text x="{label_x:.1f}" y="{max(peak_y - 8, 10):.1f}" font-size="10" '
        f'font-weight="bold" text-anchor="middle" fill="{LINE_COLORS[peak_name]}">'
        f'Peak {peak_value:.1f}°F · {hour_label(peak_hour)}</text>'
    )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" '
        f'width="{WIDTH}" height="{HEIGHT}" font-family="Roboto, sans-serif">'
        f'<defs><linearGradient id="heat" gradientUnits="userSpaceOnUse" '
        f'x1="0" y1="{BOTTOM}" x2="0" y2="{TOP}">{"".join(stops)}</linearGradient></defs>'
        f'{"".join(shapes)}'
        f'<line x1="{LEFT}" y1="{BOTTOM}" x2="{RIGHT}" y2="{BOTTOM}" stroke="#CBD5E1" stroke-width="1"/>'
        f'</svg>'
    )

    description = (
        f"Estimated WBGT from 6 AM to 10 PM. Peak {peak_value:.1f} °F "
        f"at {hour_label(peak_hour)}, {peak_name} category."
    )

    return svg.encode(), description
