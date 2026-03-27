#!/usr/bin/env python3
"""Render-friendly web app for Kanagawa's weekly weather forecast."""

from __future__ import annotations

import html
import json
import os
import ssl
import sys
import threading
import time
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

FORECAST_URL = "https://www.jma.go.jp/bosai/forecast/data/forecast/140000.json"
OVERVIEW_URL = "https://www.jma.go.jp/bosai/forecast/data/overview_forecast/140000.json"
MAX_RESPONSE_BYTES = 1_000_000
USER_AGENT = "kanagawa-weather-web/1.0"
HOST = os.getenv("HOST", "0.0.0.0")


class ForecastError(RuntimeError):
    """Raised when the upstream JMA payload is unavailable or invalid."""


def read_float_env(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return float(raw_value)
    except ValueError as exc:
        raise ForecastError(f"{name} must be a number") from exc


def read_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ForecastError(f"{name} must be an integer") from exc


REQUEST_TIMEOUT_SECONDS = read_float_env("WEATHER_REQUEST_TIMEOUT_SECONDS", 10.0)
CACHE_TTL_SECONDS = read_int_env("WEATHER_CACHE_TTL_SECONDS", 900)
PORT = read_int_env("PORT", 8000)
COPYRIGHT_NOTICE = f"Copyright {datetime.now().year} Kanagawa Weekly Weather Viewer"

WEATHER_CODE_LABELS = {
    "100": "Sunny",
    "101": "Sunny, cloudy at times",
    "102": "Sunny, occasional rain",
    "103": "Sunny, rain at times",
    "104": "Sunny, occasional snow",
    "105": "Sunny, snow at times",
    "106": "Sunny, then rain",
    "107": "Sunny, then snow",
    "108": "Sunny, rain or snow",
    "110": "Sunny, later cloudy at times",
    "111": "Sunny, later cloudy",
    "112": "Sunny, later occasional rain",
    "113": "Sunny, later rain at times",
    "114": "Sunny, later rain",
    "115": "Sunny, later occasional snow",
    "116": "Sunny, later snow at times",
    "117": "Sunny, later snow",
    "119": "Sunny, later rain or thunderstorm",
    "120": "Sunny, brief rain morning or evening",
    "121": "Sunny, brief rain early",
    "122": "Sunny, brief rain in the evening",
    "123": "Sunny with mountain thunderstorms",
    "124": "Sunny with mountain snow",
    "125": "Sunny with afternoon thunderstorms",
    "126": "Sunny, rain from midday",
    "127": "Sunny, rain from evening",
    "128": "Sunny, rain at night",
    "130": "Fog early, then sunny",
    "131": "Sunny, fog before dawn",
    "132": "Sunny, cloudy morning and evening",
    "140": "Sunny, rain and thunder at times",
    "160": "Sunny, snow or rain briefly",
    "170": "Sunny, snow or rain at times",
    "181": "Sunny, later snow or rain",
    "200": "Cloudy",
    "201": "Cloudy, sunny at times",
    "202": "Cloudy, occasional rain",
    "203": "Cloudy, rain at times",
    "204": "Cloudy, occasional snow",
    "205": "Cloudy, snow at times",
    "206": "Cloudy, then rain",
    "207": "Cloudy, then snow",
    "208": "Cloudy, rain or snow",
    "209": "Cloudy, drizzle or mist",
    "210": "Cloudy, later sunny at times",
    "211": "Cloudy, later sunny",
    "212": "Cloudy, later occasional rain",
    "213": "Cloudy, later rain at times",
    "214": "Cloudy, later rain",
    "215": "Cloudy, later occasional snow",
    "216": "Cloudy, later snow at times",
    "217": "Cloudy, later snow",
    "218": "Cloudy, later rain or snow",
    "219": "Cloudy, later rain or thunderstorm",
    "220": "Cloudy, brief rain morning or evening",
    "221": "Cloudy, brief rain early",
    "222": "Cloudy, brief rain in the evening",
    "223": "Cloudy, some daytime sun",
    "224": "Cloudy, rain from midday",
    "225": "Cloudy, rain from evening",
    "226": "Cloudy, rain at night",
    "228": "Cloudy, snow from midday",
    "229": "Cloudy, snow from evening",
    "230": "Cloudy, snow at night",
    "231": "Cloudy with fog or drizzle on coasts",
    "240": "Cloudy, rain and thunder at times",
    "250": "Cloudy, snow and thunder at times",
    "260": "Cloudy, snow or rain briefly",
    "270": "Cloudy, snow or rain at times",
    "281": "Cloudy, later snow or rain",
    "300": "Rain",
    "301": "Rain, sunny at times",
    "302": "Rain, occasionally stopping",
    "303": "Rain, snow at times",
    "304": "Rain or snow",
    "306": "Heavy rain",
    "308": "Stormy rain",
    "309": "Rain, occasional snow",
    "311": "Rain, later sunny",
    "313": "Rain, later cloudy",
    "314": "Rain, later snow at times",
    "315": "Rain, later snow",
    "316": "Rain or snow, later sunny",
    "317": "Rain or snow, later cloudy",
    "320": "Rain early, then sunny",
    "321": "Rain early, then cloudy",
    "322": "Rain with occasional snow morning and evening",
    "323": "Rain, sunny from midday",
    "324": "Rain, sunny from evening",
    "325": "Rain, clear at night",
    "326": "Rain, snow from evening",
    "327": "Rain, snow at night",
    "328": "Rain, occasionally heavy",
    "329": "Rain, brief sleet",
    "340": "Snow or rain",
    "350": "Rain with thunder",
    "361": "Snow or rain, later sunny",
    "371": "Snow or rain, later cloudy",
    "400": "Snow",
    "401": "Snow, sunny at times",
    "402": "Snow, occasionally stopping",
    "403": "Snow, rain at times",
    "405": "Heavy snow",
    "406": "Snowstorm",
    "407": "Blizzard",
    "409": "Snow, occasional rain",
    "411": "Snow, later sunny",
    "413": "Snow, later cloudy",
    "414": "Snow, later rain",
    "420": "Snow early, then sunny",
    "421": "Snow early, then cloudy",
    "422": "Snow, rain from midday",
    "423": "Snow, rain from evening",
    "425": "Snow, occasionally heavy",
    "426": "Snow, later sleet",
    "427": "Snow, then rain at night",
    "450": "Snow with thunder",
}

DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

_CACHE: dict[str, Any] = {"data": None, "fetched_at": 0.0}
_CACHE_LOCK = threading.Lock()


def fetch_json(url: str) -> Any:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )

    try:
        with urlopen(
            request,
            timeout=REQUEST_TIMEOUT_SECONDS,
            context=ssl.create_default_context(),
        ) as response:
            if response.status != HTTPStatus.OK:
                raise ForecastError(f"Upstream returned {response.status} for {url}")

            payload = response.read(MAX_RESPONSE_BYTES + 1)
            if len(payload) > MAX_RESPONSE_BYTES:
                raise ForecastError(f"Upstream payload too large for {url}")

            encoding = response.headers.get_content_charset("utf-8")
            return json.loads(payload.decode(encoding))
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        raise ForecastError(f"Failed to fetch {url}: {exc}") from exc


