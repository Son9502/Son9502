"""Refreshes the README greeting (by time of day) and regenerates the travel map."""

import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
DATA = ROOT / "scripts" / "data"
MAP_SVG = ROOT / "assets" / "world-map.svg"
TIMEZONE = "America/Los_Angeles"

GREETINGS = [
    (5, 12, "Ẹ káàárọ̀", "Good morning"),
    (12, 17, "Ẹ káàsán", "Good afternoon"),
    (17, 21, "Ẹ káalẹ́", "Good evening"),
]
NIGHT = ("Ẹ kú alẹ́", "Good night")

# Countries too small for the 110m dataset, drawn as dots: code -> (lat, lon)
MARKERS = {"ABW": (12.5, -70.0), "HKG": (22.3, 114.2)}

VISITED_COLOR = "#2ea043"
WISHLIST_COLOR = "#f0883e"
BASE_COLOR = "#aab4be"


def greeting(now: datetime) -> tuple[str, str]:
    for start, end, yoruba, english in GREETINGS:
        if start <= now.hour < end:
            return yoruba, english
    return NIGHT


def typing_url(lines: list[str]) -> str:
    query = ";".join(quote_plus(line) for line in lines)
    return (
        "https://readme-typing-svg.demolab.com?font=Calibri&color=6E7781&size=28&pause=1500"
        "&center=true&vCenter=true&multiline=true&repeat=false&width=500&height=90"
        f"&lines={query}"
    )


def update_greeting() -> None:
    now = datetime.now(ZoneInfo(TIMEZONE))
    yoruba, english = greeting(now)
    block = (
        "<!-- GREETING:START -->\n"
        f'<p align="center"><img src="{typing_url([yoruba, f"({english})"])}" '
        f'alt="{yoruba} ({english})"></p>\n'
        "<!-- GREETING:END -->"
    )
    text = README.read_text(encoding="utf-8")
    text = re.sub(
        r"<!-- GREETING:START -->.*?<!-- GREETING:END -->",
        lambda _: block,
        text,
        flags=re.S,
    )
    README.write_text(text, encoding="utf-8")


def project(lon: float, lat: float, width: int, height: int) -> tuple[float, float]:
    return (lon + 180) / 360 * width, (85 - lat) / 145 * height


def ring_path(ring: list, width: int, height: int) -> str:
    points = [project(lon, lat, width, height) for lon, lat in ring]
    return "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in points) + "Z"


def build_map() -> None:
    width, height = 1000, 403
    countries = json.loads((DATA / "countries.json").read_text(encoding="utf-8"))
    visited, wishlist = set(countries["visited"]), set(countries["wishlist"])
    geo = json.loads((DATA / "countries.geojson").read_text(encoding="utf-8"))

    paths, drawn = [], set()
    for feature in geo["features"]:
        code = feature["properties"]["ADM0_A3"]
        if code == "ATA":
            continue
        drawn.add(code)
        color = (
            VISITED_COLOR if code in visited
            else WISHLIST_COLOR if code in wishlist
            else BASE_COLOR
        )
        geometry = feature["geometry"]
        polygons = (
            [geometry["coordinates"]]
            if geometry["type"] == "Polygon"
            else geometry["coordinates"]
        )
        d = "".join(ring_path(ring, width, height) for poly in polygons for ring in poly)
        paths.append(f'<path d="{d}" fill="{color}" stroke="#ffffff" stroke-width="0.4"/>')

    dots = []
    for code in (visited | wishlist) - drawn:
        if code in MARKERS:
            x, y = project(MARKERS[code][1], MARKERS[code][0], width, height)
            color = VISITED_COLOR if code in visited else WISHLIST_COLOR
            dots.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{color}" '
                'stroke="#ffffff" stroke-width="1"/>'
            )

    legend = (
        f'<rect x="12" y="{height - 62}" width="12" height="12" fill="{VISITED_COLOR}"/>'
        f'<text x="30" y="{height - 52}" font-size="13" font-family="sans-serif" fill="#57606a">'
        f"Visited ({len(visited)})</text>"
        f'<rect x="12" y="{height - 42}" width="12" height="12" fill="{WISHLIST_COLOR}"/>'
        f'<text x="30" y="{height - 32}" font-size="13" font-family="sans-serif" fill="#57606a">'
        f"Want to visit ({len(wishlist)})</text>"
    )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        'role="img" aria-label="World map of countries visited and wishlist">'
        + "".join(paths) + "".join(dots) + legend + "</svg>\n"
    )
    MAP_SVG.write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    update_greeting()
    build_map()
