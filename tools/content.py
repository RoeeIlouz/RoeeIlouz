"""Hand-edited profile content. Live numbers come from build.py; everything else lives here."""

GITHUB_USER = "RoeeIlouz"

NAME = "ROEE ILOUZ"
HANDLE = "ROCI"
TAGLINE = "EE student · indie builder · homelabber"
MISSION = "building apps that get me through college"

# Oscilloscope channel readouts on the right of the header: (channel, label, value, note)
CHANNELS = [
    ("CH1", "APPS", "Flutter · Dart", "Tasks + Schedule"),
    ("CH2", "LAB", "Pi 5 · Debian 13", "30+ containers, 24/7"),
    ("CH3", "AGENTS", "MCP · Claude Code", "agentic dev loops"),
]

STATUS_BAR = ["TIMEBASE 1 semester/div", "TRIG ↑ espresso", "LOC Israel", "rocisapps.com"]

LINKS = [
    {"slug": "apps", "label": "rocisapps.com", "sub": "the apps", "href": "https://rocisapps.com"},
    {"slug": "site", "label": "roee.ilouz.xyz", "sub": "portfolio", "href": "https://roee.ilouz.xyz"},
    {"slug": "x", "label": "@rocisapps", "sub": "on X", "href": "https://x.com/rocisapps"},
    {"slug": "mail", "label": "roee@ilouz.xyz", "sub": "email", "href": "mailto:roee@ilouz.xyz"},
]

# Each project renders as an IC package. status: LIVE | BETA | WIP
PROJECTS = [
    {
        "slug": "rocis-tasks",
        "kind": "ANDROID · WEB",
        "ref": "U1",
        "name": "ROCIs Tasks",
        "status": "LIVE",
        "subtitle": "tasks + calendar on one timeline",
        "desc": "Offline-first planner with natural-language input, checklists and two-way Google Calendar sync.",
        "tags": ["FLUTTER", "FIREBASE", "GCAL SYNC"],
        "href": "https://play.google.com/store/apps/details?id=com.rocisapps.tasks",
        "footer": "Google Play · tasks.rocisapps.com",
    },
    {
        "slug": "rocis-schedule",
        "kind": "ANDROID · iOS",
        "ref": "U2",
        "name": "ROCIs Schedule",
        "status": "BETA",
        "subtitle": "timetable, exams & GPA for students",
        "desc": "Weekly timetable, live exam countdowns, weighted GPA and 1-tap .ics import from Canvas & Moodle. 8 languages, RTL ready.",
        "tags": ["FLUTTER", "SQLITE", "FIRESTORE"],
        "href": "https://github.com/RoeeIlouz/ROCIs-Schedule",
        "footer": "github.com/RoeeIlouz/ROCIs-Schedule",
    },
    {
        "slug": "homelab",
        "kind": "SELF-HOSTED",
        "ref": "U3",
        "name": "Homelab",
        "status": "LIVE",
        "subtitle": "Raspberry Pi 5 production node",
        "desc": "Debian 13 box running 30+ Docker services behind Cloudflare Zero Trust and Twingate, with GitOps backups.",
        "tags": ["DOCKER", "DEBIAN 13", "ZERO TRUST"],
        "href": "https://github.com/RoeeIlouz/Homelab",
        "footer": "github.com/RoeeIlouz/Homelab",
    },
    {
        "slug": "context-menu-editor",
        "kind": "WINDOWS",
        "ref": "U4",
        "name": "Context Menu Editor",
        "status": "LIVE",
        "subtitle": "the Windows right-click menu, cleaned up",
        "desc": "Commands, shell extensions and Win 11 items in one list. Disable, add, back up, undo. irm rocisapps.com/cme | iex",
        "tags": ["POWERSHELL", "WPF", "WIN 11"],
        "href": "https://github.com/RoeeIlouz/ROCIsContextMenu-Editor",
        "footer": "github.com/RoeeIlouz/ROCIsContextMenu-Editor",
    },
]

# Tech stack as a Bill of Materials: (designator, block, parts)
BOM = [
    ("U1-U4", "Languages", "Dart · Python · C · TypeScript · PowerShell · Bash"),
    ("F1", "Frameworks", "Flutter · Provider/Riverpod · Firebase · Astro"),
    ("H1", "Infra", "Debian 13 · Docker Compose · Cloudflare ZT · Twingate · NPM"),
    ("A1", "AI tooling", "Claude Code · MCP servers · multi-agent workflows"),
    ("E1", "EE bench", "circuit analysis · embedded C · mechatronics"),
]

# Generated Flutter runner code and build glue that would skew the language meter.
LANG_IGNORE = {"CMake", "C++", "Swift", "Objective-C", "Batchfile", "HTML", "CSS"}
