"""Builds the profile: fetches live GitHub numbers, renders the SVG panels and README.md.

Usage:
    python tools/build.py            # fetch + render
    python tools/build.py --offline  # render from tools/data/stats.json
Token: GITHUB_TOKEN env var, else `gh auth token`.
"""

import base64
import datetime as dt
import html
import json
import os
import subprocess
import sys
from pathlib import Path

import content as C

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
DATA = ROOT / "tools" / "data" / "stats.json"
FONTS = ROOT / "tools" / "fonts"

W = 880

BG = "#0d0708"
MASK = "#150809"        # solder mask
MASK_EDGE = "#3b1a20"
TRACE = "#5e2329"       # copper under mask
DISPLAY = "#090506"
SEG_OFF = "#2a1013"
SILK = "#f2e8e8"
DIM = "#a08589"
GOLD = "#d4a24c"
GOLD_DIM = "#a8803c"
EPOXY = "#141113"
RED = "#dc2626"
RED_HI = "#ff5a5a"
RED_LO = "#7f1d1d"
AMBER = "#f59e0b"
GREEN = "#22c55e"
STATUS_COLOR = {"LIVE": GREEN, "BETA": AMBER, "WIP": RED_HI}
LED_LEVELS = [RED_LO, "#b91c1c", RED, RED_HI]


# ---------------------------------------------------------------- fetch

QUERY = """
query($login: String!) {
  user(login: $login) {
    createdAt
    followers { totalCount }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
  }
}
"""


def token():
    if os.environ.get("GITHUB_TOKEN"):
        return os.environ["GITHUB_TOKEN"]
    return subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()


def fetch():
    import requests

    r = requests.post(
        "https://api.github.com/graphql",
        json={"query": QUERY, "variables": {"login": C.GITHUB_USER}},
        headers={"Authorization": f"bearer {token()}"},
        timeout=30,
    )
    r.raise_for_status()
    body = r.json()
    if "errors" in body:
        raise SystemExit(f"GraphQL error: {body['errors']}")
    u = body["data"]["user"]
    cal = u["contributionsCollection"]["contributionCalendar"]
    days = [(d["date"], d["contributionCount"]) for w in cal["weeks"] for d in w["contributionDays"]]
    langs = {}
    for repo in u["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            name = e["node"]["name"]
            if name not in C.LANG_IGNORE:
                langs[name] = langs.get(name, 0) + e["size"]
    stats = {
        "generated": dt.date.today().isoformat(),
        "since": u["createdAt"][:4],
        "followers": u["followers"]["totalCount"],
        "repos": u["repositories"]["totalCount"],
        "stars": sum(n["stargazerCount"] for n in u["repositories"]["nodes"]),
        "total": cal["totalContributions"],
        "days": days,
        "langs": langs,
    }
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(stats, indent=1))
    return stats


# ---------------------------------------------------------------- helpers


def esc(s):
    return html.escape(str(s), quote=True)


def wrap(text, max_chars):
    lines, cur = [], ""
    for word in text.split():
        if cur and len(cur) + 1 + len(word) > max_chars:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    if cur:
        lines.append(cur)
    return lines


def font_css(weights):
    faces = []
    for w in weights:
        b64 = base64.b64encode((FONTS / f"jbm-{w}.woff2").read_bytes()).decode()
        faces.append(f"@font-face{{font-family:'JBM';font-weight:{w};src:url(data:font/woff2;base64,{b64}) format('woff2')}}")
    return "".join(faces)


BASE_CSS = (
    "text{font-family:'JBM',ui-monospace,Consolas,Menlo,monospace;fill:" + SILK + "}"
    ".dim{fill:" + DIM + "}.red{fill:" + RED_HI + "}.gold{fill:" + GOLD + "}.b{font-weight:700}.xb{font-weight:800}"
    ".tr{fill:none;stroke:" + TRACE + ";stroke-width:3;stroke-linejoin:round;stroke-linecap:round}"
    ".flow{fill:none;stroke:" + RED_HI + ";stroke-width:2;stroke-linecap:round;stroke-dasharray:5 70;animation:flow 2.4s linear infinite}"
    "@keyframes flow{from{stroke-dashoffset:75}to{stroke-dashoffset:0}}"
    ".blink{animation:blink 1.6s steps(2,start) infinite}@keyframes blink{to{visibility:hidden}}"
    "@media (prefers-reduced-motion:reduce){*{animation:none!important}.flow{display:none}}"
)

