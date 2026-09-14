#!/usr/bin/env python3
import json
import os
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from html import escape

USERNAME = "Shadorux"
OUTPUT = "language-stats.svg"
TOKEN = os.environ.get("GITHUB_TOKEN", "")

HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "Shadorux-language-stats",
    "X-GitHub-Api-Version": "2022-11-28",
}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"


def api_get(url):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def public_repositories():
    repos = []
    page = 1
    while True:
        query = urllib.parse.urlencode({
            "per_page": 100,
            "page": page,
            "type": "owner",
            "sort": "updated",
        })
        batch = api_get(f"https://api.github.com/users/{USERNAME}/repos?{query}")
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return [repo for repo in repos if not repo.get("fork") and not repo.get("archived")]


def collect_languages(repos):
    totals = Counter()
    scanned = 0
    for repo in repos:
        try:
            languages = api_get(repo["languages_url"])
        except Exception as exc:
            print(f"Skipping {repo['full_name']}: {exc}")
            continue
        if languages:
            scanned += 1
        for language, byte_count in languages.items():
            totals[language] += int(byte_count)
    return totals, scanned


def human_bytes(value):
    value = float(value)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024


def build_svg(totals, repo_count):
    ranked = totals.most_common()
    total_bytes = sum(totals.values())
    top = ranked[:8]
    other_bytes = sum(value for _, value in ranked[8:])
    if other_bytes:
        top.append(("Other", other_bytes))

    row_height = 39
    width = 760
    height = 150 + max(len(top), 1) * row_height + 55
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    shades = ["#ff1a1a", "#ee1010", "#d90b0b", "#c20707", "#a90505", "#8f0303", "#760202", "#5e0202", "#444444"]

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" rx="14" fill="#050505"/>',
        '<rect x="1" y="1" width="758" height="100%" rx="13" fill="none" stroke="#2f333a"/>',
        '<rect x="28" y="24" width="5" height="54" rx="2" fill="#ff0000"/>',
        '<text x="50" y="47" fill="#ff2020" font-family="Segoe UI,Arial,sans-serif" font-size="14" font-weight="700" letter-spacing="2">CHAOS ARSENAL // LIVE</text>',
        '<text x="50" y="76" fill="#ffffff" font-family="Segoe UI,Arial,sans-serif" font-size="25" font-weight="700">CURRENT CODE LANGUAGE DISTRIBUTION</text>',
        f'<text x="50" y="101" fill="#8b949e" font-family="Segoe UI,Arial,sans-serif" font-size="12">GitHub Linguist bytes across {repo_count} public, non-fork repositories</text>',
    ]

    if not top or total_bytes == 0:
        lines.append('<text x="50" y="155" fill="#ffffff" font-family="Segoe UI,Arial,sans-serif" font-size="16">No language data found.</text>')
    else:
        y = 142
        bar_x = 210
        bar_width = 430
        for index, (language, byte_count) in enumerate(top):
            pct = byte_count / total_bytes * 100
            shade = shades[min(index, len(shades) - 1)]
            fill_width = max(2, bar_width * pct / 100)
            name = escape(language)
            lines.extend([
                f'<text x="50" y="{y + 14}" fill="#f0f0f0" font-family="Segoe UI,Arial,sans-serif" font-size="14" font-weight="600">{name}</text>',
                f'<rect x="{bar_x}" y="{y}" width="{bar_width}" height="14" rx="7" fill="#17191d"/>',
                f'<rect x="{bar_x}" y="{y}" width="{fill_width:.1f}" height="14" rx="7" fill="{shade}"/>',
                f'<text x="{bar_x + bar_width + 14}" y="{y + 12}" fill="#ffffff" font-family="Consolas,monospace" font-size="12">{pct:5.1f}%</text>',
                f'<text x="50" y="{y + 30}" fill="#6e7681" font-family="Consolas,monospace" font-size="10">{human_bytes(byte_count)}</text>',
            ])
            y += row_height

    lines.extend([
        f'<text x="50" y="{height - 24}" fill="#6e7681" font-family="Consolas,monospace" font-size="10">GENERATED {now} · SOURCE: GITHUB / LANGUAGES API</text>',
        '</svg>',
    ])
    return "\n".join(lines) + "\n"


def main():
    repos = public_repositories()
    totals, scanned = collect_languages(repos)
    svg = build_svg(totals, scanned)
    with open(OUTPUT, "w", encoding="utf-8") as handle:
        handle.write(svg)
    print(f"Generated {OUTPUT}: {len(totals)} languages across {scanned} repositories.")


if __name__ == "__main__":
    main()