def load_weather_snapshot(now: float | None = None) -> dict[str, Any]:
    current_time = now if now is not None else time.time()

    with _CACHE_LOCK:
        cached_data = _CACHE["data"]
        fetched_at = _CACHE["fetched_at"]
        if cached_data and current_time - fetched_at < CACHE_TTL_SECONDS:
            return cached_data

    forecast_payload = fetch_json(FORECAST_URL)
    overview_payload = fetch_json(OVERVIEW_URL)
    snapshot = build_view_model(forecast_payload, overview_payload)

    with _CACHE_LOCK:
        _CACHE["data"] = snapshot
        _CACHE["fetched_at"] = current_time

    return snapshot


def build_view_model(forecast_payload: Any, overview_payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(forecast_payload, list) or len(forecast_payload) < 2:
        raise ForecastError("Unexpected forecast payload structure")
    if not isinstance(overview_payload, dict):
        raise ForecastError("Unexpected overview payload structure")

    try:
        detailed = forecast_payload[0]
        weekly = forecast_payload[1]

        weekly_days = weekly["timeSeries"][0]
        weekly_temps = weekly["timeSeries"][1]
        daily_area = weekly_days["areas"][0]
        temp_area = weekly_temps["areas"][0]

        east_west_series = detailed["timeSeries"][0]
        pop_series = detailed["timeSeries"][1]
        temp_series = detailed["timeSeries"][2]

        east_west_weather = {}
        for area in east_west_series["areas"]:
            east_west_weather[area["area"]["name"]] = {
                "dates": east_west_series["timeDefines"],
                "weather_codes": area.get("weatherCodes", []),
                "weathers": area.get("weathers", []),
            }

        east_west_pops = {}
        for area in pop_series["areas"]:
            east_west_pops[area["area"]["name"]] = dict(
                zip(pop_series["timeDefines"], area.get("pops", []), strict=False)
            )

        local_temps = {}
        for area in temp_series["areas"]:
            local_temps[area["area"]["name"]] = dict(
                zip(temp_series["timeDefines"], area.get("temps", []), strict=False)
            )

        weekly_rows = []
        east = east_west_weather.get("東部", {})
        west = east_west_weather.get("西部", {})
        east_dates = {date[:10]: index for index, date in enumerate(east.get("dates", []))}
        west_dates = {date[:10]: index for index, date in enumerate(west.get("dates", []))}

        for index, raw_date in enumerate(weekly_days["timeDefines"]):
            date_key = raw_date[:10]
            east_label = None
            west_label = None

            if date_key in east_dates:
                east_index = east_dates[date_key]
                east_label = safe_get(east.get("weathers", []), east_index)
            if date_key in west_dates:
                west_index = west_dates[date_key]
                west_label = safe_get(west.get("weathers", []), west_index)

            if east_label and west_label:
                if east_label == west_label:
                    summary = east_label
                else:
                    summary = f"East: {east_label} / West: {west_label}"
            else:
                weather_code = safe_get(daily_area.get("weatherCodes", []), index, "-")
                summary = WEATHER_CODE_LABELS.get(
                    weather_code,
                    f"Weather code {weather_code}",
                )

            weekly_rows.append(
                {
                    "date": raw_date,
                    "label": format_date(raw_date),
                    "summary": summary,
                    "pop": safe_get(daily_area.get("pops", []), index, "-") or "-",
                    "reliability": safe_get(daily_area.get("reliabilities", []), index, "-") or "-",
                    "temp_min": safe_get(temp_area.get("tempsMin", []), index, "-") or "-",
                    "temp_max": safe_get(temp_area.get("tempsMax", []), index, "-") or "-",
                }
            )

        detail_cards = [
            build_region_card("East", east_west_weather.get("東部"), east_west_pops.get("東部", {})),
            build_region_card("West", east_west_weather.get("西部"), east_west_pops.get("西部", {})),
        ]

        city_cards = [
            build_city_card("Yokohama", local_temps.get("横浜", {})),
            build_city_card("Odawara", local_temps.get("小田原", {})),
        ]

        report_datetime = detailed.get("reportDatetime", "")
        published_at = format_timestamp(report_datetime)
        overview_text = overview_payload.get("text", "").strip()
    except (AttributeError, IndexError, KeyError, TypeError, ValueError) as exc:
        raise ForecastError("Unexpected forecast payload structure") from exc

    return {
        "publishing_office": detailed.get("publishingOffice", "Japan Meteorological Agency"),
        "published_at": published_at,
        "overview_text": overview_text,
        "weekly_rows": weekly_rows,
        "detail_cards": detail_cards,
        "city_cards": city_cards,
        "source_links": [
            {"label": "JMA forecast JSON", "url": FORECAST_URL},
            {"label": "JMA overview JSON", "url": OVERVIEW_URL},
        ],
    }


def build_region_card(title: str, weather_series: dict[str, Any] | None, pop_lookup: dict[str, str]) -> dict[str, Any]:
    items = []
    if weather_series:
        for raw_date, weather in zip(weather_series.get("dates", []), weather_series.get("weathers", []), strict=False):
            pop = pop_lookup.get(raw_date, "-") or "-"
            items.append(
                {
                    "label": format_date(raw_date),
                    "weather": weather,
                    "pop": pop,
                }
            )
    return {"title": title, "items": items}


def build_city_card(title: str, temp_lookup: dict[str, str]) -> dict[str, Any]:
    items = []
    for raw_date, temp in temp_lookup.items():
        items.append(
            {
                "label": format_timestamp(raw_date),
                "temp": temp or "-",
            }
        )
    return {"title": title, "items": items}


def format_date(raw_date: str) -> str:
    parsed = datetime.fromisoformat(raw_date)
    return f"{parsed:%Y-%m-%d} ({DAY_LABELS[parsed.weekday()]})"


def format_timestamp(raw_date: str) -> str:
    parsed = datetime.fromisoformat(raw_date)
    return f"{parsed:%Y-%m-%d %H:%M %Z}".strip()


def safe_get(items: list[Any], index: int, default: Any = "") -> Any:
    if 0 <= index < len(items):
        return items[index]
    return default


def render_page(snapshot: dict[str, Any]) -> str:
    headline = escape_text("Kanagawa 7-Day Forecast")
    office = escape_text(snapshot["publishing_office"])
    published_at = escape_text(snapshot["published_at"])
    overview_text = "<br>".join(escape_text(snapshot["overview_text"]).splitlines()) or "No overview available."
    copyright_notice = escape_text(COPYRIGHT_NOTICE)

    rows_html = "".join(
        """
        <tr>
          <td>{label}</td>
          <td>{summary}</td>
          <td>{pop}</td>
          <td>{temp_min}</td>
          <td>{temp_max}</td>
          <td>{reliability}</td>
        </tr>
        """.format(
            label=escape_text(row["label"]),
            summary=escape_text(row["summary"]),
            pop=escape_text(row["pop"]),
            temp_min=escape_text(row["temp_min"]),
            temp_max=escape_text(row["temp_max"]),
            reliability=escape_text(row["reliability"]),
        )
        for row in snapshot["weekly_rows"]
    )

    detail_html = "".join(render_region_card(card) for card in snapshot["detail_cards"])
    city_html = "".join(render_city_card(card) for card in snapshot["city_cards"])
    sources_html = "".join(
        '<li><a href="{url}" rel="noopener noreferrer">{label}</a></li>'.format(
            url=escape_attribute(source["url"]),
            label=escape_text(source["label"]),
        )
        for source in snapshot["source_links"]
    )

    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Kanagawa Weekly Weather</title>
    <style>
      :root {{
        --bg: #f3efe2;
        --panel: rgba(255, 252, 245, 0.88);
        --ink: #1f2a30;
        --accent: #0f766e;
        --accent-soft: #d0ece7;
        --line: rgba(31, 42, 48, 0.12);
        --shadow: 0 28px 56px rgba(31, 42, 48, 0.14);
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        min-height: 100vh;
        color: var(--ink);
        font-family: "Iowan Old Style", "Palatino Linotype", "Yu Mincho", serif;
        background:
          radial-gradient(circle at top left, rgba(15, 118, 110, 0.16), transparent 32%),
          linear-gradient(140deg, #f6f1e5 0%, #e2efe8 45%, #c7dce8 100%);
      }}
      a {{ color: inherit; }}
      .shell {{
        width: min(1120px, calc(100vw - 32px));
        margin: 0 auto;
        padding: 28px 0 40px;
      }}
      .hero {{
        padding: 32px;
        border-bottom: 1px solid var(--line);
      }}
      .eyebrow {{
        margin: 0 0 10px;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--accent);
        font-size: 0.78rem;
      }}
      h1 {{
        margin: 0;
        font-size: clamp(2.2rem, 6vw, 4.4rem);
        line-height: 0.95;
      }}
      .subtitle {{
        max-width: 48rem;
        margin-top: 18px;
        font-size: 1rem;
        line-height: 1.7;
      }}
      .panel {{
        backdrop-filter: blur(16px);
        background: var(--panel);
        border: 1px solid rgba(255, 255, 255, 0.75);
        border-radius: 24px;
        box-shadow: var(--shadow);
        overflow: hidden;
      }}
      .grid {{
        display: grid;
        grid-template-columns: 1.4fr 1fr;
        gap: 18px;
        margin-top: 18px;
      }}
      .stack {{
        display: grid;
        gap: 18px;
      }}
      .section {{
        padding: 26px 28px 28px;
      }}
      .section h2 {{
        margin: 0 0 14px;
        font-size: 1.2rem;
      }}
      .meta {{
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 18px;
      }}
      .badge {{
        padding: 10px 14px;
        background: var(--accent-soft);
        border-radius: 999px;
        font-size: 0.92rem;
      }}
      table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 0.95rem;
      }}
      th, td {{
        padding: 12px 10px;
        text-align: left;
        vertical-align: top;
        border-top: 1px solid var(--line);
      }}
      th {{
        color: rgba(31, 42, 48, 0.76);
        font-weight: 600;
      }}
      tbody tr:hover {{
        background: rgba(15, 118, 110, 0.05);
      }}
      .cards {{
        display: grid;
        gap: 16px;
      }}
      .mini-card {{
        padding: 18px;
        border: 1px solid var(--line);
        border-radius: 18px;
        background: rgba(255, 255, 255, 0.58);
      }}
      .mini-card h3 {{
        margin: 0 0 10px;
        font-size: 1rem;
      }}
      .mini-card ul {{
        margin: 0;
        padding-left: 18px;
        display: grid;
        gap: 8px;
      }}
      .sources ul {{
        margin: 0;
        padding-left: 20px;
        display: grid;
        gap: 8px;
      }}
      .footer {{
        margin-top: 18px;
        text-align: center;
        font-size: 0.85rem;
        color: rgba(31, 42, 48, 0.72);
      }}
      @media (max-width: 860px) {{
        .grid {{
          grid-template-columns: 1fr;
        }}
        .hero {{
          padding: 26px 24px;
        }}
        .section {{
          padding: 24px 20px;
        }}
        table, thead, tbody, tr, th, td {{
          display: block;
        }}
        thead {{
          display: none;
        }}
        tbody tr {{
          padding: 10px 0;
          border-top: 1px solid var(--line);
        }}
        td {{
          border: 0;
          padding: 6px 0;
        }}
        td::before {{
          display: inline-block;
          min-width: 108px;
          font-weight: 700;
          color: rgba(31, 42, 48, 0.72);
        }}
        td:nth-child(1)::before {{ content: "Date"; }}
        td:nth-child(2)::before {{ content: "Forecast"; }}
        td:nth-child(3)::before {{ content: "Rain %"; }}
        td:nth-child(4)::before {{ content: "Low"; }}
        td:nth-child(5)::before {{ content: "High"; }}
        td:nth-child(6)::before {{ content: "Reliability"; }}
      }}
    </style>
  </head>
  <body>
    <main class="shell">
      <section class="panel hero">
        <p class="eyebrow">Kanagawa Prefecture</p>
        <h1>{headline}</h1>
        <p class="subtitle">{overview_text}</p>
        <div class="meta">
          <span class="badge">Source: {office}</span>
          <span class="badge">Updated: {published_at}</span>
        </div>
      </section>
      <section class="grid">
        <div class="panel section">
          <h2>Weekly outlook</h2>
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Forecast</th>
                <th>Rain %</th>
                <th>Low</th>
                <th>High</th>
                <th>Reliability</th>
              </tr>
            </thead>
            <tbody>
              {rows_html}
            </tbody>
          </table>
        </div>
        <div class="stack">
          <section class="panel section">
            <h2>Near-term regional detail</h2>
            <div class="cards">{detail_html}</div>
          </section>
          <section class="panel section">
            <h2>City temperature snapshots</h2>
            <div class="cards">{city_html}</div>
          </section>
          <section class="panel section sources">
            <h2>Source endpoints</h2>
            <ul>{sources_html}</ul>
          </section>
        </div>
      </section>
      <footer class="footer">{copyright_notice}</footer>
    </main>
  </body>
