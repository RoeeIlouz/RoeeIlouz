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
import math
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
PANEL = "#140a0c"
SCREEN = "#090506"
EDGE = "#3b1a20"
GRID = "#24100f"
GRID_MAJ = "#4a1d24"
DIM = "#9b7b80"
TEXT = "#f5e9ea"
RED = "#dc2626"
RED_HI = "#ff5a5a"
RED_LO = "#7f1d1d"
AMBER = "#f59e0b"
GREEN = "#22c55e"
STATUS_COLOR = {"LIVE": GREEN, "BETA": AMBER, "WIP": RED_HI}


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
    "text{font-family:'JBM',ui-monospace,Consolas,Menlo,monospace;fill:" + TEXT + "}"
    ".dim{fill:" + DIM + "}.red{fill:" + RED_HI + "}.b{font-weight:700}.xb{font-weight:800}"
    "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
)


def svg(name, h, body, title, desc, weights=(400, 700), css="", width=W):
    out = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{h}" viewBox="0 0 {width} {h}" '
        f'role="img" aria-labelledby="t d">\n<title id="t">{esc(title)}</title>\n<desc id="d">{esc(desc)}</desc>\n'
        f"<style>{font_css(weights)}{BASE_CSS}{css}</style>\n{body}\n</svg>\n"
    )
    (ASSETS / name).parent.mkdir(parents=True, exist_ok=True)
    (ASSETS / name).write_text(out, encoding="utf-8")


def frame(h, x=0, y=0, w=W):
    return f'<rect x="{x + 1}" y="{y + 1}" width="{w - 2}" height="{h - 2}" rx="14" fill="{PANEL}" stroke="{EDGE}" stroke-width="1.5"/>'


def strip(title, meta="", y=0):
    """Instrument title strip at the top of a panel."""
    s = f'<text x="24" y="{y + 30}" font-size="12" class="b" letter-spacing="2"><tspan class="red">▸</tspan> {esc(title)}</text>'
    if meta:
        s += f'<text x="{W - 24}" y="{y + 30}" font-size="11" class="dim" text-anchor="end">{esc(meta)}</text>'
    s += f'<line x1="20" x2="{W - 20}" y1="{y + 44}" y2="{y + 44}" stroke="{EDGE}"/>'
    return s


def graticule(x, y, w, h, nx, ny):
    dx, dy = w / nx, h / ny
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{SCREEN}" stroke="{EDGE}"/>']
    for i in range(1, nx):
        cx = x + i * dx
        major = i == nx // 2
        out.append(f'<line x1="{cx:.1f}" x2="{cx:.1f}" y1="{y}" y2="{y + h}" stroke="{GRID_MAJ if major else GRID}" stroke-dasharray="{"" if major else "2 4"}"/>')
    for j in range(1, ny):
        cy = y + j * dy
        major = j == ny // 2
        out.append(f'<line x1="{x}" x2="{x + w}" y1="{cy:.1f}" y2="{cy:.1f}" stroke="{GRID_MAJ if major else GRID}" stroke-dasharray="{"" if major else "2 4"}"/>')
    return "".join(out)