GLOW = (
    '<filter id="glow" x="-50%" y="-50%" width="200%" height="200%">'
    '<feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
)


def svg(name, h, body, title, desc, weights=(400, 700), css="", width=W):
    out = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{h}" viewBox="0 0 {width} {h}" '
        f'role="img" aria-labelledby="t d">\n<title id="t">{esc(title)}</title>\n<desc id="d">{esc(desc)}</desc>\n'
        f"<style>{font_css(weights)}{BASE_CSS}{css}</style>\n{body}\n</svg>\n"
    )
    (ASSETS / name).parent.mkdir(parents=True, exist_ok=True)
    (ASSETS / name).write_text(out, encoding="utf-8")


def board(h, w=W, holes=True):
    """PCB outline with optional mounting holes in the corners."""
    s = f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="14" fill="{MASK}" stroke="{MASK_EDGE}" stroke-width="1.5"/>'
    if holes:
        for x, y in ((22, 22), (w - 22, 22), (22, h - 22), (w - 22, h - 22)):
            s += f'<circle cx="{x}" cy="{y}" r="7" fill="{BG}" stroke="{GOLD_DIM}" stroke-width="3"/>'
    return s


def strip(title, meta="", y=0):
    """Silkscreen title line at the top of a panel."""
    s = f'<text x="44" y="{y + 30}" font-size="12" class="b" letter-spacing="2"><tspan class="red">▸</tspan> {esc(title)}</text>'
    if meta:
        s += f'<text x="{W - 44}" y="{y + 30}" font-size="11" class="dim" text-anchor="end">{esc(meta)}</text>'
    s += f'<line x1="44" x2="{W - 44}" y1="{y + 44}" y2="{y + 44}" stroke="{SILK}" stroke-opacity=".18" stroke-dasharray="1 3"/>'
    return s


def via(x, y):
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{GOLD_DIM}"/><circle cx="{x:.1f}" cy="{y:.1f}" r="1.8" fill="{BG}"/>'


def trace(pts, flow=True, dur=2.4):
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    s = f'<path class="tr" d="{d}"/>'
    if flow:
        s += f'<path class="flow" d="{d}" style="animation-duration:{dur}s"/>'
    return s


SEGMENTS = {
    "0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd",
    "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcdfg", "d": "bcdeg", "-": "g",
}


def seven_seg(x, y, text, h=44, w=24, t=6.4, pitch=31):
    """Classic 7-segment display. Unlit segments stay faintly visible."""
    out = [f'<g transform="translate({x},{y}) skewX(-7)">']
    lit_parts, off_parts = [], []
    for i, ch in enumerate(text):
        ox = i * pitch
        half = h / 2
        rects = {
            "a": (ox + t, 0, w - 2 * t, t),
            "b": (ox + w - t, t, t, half - 1.5 * t),
            "c": (ox + w - t, half + t / 2, t, half - 1.5 * t),
            "d": (ox + t, h - t, w - 2 * t, t),
            "e": (ox, half + t / 2, t, half - 1.5 * t),
            "f": (ox, t, t, half - 1.5 * t),
            "g": (ox + t, half - t / 2, w - 2 * t, t),
        }
        on = SEGMENTS.get(ch, "")
        for seg, (rx, ry, rw, rh) in rects.items():
            r = f'<rect x="{rx + 0.5:.1f}" y="{ry + 0.5:.1f}" width="{rw - 1:.1f}" height="{rh - 1:.1f}" rx="2"/>'
            (lit_parts if seg in on else off_parts).append(r)
    out.append(f'<g fill="#190809">{"".join(off_parts)}</g>')
    out.append(f'<g fill="{RED_HI}" filter="url(#glow)">{"".join(lit_parts)}</g></g>')
    return "".join(out)


# ---------------------------------------------------------------- panels