</html>
"""


def render_region_card(card: dict[str, Any]) -> str:
    items = "".join(
        "<li>{label}: {weather} (Rain {pop}%)</li>".format(
            label=escape_text(item["label"]),
            weather=escape_text(item["weather"]),
            pop=escape_text(item["pop"]),
        )
        for item in card["items"]
    )
    return (
        '<article class="mini-card"><h3>{title}</h3><ul>{items}</ul></article>'.format(
            title=escape_text(card["title"]),
            items=items,
        )
    )


def render_city_card(card: dict[str, Any]) -> str:
    items = "".join(
        "<li>{label}: {temp}C</li>".format(
            label=escape_text(item["label"]),
            temp=escape_text(item["temp"]),
        )
        for item in card["items"]
    )
    return (
        '<article class="mini-card"><h3>{title}</h3><ul>{items}</ul></article>'.format(
            title=escape_text(card["title"]),
            items=items,
        )
    )


def escape_text(value: Any) -> str:
    return html.escape(str(value), quote=False)


def escape_attribute(value: Any) -> str:
    return html.escape(str(value), quote=True)


class WeatherHandler(BaseHTTPRequestHandler):
    server_version = "KanagawaWeather"

    def version_string(self) -> str:
        return self.server_version

    def do_GET(self) -> None:  # noqa: N802
        self._handle_request(include_body=True)

    def do_HEAD(self) -> None:  # noqa: N802
        self._handle_request(include_body=False)

    def _handle_request(self, include_body: bool) -> None:
        if self.path == "/":
            self.serve_index(include_body=include_body)
            return

        if self.path == "/healthz":
            try:
                load_weather_snapshot()
            except ForecastError:
                self.send_response(HTTPStatus.SERVICE_UNAVAILABLE)
                self._set_common_headers("application/json; charset=utf-8")
                self.end_headers()
                if include_body:
                    self.wfile.write(b'{"status":"degraded"}')
                return

            self.send_response(HTTPStatus.OK)
            self._set_common_headers("application/json; charset=utf-8")
            self.end_headers()
            if include_body:
                self.wfile.write(b'{"status":"ok"}')
            return

        if self.path == "/favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return

        body = render_not_found_page().encode("utf-8")
        self.send_response(HTTPStatus.NOT_FOUND)
        self._set_common_headers("text/html; charset=utf-8")
        self.end_headers()
        if include_body:
            self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def serve_index(self, include_body: bool) -> None:
        try:
            snapshot = load_weather_snapshot()
            document = render_page(snapshot).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self._set_common_headers("text/html; charset=utf-8")
            self.end_headers()
            if include_body:
                self.wfile.write(document)
        except ForecastError as exc:
            print(f"Weather fetch failed: {exc}", file=sys.stderr, flush=True)
            body = render_error_page().encode("utf-8")
            self.send_response(HTTPStatus.BAD_GATEWAY)
            self._set_common_headers("text/html; charset=utf-8")
            self.end_headers()
            if include_body:
                self.wfile.write(body)

    def _set_common_headers(self, content_type: str) -> None:
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; img-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")


def render_error_page() -> str:
    copyright_notice = escape_text(COPYRIGHT_NOTICE)
    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Weather unavailable</title>
    <style>
      body {{
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        background: linear-gradient(160deg, #f8efe7 0%, #e2edf0 100%);
        color: #1f2a30;
        font-family: "Iowan Old Style", "Palatino Linotype", "Yu Mincho", serif;
      }}
      article {{
        width: min(640px, calc(100vw - 32px));
        padding: 28px;
        border-radius: 24px;
        background: rgba(255, 252, 245, 0.88);
        box-shadow: 0 22px 50px rgba(31, 42, 48, 0.14);
      }}
      .legal {{
        margin-top: 18px;
        font-size: 0.9rem;
        color: rgba(31, 42, 48, 0.7);
      }}
    </style>
  </head>
  <body>
    <article>
      <h1>Weather data unavailable</h1>
      <p>Weather data could not be loaded from the upstream provider.</p>
      <p>Try again in a few minutes.</p>
      <p class="legal">{copyright_notice}</p>
    </article>
  </body>
</html>
"""


def render_not_found_page() -> str:
    copyright_notice = escape_text(COPYRIGHT_NOTICE)
    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Not found</title>
    <style>
      body {{
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        background: linear-gradient(160deg, #f8efe7 0%, #e2edf0 100%);
        color: #1f2a30;
        font-family: "Iowan Old Style", "Palatino Linotype", "Yu Mincho", serif;
      }}
      article {{
        width: min(640px, calc(100vw - 32px));
        padding: 28px;
        border-radius: 24px;
        background: rgba(255, 252, 245, 0.88);
        box-shadow: 0 22px 50px rgba(31, 42, 48, 0.14);
      }}
      .legal {{
        margin-top: 18px;
        font-size: 0.9rem;
        color: rgba(31, 42, 48, 0.7);
      }}
    </style>
  </head>
  <body>
    <article>
      <p>Not found.</p>
      <p class="legal">{copyright_notice}</p>
    </article>
  </body>
</html>
"""


def run_server() -> None:
    server = ThreadingHTTPServer((HOST, PORT), WeatherHandler)
    print(f"Serving Kanagawa weather on http://{HOST}:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    run_server()