def smooth_path(pts, floor=None):
    """Catmull-Rom spline through pts as cubic beziers; control points clamped to floor (no dips below zero)."""
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(len(pts) - 1):
        p0 = pts[max(i - 1, 0)]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[min(i + 2, len(pts) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        if floor is not None:
            c1, c2 = (c1[0], min(c1[1], floor)), (c2[0], min(c2[1], floor))
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d


GLOW = (
    '<filter id="glow" x="-20%" y="-50%" width="140%" height="200%">'
    '<feGaussianBlur stdDeviation="2.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
)


# ---------------------------------------------------------------- panels


def header():
    h = 340
    sx, sy, sw, sh = 20, 48, 600, 256
    # Signature trace: idle, a digital burst, a sine packet, then an RLC step response.
    pts, base, amp = [], sy + 206, 20
    for i in range(0, sw + 1, 2):
        t = i / sw
        if t < 0.08:
            v = 0
        elif t < 0.34:
            v = 1 if int((t - 0.08) / 0.0325) % 2 == 0 else -0.2
        elif t < 0.58:
            v = math.sin((t - 0.34) * 2 * math.pi * 12) * math.sin((t - 0.34) / 0.24 * math.pi)
        elif t < 0.6:
            v = 0
        else:
            k = t - 0.6
            v = 1 - math.exp(-k * 14) * math.cos(k * 2 * math.pi * 11)
        pts.append((sx + i, base - v * amp))
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    plen = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))

    css = (
        f".trace{{stroke-dasharray:{plen:.0f};animation:draw 7s ease-in-out infinite}}"
        f"@keyframes draw{{0%{{stroke-dashoffset:{plen:.0f}}}55%,100%{{stroke-dashoffset:0}}}}"
        ".blink{animation:blink 1.4s steps(2,start) infinite}@keyframes blink{to{visibility:hidden}}"
    )
    b = [f"<defs>{GLOW}</defs>", frame(h)]
    b.append(f'<text x="24" y="31" font-size="11" class="dim" letter-spacing="2">ROCI-SCOPE · DSO-26</text>')
    b.append(f'<text x="{W - 24}" y="31" font-size="11" text-anchor="end" letter-spacing="2" class="b"><tspan class="red blink">●</tspan> RUN</text>')
    b.append(graticule(sx, sy, sw, sh, 10, 8))
    b.append(f'<text x="{sx + 24}" y="{sy + 64}" font-size="48" class="xb" letter-spacing="1" filter="url(#glow)">{esc(C.NAME)}</text>')
    b.append(f'<text x="{sx + 26}" y="{sy + 92}" font-size="15" class="b"><tspan class="dim">aka </tspan><tspan class="red">{esc(C.HANDLE)}</tspan></text>')
    b.append(f'<text x="{sx + 26}" y="{sy + 126}" font-size="14">{esc(C.TAGLINE)}</text>')
    b.append(f'<text x="{sx + 26}" y="{sy + 148}" font-size="13" class="dim">&gt; {esc(C.MISSION)}<tspan class="red blink">_</tspan></text>')
    b.append(f'<path d="{d}" fill="none" stroke="{RED_LO}" stroke-width="1.5" opacity=".55"/>')
    b.append(f'<path class="trace" d="{d}" fill="none" stroke="{RED_HI}" stroke-width="2" filter="url(#glow)"/>')
    b.append(f'<text x="{sx + sw - 10}" y="{sy + sh - 10}" font-size="10" class="dim" text-anchor="end">1 V/div</text>')

    cx, cw, ch = 636, 224, 80
    for i, (chn, label, value, note) in enumerate(C.CHANNELS):
        y = sy + i * (ch + 8)
        b.append(f'<rect x="{cx}" y="{y}" width="{cw}" height="{ch}" rx="6" fill="{SCREEN}" stroke="{EDGE}"/>')
        b.append(f'<rect x="{cx}" y="{y + 12}" width="3" height="{ch - 24}" fill="{RED}"/>')
        b.append(f'<text x="{cx + 16}" y="{y + 24}" font-size="10" letter-spacing="1.5"><tspan class="red b">{esc(chn)}</tspan><tspan class="dim"> · {esc(label)}</tspan></text>')
        b.append(f'<text x="{cx + 16}" y="{y + 48}" font-size="15" class="b">{esc(value)}</text>')
        b.append(f'<text x="{cx + 16}" y="{y + 67}" font-size="11" class="dim">{esc(note)}</text>')

    b.append(f'<line x1="20" x2="{W - 20}" y1="{h - 30}" y2="{h - 30}" stroke="{EDGE}"/>')
    step = (W - 48) / len(C.STATUS_BAR)
    for i, item in enumerate(C.STATUS_BAR):
        b.append(f'<text x="{24 + i * step:.0f}" y="{h - 11}" font-size="10.5" class="dim" letter-spacing="1">{esc(item)}</text>')

    channels = "; ".join(f"{c[2]} ({c[3]})" for c in C.CHANNELS)
    svg("header.svg", h, "\n".join(b), f"{C.NAME} ({C.HANDLE})",
        f"{C.TAGLINE}, {C.MISSION}. Drawn as an oscilloscope screen. Channels: {channels}.",
        weights=(400, 700, 800), css=css)