def header():
    h = 400
    b = [f"<defs>{GLOW}</defs>", board(h)]
    b.append(f'<text x="44" y="30" font-size="10.5" class="dim" letter-spacing="2">ROCI-MAIN · 2 LAYER · 1.6 mm</text>')
    b.append(f'<circle class="blink" cx="{W - 90}" cy="26" r="4" fill="{RED_HI}" filter="url(#glow)"/>'
             f'<text x="{W - 80}" y="30" font-size="10.5" class="dim" letter-spacing="2">PWR</text>')

    # Main IC (QFP-40) on the right
    cx, cy, size = 720, 142, 124
    x0, y0 = cx - size / 2, cy - size / 2
    pitch, n = 11, 10
    offs = [-pitch * (n - 1) / 2 + k * pitch for k in range(n)]
    pins = []
    for o in offs:
        pins += [(cx + o - 2.5, y0 - 9, 5, 9), (cx + o - 2.5, y0 + size, 5, 9),
                 (x0 - 9, cy + o - 2.5, 9, 5), (x0 + size, cy + o - 2.5, 9, 5)]

    # Traces first so the chip and pads sit on top of them.
    tps = [(66, 272), (262, 272), (458, 272)]
    lanes = [228, 238, 248]
    for k, ((tx, ty), lane) in enumerate(zip(tps, lanes)):
        px = cx + offs[k + 1]
        b.append(trace([(px, y0 + size + 9), (px, lane), (tx + (ty - lane), lane), (tx, ty)], dur=2.0 + k * 0.5))
    for k, dy in ((2, -26), (5, 0), (7, 26)):
        py = cy + offs[k]
        b.append(trace([(x0 + size + 9, py), (812, py), (812 + abs(dy), py + dy)], dur=2.8) + via(812 + abs(dy), py + dy))
    tx1 = cx + offs[2]
    b.append(trace([(tx1, y0 - 9), (tx1, 58), (tx1 - 20, 38), (560, 38)], dur=3.2) + via(560, 38))
    tx2 = cx + offs[7]
    b.append(trace([(tx2, y0 - 9), (tx2, 54), (tx2 + 16, 38)], flow=False) + via(tx2 + 16, 38))
    for k, label in ((4, "R1"), (6, "C1")):
        py = cy + offs[k]
        b.append(trace([(x0 - 9, py), (612, py)], flow=False) + trace([(586, py), (560, py)], flow=False) + via(560, py))
        b.append(f'<rect x="604" y="{py - 5}" width="9" height="10" rx="1" fill="{GOLD}"/>'
                 f'<rect x="585" y="{py - 5}" width="9" height="10" rx="1" fill="{GOLD}"/>'
                 f'<rect x="594" y="{py - 4}" width="10" height="8" fill="{EPOXY if label == "R1" else "#6b4a2e"}"/>'
                 f'<text x="599" y="{py - 9}" font-size="8" class="dim" text-anchor="middle">{label}</text>')

    b.append(f'<rect x="{x0 - 16}" y="{y0 - 16}" width="{size + 32}" height="{size + 32}" fill="none" stroke="{SILK}" stroke-opacity=".3" stroke-dasharray="2 3"/>')
    b.append("".join(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{hh}" fill="{GOLD}"/>' for x, y, w, hh in pins))
    b.append(f'<rect x="{x0}" y="{y0}" width="{size}" height="{size}" rx="4" fill="{EPOXY}" stroke="#2e2628"/>')
    b.append(f'<circle cx="{x0 + 14}" cy="{y0 + 14}" r="4" fill="#2e2628"/>')
    b.append(f'<text x="{cx}" y="{cy + 2}" font-size="26" class="xb" text-anchor="middle" letter-spacing="2">ROCI</text>')
    b.append(f'<text x="{cx}" y="{cy + 22}" font-size="9.5" class="dim" text-anchor="middle" letter-spacing="1.5">EE-2026 · IL</text>')
    b.append(f'<text x="{x0 - 16}" y="{y0 - 22}" font-size="10" class="dim">U0</text>')

    # Silkscreen name block
    b.append(f'<text x="44" y="112" font-size="48" class="xb" letter-spacing="1">{esc(C.NAME)}</text>')
    b.append(f'<text x="46" y="142" font-size="15" class="b"><tspan class="dim">aka </tspan><tspan class="red">{esc(C.HANDLE)}</tspan></text>')
    b.append(f'<text x="46" y="176" font-size="14">{esc(C.TAGLINE)}</text>')
    b.append(f'<text x="46" y="200" font-size="13" class="dim">// {esc(C.MISSION)}</text>')

    # Test points
    for (tx, ty), (ref, net, value, note) in zip(tps, C.TEST_POINTS):
        b.append(f'<circle cx="{tx}" cy="{ty}" r="8" fill="{GOLD}"/><circle cx="{tx}" cy="{ty}" r="3.2" fill="{BG}"/>')
        b.append(f'<text x="{tx - 10}" y="{ty + 30}" font-size="10" letter-spacing="1.5"><tspan class="red b">{esc(ref)}</tspan><tspan class="dim"> · {esc(net)}</tspan></text>')
        b.append(f'<text x="{tx - 10}" y="{ty + 50}" font-size="15" class="b">{esc(value)}</text>')
        b.append(f'<text x="{tx - 10}" y="{ty + 68}" font-size="11" class="dim">{esc(note)}</text>')

    b.append(f'<line x1="44" x2="{W - 44}" y1="{h - 36}" y2="{h - 36}" stroke="{SILK}" stroke-opacity=".18" stroke-dasharray="1 3"/>')
    step = (W - 88) / len(C.STATUS_BAR)
    for i, item in enumerate(C.STATUS_BAR):
        b.append(f'<text x="{44 + i * step:.0f}" y="{h - 16}" font-size="10.5" class="dim" letter-spacing="1">{esc(item)}</text>')

    tps_desc = "; ".join(f"{t[1]}: {t[2]} ({t[3]})" for t in C.TEST_POINTS)
    svg("header.svg", h, "\n".join(b), f"{C.NAME} ({C.HANDLE})",
        f"{C.TAGLINE}, {C.MISSION}. Drawn as a circuit board with a chip labeled ROCI. {tps_desc}.",
        weights=(400, 700, 800))


def links():
    w, h = 220, 60
    for i, L in enumerate(C.LINKS, 1):
        b = [board(h, w=w, holes=False)]
        b.append(f'<rect x="18" y="19" width="22" height="22" rx="2" fill="{GOLD}"/><circle cx="29" cy="30" r="5" fill="{BG}"/>')
        b.append(f'<text x="29" y="54" font-size="7.5" class="dim" text-anchor="middle">J{i}</text>')
        b.append(f'<text x="54" y="28" font-size="13" class="b">{esc(L["label"])}</text>')
        b.append(f'<text x="54" y="44" font-size="10" class="dim" letter-spacing="1">{esc(L["sub"].upper())}</text>')
        svg(f"links/{L['slug']}.svg", h, "\n".join(b), L["label"], f"{L['sub']}: {L['label']}", width=w)


def streaks(days):
    today = dt.date.today().isoformat()
    counts = [c for d, c in days if d <= today]
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    cur = 0
    seq = counts[:-1] if counts and counts[-1] == 0 else counts  # today may not have started yet
    for c in reversed(seq):
        if not c:
            break
        cur += 1
    return cur, longest, sum(1 for c in counts if c)


def stats(s):
    h = 290
    cur, longest, active = streaks(s["days"])
    tiles = [
        ("DS1", "CONTRIBUTIONS", str(s["total"]), "last 12 months"),
        ("DS2", "STREAK", f"{cur}d", f"best {longest}d"),
        ("DS3", "ACTIVE DAYS", str(active), "of the last 365"),
        ("DS4", "PUBLIC REPOS", str(s["repos"]), "source, no forks"),
        ("DS5", "STARS", str(s["stars"]), "across public repos"),
        ("DS6", "ON GITHUB", s["since"], "member since"),
    ]
    b = [f"<defs>{GLOW}</defs>", board(h), strip("READOUTS", f"auto-updated {s['generated']}")]
    tw, th, gap, x0, y0 = 152, 102, 10, 44, 62
    for i, (ref, label, value, note) in enumerate(tiles):
        x, y = x0 + (i % 3) * (tw + gap), y0 + (i // 3) * (th + gap)
        b.append(f'<rect x="{x}" y="{y}" width="{tw}" height="{th}" rx="4" fill="{DISPLAY}" stroke="{MASK_EDGE}"/>')
        b.append(f'<text x="{x + 12}" y="{y + 18}" font-size="9.5" letter-spacing="1.2"><tspan class="red b">{ref}</tspan><tspan class="dim"> {esc(label)}</tspan></text>')
        b.append(seven_seg(x + 18, y + 30, value))
        b.append(f'<text x="{x + 12}" y="{y + 92}" font-size="9.5" class="dim">{esc(note)}</text>')

    # LED bar-graph of top languages
    mx, my, mw = 530, 62, 306
    b.append(f'<rect x="{mx}" y="{my}" width="{mw}" height="{2 * th + gap}" rx="4" fill="{DISPLAY}" stroke="{MASK_EDGE}"/>')
    b.append(f'<text x="{mx + 12}" y="{my + 18}" font-size="9.5" letter-spacing="1.2"><tspan class="red b">BAR1</tspan><tspan class="dim"> LANGUAGES · bytes</tspan></text>')
    total = sum(s["langs"].values()) or 1
    top = sorted(s["langs"].items(), key=lambda kv: -kv[1])[:6]
    segs, seg_w, seg_gap = 16, 7, 2
    for i, (name, size) in enumerate(top):
        y = my + 44 + i * 26
        pct = size / total
        lit = max(1, round(pct / (top[0][1] / total) * segs))
        b.append(f'<text x="{mx + 12}" y="{y + 9}" font-size="11">{esc(name[:11])}</text>')
        on, off = [], []
        for k in range(segs):
            r = f'<rect x="{mx + 106 + k * (seg_w + seg_gap)}" y="{y}" width="{seg_w}" height="11" rx="1.5"/>'
            (on if k < lit else off).append(r)
        b.append(f'<g fill="{SEG_OFF}">{"".join(off)}</g><g fill="{RED_HI}" filter="url(#glow)">{"".join(on)}</g>')
        b.append(f'<text x="{mx + mw - 12}" y="{y + 9}" font-size="11" class="dim" text-anchor="end">{pct * 100:.0f}%</text>')

    langs_desc = ", ".join(f"{n} {v / total * 100:.0f}%" for n, v in top)
    svg("stats.svg", h, "\n".join(b), "Readouts",
        f"{s['total']} contributions in the last 12 months; current streak {cur} days, longest {longest}; {active} active days; "
        f"{s['repos']} public repos; {s['stars']} stars; on GitHub since {s['since']}. Top languages: {langs_desc}.",
        weights=(400, 700))


def matrix(s):
    """Contribution calendar as a 53x7 LED matrix."""
    days = [(dt.date.fromisoformat(d), c) for d, c in s["days"]]
    first = days[0][0]
    first_wd = (first.weekday() + 1) % 7  # Sunday = 0, matching GitHub's calendar
    nonzero = sorted(c for _, c in days if c)

    def level(c):
        if not c:
            return -1
        rank = sum(1 for v in nonzero if v <= c) / len(nonzero)
        return min(3, int(rank * 4 - 1e-9))

    cols = (len(days) + first_wd + 6) // 7
    gx, gy, cell = 82, 84, (W - 82 - 44) / cols
    h = gy + 7 * cell + 64
    b = [f"<defs>{GLOW}</defs>", board(h)]
    busiest = max(days, key=lambda dc: dc[1])
    b.append(strip("LED MATRIX · CONTRIBUTIONS", f"Σ {s['total']} · busiest {busiest[0].strftime('%b %d')} ({busiest[1]})"))
    for row, name in ((1, "MON"), (3, "WED"), (5, "FRI")):
        b.append(f'<text x="{gx - 10}" y="{gy + row * cell + cell / 2 + 3.5:.1f}" font-size="9" class="dim" text-anchor="end">{name}</text>')
    off, lit = [], {i: [] for i in range(4)}
    seen = set()
    for i, (date, c) in enumerate(days):
        col, row = divmod(i + first_wd, 7)
        x, y = gx + col * cell + cell / 2, gy + row * cell + cell / 2
        if date.day <= 7 and row == 0 and (date.year, date.month) not in seen:
            seen.add((date.year, date.month))
            b.append(f'<text x="{x - cell / 2:.1f}" y="{gy - 10}" font-size="9" class="dim">{date.strftime("%b").upper()}</text>')
        lv = level(c)
        circle = f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{cell * 0.33:.2f}"/>'
        (off if lv < 0 else lit[lv]).append(circle)
    b.append(f'<g fill="{SEG_OFF}">{"".join(off)}</g>')
    b.append(f'<g filter="url(#glow)">' + "".join(f'<g fill="{LED_LEVELS[k]}">{"".join(v)}</g>' for k, v in lit.items()) + "</g>")
    lx = W - 44 - 5 * 16 - 64
    ly = h - 26
    b.append(f'<text x="{lx}" y="{ly + 4}" font-size="9.5" class="dim" text-anchor="end">less</text>')
    for k, color in enumerate([SEG_OFF] + LED_LEVELS):
        b.append(f'<circle cx="{lx + 14 + k * 16}" cy="{ly}" r="4.6" fill="{color}"/>')
    b.append(f'<text x="{lx + 14 + 5 * 16}" y="{ly + 4}" font-size="9.5" class="dim">more</text>')
    b.append(f'<text x="44" y="{ly + 4}" font-size="9.5" class="dim" letter-spacing="1">D1-D{len(days)} · one LED per day · commits, PRs, issues, reviews</text>')
    svg("matrix.svg", h, "\n".join(b), "Contribution LED matrix",
        f"One LED per day for the last year, brighter means more contributions. {s['total']} total; busiest day "
        f"{busiest[0].strftime('%b %d, %Y')} with {busiest[1]}.")


def section(name, title, meta=""):
    h = 54
    b = [board(h, holes=False), f'<text x="24" y="34" font-size="13" class="b" letter-spacing="2"><tspan class="red">▸</tspan> {esc(title)}</text>']
    if meta:
        b.append(f'<text x="{W - 24}" y="34" font-size="11" class="dim" text-anchor="end">{esc(meta)}</text>')
    svg(name, h, "\n".join(b), title, title)


def chip(p):
    w, h = 440, 262
    bx, by, bw, bh = 22, 40, 396, 180
    b = [board(h, w=w, holes=False)]
    pin_xs = [bx + 20 + k * (bw - 40) / 11 - 5 for k in range(12)]
    for k in (1, 4, 9):
        x = pin_xs[k] + 5
        b.append(trace([(x, by - 12), (x, 18), (x + 10, 8)], flow=False))
    b.append(f'<rect x="{bx - 8}" y="{by - 20}" width="{bw + 16}" height="{bh + 40}" fill="none" stroke="{SILK}" stroke-opacity=".22" stroke-dasharray="2 3"/>')
    for x in pin_xs:
        b.append(f'<rect x="{x:.1f}" y="{by - 12}" width="10" height="12" rx="1" fill="{GOLD_DIM}"/>')
        b.append(f'<rect x="{x:.1f}" y="{by + bh}" width="10" height="12" rx="1" fill="{GOLD_DIM}"/>')
    b.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="5" fill="{EPOXY}" stroke="#2e2628" stroke-width="1.5"/>')
    b.append(f'<path d="M{bx},{by + bh / 2 - 12} a12,12 0 0 1 0,24" fill="{MASK}" stroke="#2e2628"/>')
    b.append(f'<circle cx="{bx + 14}" cy="{by + bh - 14}" r="4" fill="#2e2628"/>')
    ix = bx + 26
    b.append(f'<text x="{ix}" y="{by + 26}" font-size="11" letter-spacing="1.5"><tspan class="red b">{esc(p["ref"])}</tspan><tspan class="dim"> · {esc(p["kind"])}</tspan></text>')
    sc = STATUS_COLOR[p["status"]]
    b.append(f'<circle cx="{bx + bw - 62}" cy="{by + 22}" r="4" fill="{sc}"/>'
             f'<text x="{bx + bw - 52}" y="{by + 26}" font-size="10" class="b" letter-spacing="1.5" style="fill:{sc}">{p["status"]}</text>')
    b.append(f'<text x="{ix}" y="{by + 56}" font-size="22" class="xb">{esc(p["name"])}</text>')
    b.append(f'<text x="{ix}" y="{by + 76}" font-size="11" class="red">{esc(p["subtitle"])}</text>')
    for i, line in enumerate(wrap(p["desc"], 49)[:3]):
        b.append(f'<text x="{ix}" y="{by + 100 + i * 17}" font-size="11.5" class="dim">{esc(line)}</text>')
    tx = ix
    for tag in p["tags"]:
        tw = len(tag) * 6 + 16
        b.append(f'<rect x="{tx}" y="{by + bh - 30}" width="{tw}" height="18" rx="3" fill="none" stroke="{GOLD_DIM}" stroke-opacity=".7"/>'
                 f'<text x="{tx + 8}" y="{by + bh - 17}" font-size="10" class="b gold" letter-spacing=".5">{esc(tag)}</text>')
        tx += tw + 6
    b.append(f'<text x="{w / 2}" y="{h - 10}" font-size="10" class="dim" text-anchor="middle">→ {esc(p["footer"])}</text>')
    svg(f"chips/{p['slug']}.svg", h, "\n".join(b), p["name"],
        f"{p['name']} ({p['status']}, {p['kind']}): {p['subtitle']}. {p['desc']} Built with {', '.join(t.title() for t in p['tags'])}.",
        weights=(400, 700, 800), width=w)


def bom():
    rh = 32
    h = 62 + rh * (len(C.BOM) + 1) + 30
    b = [board(h), strip("BILL OF MATERIALS", "tech stack")]
    cols = (44, 140, 290)
    y = 62
    b.append(f'<rect x="44" y="{y}" width="{W - 88}" height="{rh}" rx="4" fill="{DISPLAY}"/>')
    for x, head in zip(cols, ("REF", "BLOCK", "PARTS")):
        b.append(f'<text x="{x + 8}" y="{y + 21}" font-size="10" class="dim b" letter-spacing="1.5">{head}</text>')
    for i, (ref, block, parts) in enumerate(C.BOM):
        ry = y + rh * (i + 1)
        b.append(f'<line x1="44" x2="{W - 44}" y1="{ry + rh}" y2="{ry + rh}" stroke="{SILK}" stroke-opacity=".1"/>')
        b.append(f'<text x="{cols[0] + 8}" y="{ry + 21}" font-size="12" class="red b">{esc(ref)}</text>')
        b.append(f'<text x="{cols[1] + 8}" y="{ry + 21}" font-size="12" class="b">{esc(block)}</text>')
        b.append(f'<text x="{cols[2] + 8}" y="{ry + 21}" font-size="12">{esc(parts)}</text>')
    svg("stack.svg", h, "\n".join(b), "Bill of materials (tech stack)",
        " ".join(f"{block}: {parts}." for _, block, parts in C.BOM))


def footer():
    h = 96
    b = [board(h, holes=False)]
    b.append(f'<text x="24" y="34" font-size="11" class="b" letter-spacing="2">ROCI-MAIN <tspan class="dim">· REV {dt.date.today():%Y.%m} · DESIGNED IN ISRAEL</tspan></text>')
    b.append(f'<text x="{W - 24}" y="34" font-size="10" class="dim" text-anchor="end">end of board</text>')
    n, fw, gap = 46, 12, 6
    start = (W - (n * fw + (n - 1) * gap)) / 2
    for k in range(n):
        x = start + k * (fw + gap)
        b.append(f'<rect x="{x:.1f}" y="58" width="{fw}" height="37" rx="2" fill="{GOLD}" opacity="{.95 if k % 2 else .8}"/>')
    svg("footer.svg", h, "\n".join(b), "End of board", "Board edge with a row of gold connector fingers.")


# ---------------------------------------------------------------- readme


def readme():
    img = lambda src, alt, width="100%": f'<img src="./assets/{src}" width="{width}" align="top" alt="{esc(alt)}">'
    pct = f"{100 / len(C.LINKS):g}%"
    lines = ['<p align="center">',
             f'<a href="https://rocisapps.com">{img("header.svg", f"{C.NAME} ({C.HANDLE}). {C.TAGLINE}.")}</a>',
             "".join(f'<a href="{L["href"]}">{img(f"links/{L["slug"]}.svg", f"{L["sub"]}: {L["label"]}", pct)}</a>' for L in C.LINKS),
             img("stats.svg", "Readouts: live GitHub stats and top languages"),
             img("matrix.svg", "Contribution LED matrix for the last year"),
             img("projects.svg", "Projects")]
    for i in range(0, len(C.PROJECTS), 2):
        lines.append("".join(
            f'<a href="{p["href"]}">{img(f"chips/{p["slug"]}.svg", f"{p["name"]} ({p["status"]}): {p["subtitle"]}", "50%")}</a>'
            for p in C.PROJECTS[i:i + 2]))
    lines += [img("stack.svg", "Tech stack: " + "; ".join(f"{b}: {p}" for _, b, p in C.BOM)),
              img("footer.svg", "End of board."),
              "</p>", "",
              "<!-- Generated by tools/build.py. Edit tools/content.py, not this file. -->", ""]
    (ROOT / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    s = json.loads(DATA.read_text()) if "--offline" in sys.argv else fetch()
    for old in ("signal.svg",):
        (ASSETS / old).unlink(missing_ok=True)
    header()
    links()
    stats(s)
    matrix(s)
    section("projects.svg", "COMPONENTS", "click a chip to open it")
    for p in C.PROJECTS:
        chip(p)
    bom()
    footer()
    readme()
    print(f"built {len(list(ASSETS.rglob('*.svg')))} svgs, {s['total']} contributions")


if __name__ == "__main__":
    main()
