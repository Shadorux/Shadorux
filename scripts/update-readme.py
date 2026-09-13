import json
import os
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

USER = "Shadorux"
LASTFM_USER = "ultlifeform_"
README = Path("README.md")


def get_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def gh(path):
    token = os.getenv("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "shadorux-readme"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return get_json(f"https://api.github.com{path}", headers)


def replace_block(text, name, body):
    start = f"<!-- {name}:START -->"
    end = f"<!-- {name}:END -->"
    before, rest = text.split(start, 1)
    _, after = rest.split(end, 1)
    return before + start + "\n" + body.rstrip() + "\n" + end + after


def language_data(repos):
    totals = Counter()
    for repo in repos:
        if repo.get("fork") or repo.get("archived"):
            continue
        try:
            for lang, count in gh(f"/repos/{USER}/{repo['name']}/languages").items():
                totals[lang] += count
        except Exception:
            pass
    total = sum(totals.values()) or 1
    return [(lang, count / total * 100) for lang, count in totals.most_common(6)]


def bar(pct, width=22):
    n = max(0, min(width, round(pct / 100 * width)))
    return "█" * n + "░" * (width - n)


def main():
    repos = gh(f"/users/{USER}/repos?per_page=100&sort=updated")
    langs = language_data(repos)
    recent = next((r for r in repos if r["name"].lower() != USER.lower()), repos[0])
    try:
        commit = gh(f"/repos/{USER}/{recent['name']}/commits?per_page=1")[0]
        msg = commit["commit"]["message"].splitlines()[0][:64]
        stamp = commit["commit"]["committer"]["date"][:10]
    except Exception:
        msg, stamp = "telemetry unavailable", "---- -- --"

    shadow_repos = [r for r in repos if "shadow" in (r["name"] + " " + (r.get("description") or "")).lower()]
    lang_lines = "\n".join(f"{lang[:13]:13} {bar(pct)} {pct:5.1f}%" for lang, pct in langs)
    system = f"""```text
SHADORUX // SYSTEM STATUS
────────────────────────────────────────────────────
SPECIAL_INTEREST  SHADOW THE HEDGEHOG
STATUS            ONLINE
PUBLIC_REPOS      {len(repos)}
SHADOW_REPOS      {len(shadow_repos)}
LATEST_PROJECT    {recent['name']}
LATEST_COMMIT     {stamp} // {msg}

LANGUAGE DISTRIBUTION // REPOSITORY-DERIVED
{lang_lines}
```"""

    ecosystem = """```text
SHADOW DATABASE // LIVE
────────────────────────────────────────────────────
shadorux.dev                 MAIN NODE
shadowshrine.shadorux.dev    SHADOW SHRINE
shadorux-archive.shadorux.dev ARCHIVE NODE

MODE                         ARCHIVE / BUILD / CATALOG
SUBJECT                      SHADOW THE HEDGEHOG
```"""

    lastfm = f"""<div align=\"center\">

[![Last.fm recently played](https://lastfm-recently-played.vercel.app/api?user={urllib.parse.quote(LASTFM_USER)}&count=5&width=600&loved=true&header_style=compact_stats_only)](https://www.last.fm/user/{LASTFM_USER})

`LAST.FM // {LASTFM_USER}`

</div>"""

    text = README.read_text(encoding="utf-8")
    text = replace_block(text, "SYSTEM", system)
    text = replace_block(text, "ECOSYSTEM", ecosystem)
    text = replace_block(text, "LASTFM", lastfm)
    README.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