def links():
    w, h = 220, 60
    for L in C.LINKS:
        b = [frame(h, w=w)]
        b.append(f'<circle cx="32" cy="30" r="11" fill="{SCREEN}" stroke="{RED}" stroke-width="3"/><circle cx="32" cy="30" r="3.5" fill="{RED_HI}"/>')
        b.append(f'<text x="54" y="27" font-size="13" class="b">{esc(L["label"])}</text>')
        b.append(f'<text x="54" y="43" font-size="10" class="dim" letter-spacing="1">{esc(L["sub"].upper())}</text>')
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
    h = 270
    cur, longest, active = streaks(s["days"])
    tiles = [
        ("CONTRIBUTIONS", str(s["total"]), "last 12 months"),
        ("STREAK", f"{cur}d", f"best {longest}d"),
        ("ACTIVE DAYS", str(active), "of the last 365"),
        ("PUBLIC REPOS", str(s["repos"]), "source, no forks"),
        ("STARS", str(s["stars"]), "across public repos"),
        ("ON GITHUB", s["since"], "member since"),
    ]
    b = [f"<defs>{GLOW}</defs>", frame(h), strip("MEASUREMENTS", f"auto-updated {s['generated']}")]
    tw, th, gap, x0, y0 = 158, 92, 10, 20, 62
    for i, (label, value, note) in enumerate(tiles):
        x, y = x0 + (i % 3) * (tw + gap), y0 + (i // 3) * (th + gap)
        b.append(f'<rect x="{x}" y="{y}" width="{tw}" height="{th}" rx="6" fill="{SCREEN}" stroke="{EDGE}"/>')
        b.append(f'<text x="{x + 14}" y="{y + 22}" font-size="10" class="dim" letter-spacing="1.5">{esc(label)}</text>')
        b.append(f'<text x="{x + 14}" y="{y + 60}" font-size="32" class="xb red" filter="url(#glow)">{esc(value)}</text>')
        b.append(f'<text x="{x + 14}" y="{y + 79}" font-size="10" class="dim">{esc(note)}</text>')

    # Language VU meter
    mx, my, mw = 528, 62, 332
    b.append(f'<rect x="{mx}" y="{my}" width="{mw}" height="{2 * th + gap}" rx="6" fill="{SCREEN}" stroke="{EDGE}"/>')
    b.append(f'<text x="{mx + 14}" y="{my + 22}" font-size="10" class="dim" letter-spacing="1.5">LANGUAGE SPECTRUM · bytes</text>')
    total = sum(s["langs"].values()) or 1
    top = sorted(s["langs"].items(), key=lambda kv: -kv[1])[:6]
    segs, seg_w, seg_gap = 20, 7, 2
    for i, (name, size) in enumerate(top):
        y = my + 46 + i * 23
        pct = size / total
        lit = max(1, round(pct / (top[0][1] / total) * segs))
        b.append(f'<text x="{mx + 14}" y="{y + 9}" font-size="11">{esc(name[:11])}</text>')
        for k in range(segs):
            color = (RED_HI if k >= segs - 4 else RED) if k < lit else GRID_MAJ
            op = "1" if k < lit else ".45"
            b.append(f'<rect x="{mx + 112 + k * (seg_w + seg_gap)}" y="{y}" width="{seg_w}" height="11" rx="1" fill="{color}" opacity="{op}"/>')
        b.append(f'<text x="{mx + mw - 14}" y="{y + 9}" font-size="11" class="dim" text-anchor="end">{pct * 100:.0f}%</text>')

    langs_desc = ", ".join(f"{n} {v / total * 100:.0f}%" for n, v in top)
    svg("stats.svg", h, "\n".join(b), "Measurements",
        f"{s['total']} contributions in the last 12 months; current streak {cur} days, longest {longest}; {active} active days; "
        f"{s['repos']} public repos; {s['stars']} stars; on GitHub since {s['since']}. Top languages: {langs_desc}.",
        weights=(400, 700, 800))


def signal(s):
    h = 292
    days = s["days"]
    weeks = [sum(c for _, c in days[i:i + 7]) for i in range(0, len(days), 7)]
    starts = [days[i][0] for i in range(0, len(days), 7)]
    px, py, pw, ph = 56, 62, 804, 170
    vmax = max(max(weeks), 1)
    top = math.ceil(vmax / 4 / 5) * 5 * 4 or 20
    n = len(weeks)
    pts = [(px + i * pw / (n - 1), py + ph - w / top * ph) for i, w in enumerate(weeks)]
    d = smooth_path(pts, floor=py + ph)
    area = d + f" L{px + pw},{py + ph} L{px},{py + ph} Z"
    peak_i = max(range(n), key=lambda i: weeks[i])
    busiest = max(days, key=lambda dc: dc[1])
    avg = s["total"] / 52

    css = (
        f".sweep{{animation:sweep 6s linear infinite}}@keyframes sweep{{from{{transform:translateX(0)}}to{{transform:translateX({pw}px)}}}}"
    )
    b = [f"<defs>{GLOW}<linearGradient id='fill' x1='0' y1='0' x2='0' y2='1'>"
         f"<stop offset='0' stop-color='{RED}' stop-opacity='.35'/><stop offset='1' stop-color='{RED}' stop-opacity='0'/></linearGradient>"
         f"<clipPath id='plot'><rect x='{px}' y='{py}' width='{pw}' height='{ph}'/></clipPath></defs>",
         frame(h), strip("CONTRIBUTION SIGNAL", f"Σ {s['total']}  ·  avg {avg:.0f}/wk  ·  peak {weeks[peak_i]}/wk")]
    b.append(graticule(px, py, pw, ph, 12, 4))
    for j in range(5):
        v = top * (4 - j) // 4
        b.append(f'<text x="{px - 8}" y="{py + j * ph / 4 + 4:.1f}" font-size="10" class="dim" text-anchor="end">{v}</text>')
    seen = set()
    for i, start in enumerate(starts):
        date = dt.date.fromisoformat(start)
        if date.day <= 7 and date.month not in seen:
            seen.add(date.month)
            x = px + i * pw / (n - 1)
            b.append(f'<text x="{x:.1f}" y="{py + ph + 18}" font-size="10" class="dim" text-anchor="middle">{date.strftime("%b").upper()}</text>')
    b.append(f'<g clip-path="url(#plot)"><path d="{area}" fill="url(#fill)"/>'
             f'<path d="{d}" fill="none" stroke="{RED_HI}" stroke-width="2.2" filter="url(#glow)"/>'
             f'<line class="sweep" x1="{px}" x2="{px}" y1="{py}" y2="{py + ph}" stroke="{RED_HI}" stroke-opacity=".5" stroke-width="1.5"/></g>')
    kx, ky = pts[peak_i]
    anchor = "end" if kx > px + pw * 0.75 else "start"
    off = -8 if anchor == "end" else 8
    b.append(f'<line x1="{kx:.1f}" x2="{kx:.1f}" y1="{py}" y2="{py + ph}" stroke="{AMBER}" stroke-dasharray="3 3" opacity=".8"/>')
    b.append(f'<circle cx="{kx:.1f}" cy="{ky:.1f}" r="4" fill="{AMBER}"/>')
    peak_date = dt.date.fromisoformat(starts[peak_i]).strftime("%b %d").upper()
    b.append(f'<text x="{kx + off:.1f}" y="{py + 14}" font-size="10" text-anchor="{anchor}" fill="{AMBER}" style="fill:{AMBER}">CURSOR · wk of {peak_date} · {weeks[peak_i]}</text>')
    bdate = dt.date.fromisoformat(busiest[0]).strftime("%b %d, %Y")
    b.append(f'<text x="24" y="{h - 16}" font-size="10.5" class="dim" letter-spacing="1">CH1 = commits + PRs + issues + reviews, weekly · busiest day {esc(bdate)} ({busiest[1]})</text>')
    svg("signal.svg", h, "\n".join(b), "Contribution signal",
        f"Weekly contributions over the last year drawn as an oscilloscope trace. {s['total']} total, about {avg:.0f} a week, "
        f"peak {weeks[peak_i]} in the week of {peak_date}; busiest day {bdate} with {busiest[1]}.")


def section(name, title, meta=""):
    h = 54
    b = [frame(h), f'<text x="24" y="34" font-size="13" class="b" letter-spacing="2"><tspan class="red">▸</tspan> {esc(title)}</text>']
    if meta:
        b.append(f'<text x="{W - 24}" y="34" font-size="11" class="dim" text-anchor="end">{esc(meta)}</text>')
    svg(name, h, "\n".join(b), title, title)


def chip(p):
    w, h = 440, 262
    bx, by, bw, bh = 22, 40, 396, 180
    b = [frame(h, w=w)]
    for k in range(12):
        x = bx + 20 + k * (bw - 40) / 11 - 5
        b.append(f'<rect x="{x:.1f}" y="{by - 12}" width="10" height="12" rx="1" fill="#6b5458"/>')
        b.append(f'<rect x="{x:.1f}" y="{by + bh}" width="10" height="12" rx="1" fill="#6b5458"/>')
    b.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="5" fill="#1b0f11" stroke="{EDGE}" stroke-width="1.5"/>')
    b.append(f'<path d="M{bx},{by + bh / 2 - 12} a12,12 0 0 1 0,24" fill="{PANEL}" stroke="{EDGE}"/>')
    b.append(f'<circle cx="{bx + 14}" cy="{by + bh - 14}" r="4" fill="{EDGE}"/>')
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
        b.append(f'<rect x="{tx}" y="{by + bh - 30}" width="{tw}" height="18" rx="3" fill="none" stroke="{RED_LO}"/>'
                 f'<text x="{tx + 8}" y="{by + bh - 17}" font-size="10" class="b" letter-spacing=".5">{esc(tag)}</text>')
        tx += tw + 6
    b.append(f'<text x="{w / 2}" y="{h - 12}" font-size="10" class="dim" text-anchor="middle">→ {esc(p["footer"])}</text>')
    svg(f"chips/{p['slug']}.svg", h, "\n".join(b), p["name"],
        f"{p['name']} ({p['status']}): {p['subtitle']}. {p['desc']} Built with {', '.join(t.title() for t in p['tags'])}.",
        weights=(400, 700, 800), width=w)


def bom():
    rh = 32
    h = 62 + rh * (len(C.BOM) + 1) + 16
    b = [frame(h), strip("BILL OF MATERIALS", "tech stack")]
    cols = (24, 120, 270)
    y = 62
    b.append(f'<rect x="20" y="{y}" width="{W - 40}" height="{rh}" rx="4" fill="{SCREEN}"/>')
    for x, head in zip(cols, ("REF", "BLOCK", "PARTS")):
        b.append(f'<text x="{x + 8}" y="{y + 21}" font-size="10" class="dim b" letter-spacing="1.5">{head}</text>')
    for i, (ref, block, parts) in enumerate(C.BOM):
        ry = y + rh * (i + 1)
        b.append(f'<line x1="20" x2="{W - 20}" y1="{ry + rh}" y2="{ry + rh}" stroke="{GRID}"/>')
        b.append(f'<text x="{cols[0] + 8}" y="{ry + 21}" font-size="12" class="red b">{esc(ref)}</text>')
        b.append(f'<text x="{cols[1] + 8}" y="{ry + 21}" font-size="12" class="b">{esc(block)}</text>')
        b.append(f'<text x="{cols[2] + 8}" y="{ry + 21}" font-size="12">{esc(parts)}</text>')
    svg("stack.svg", h, "\n".join(b), "Bill of materials (tech stack)",
        " ".join(f"{block}: {parts}." for _, block, parts in C.BOM))


def footer():
    h = 84
    pts = [(24, 42), (520, 42), (530, 22), (540, 62), (550, 42), (W - 220, 42)]
    d = "M" + " L".join(f"{x},{y}" for x, y in pts)
    b = [f"<defs>{GLOW}</defs>", frame(h)]
    b.append(f'<path d="{d}" fill="none" stroke="{RED}" stroke-width="2" filter="url(#glow)"/>')
    b.append(f'<text x="{W - 24}" y="38" font-size="12" class="b" text-anchor="end" letter-spacing="2"><tspan class="dim">■</tspan> STOP</text>')
    b.append(f'<text x="{W - 24}" y="56" font-size="10" class="dim" text-anchor="end">probe disconnected</text>')
    svg("footer.svg", h, "\n".join(b), "End of transmission", "A flat trace with one last blip. Probe disconnected.")


# ---------------------------------------------------------------- readme


def readme():
    img = lambda src, alt, width="100%": f'<img src="./assets/{src}" width="{width}" align="top" alt="{esc(alt)}">'
    pct = f"{100 / len(C.LINKS):g}%"
    lines = ['<p align="center">',
             f'<a href="https://rocisapps.com">{img("header.svg", f"{C.NAME} ({C.HANDLE}). {C.TAGLINE}.")}</a>',
             "".join(f'<a href="{L["href"]}">{img(f"links/{L["slug"]}.svg", f"{L["sub"]}: {L["label"]}", pct)}</a>' for L in C.LINKS),
             img("stats.svg", "Measurements: live GitHub stats and top languages"),
             img("signal.svg", "Contribution signal: weekly contributions over the last year"),
             img("projects.svg", "Projects")]
    for i in range(0, len(C.PROJECTS), 2):
        lines.append("".join(
            f'<a href="{p["href"]}">{img(f"chips/{p["slug"]}.svg", f"{p["name"]} ({p["status"]}): {p["subtitle"]}", "50%")}</a>'
            for p in C.PROJECTS[i:i + 2]))
    lines += [img("stack.svg", "Tech stack: " + "; ".join(f"{b}: {p}" for _, b, p in C.BOM)),
              img("footer.svg", "Probe disconnected."),
              "</p>", "",
              "<!-- Generated by tools/build.py. Edit tools/content.py, not this file. -->", ""]
    (ROOT / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    s = json.loads(DATA.read_text()) if "--offline" in sys.argv else fetch()
    header()
    links()
    stats(s)
    signal(s)
    section("projects.svg", "ACTIVE COMPONENTS", "click a chip to open it")
    for p in C.PROJECTS:
        chip(p)
    bom()
    footer()
    readme()
    print(f"built {len(list(ASSETS.rglob('*.svg')))} svgs, {s['total']} contributions")


if __name__ == "__main__":
    main()
