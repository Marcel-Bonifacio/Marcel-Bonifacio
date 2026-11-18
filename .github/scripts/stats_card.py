"""Build an 8-bit GitHub stats card (SVG) from the GitHub GraphQL API.

Usage: GITHUB_TOKEN=... python3 stats_card.py <username> <output.svg>
Uses only the standard library so it runs on a bare GitHub Actions runner.
"""
import datetime
import json
import os
import random
import sys
import urllib.request

USER, OUT = sys.argv[1], sys.argv[2]
TOKEN = os.environ["GITHUB_TOKEN"]

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      restrictedContributionsCount
      contributionCalendar { totalContributions }
    }
    repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false) {
      nodes { languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
        edges { size node { name color } } } }
    }
  }
}
"""


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "User-Agent": "profile-stats-card"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if data.get("errors") or not data.get("data", {}).get("user"):
        sys.exit(f"GraphQL error: {data.get('errors')}")
    return data["data"]["user"]


# ---------------- 3x5 pixel font ----------------
FONT = {
    "A": [".X.", "X.X", "XXX", "X.X", "X.X"], "B": ["XX.", "X.X", "XX.", "X.X", "XX."],
    "C": [".XX", "X..", "X..", "X..", ".XX"], "D": ["XX.", "X.X", "X.X", "X.X", "XX."],
    "E": ["XXX", "X..", "XX.", "X..", "XXX"], "F": ["XXX", "X..", "XX.", "X..", "X.."],
    "G": [".XX", "X..", "X.X", "X.X", ".XX"], "H": ["X.X", "X.X", "XXX", "X.X", "X.X"],
    "I": ["XXX", ".X.", ".X.", ".X.", "XXX"], "J": ["..X", "..X", "..X", "X.X", ".X."],
    "K": ["X.X", "X.X", "XX.", "X.X", "X.X"], "L": ["X..", "X..", "X..", "X..", "XXX"],
    "M": ["X.X", "XXX", "XXX", "X.X", "X.X"], "N": ["XX.", "X.X", "X.X", "X.X", "X.X"],
    "O": [".X.", "X.X", "X.X", "X.X", ".X."], "P": ["XX.", "X.X", "XX.", "X..", "X.."],
    "Q": [".X.", "X.X", "X.X", "XX.", ".XX"], "R": ["XX.", "X.X", "XX.", "X.X", "X.X"],
    "S": [".XX", "X..", ".X.", "..X", "XX."], "T": ["XXX", ".X.", ".X.", ".X.", ".X."],
    "U": ["X.X", "X.X", "X.X", "X.X", "XXX"], "V": ["X.X", "X.X", "X.X", "X.X", ".X."],
    "W": ["X.X", "X.X", "XXX", "XXX", "X.X"], "X": ["X.X", "X.X", ".X.", "X.X", "X.X"],
    "Y": ["X.X", "X.X", ".X.", ".X.", ".X."], "Z": ["XXX", "..X", ".X.", "X..", "XXX"],
    "0": ["XXX", "X.X", "X.X", "X.X", "XXX"], "1": [".X.", "XX.", ".X.", ".X.", "XXX"],
    "2": ["XX.", "..X", ".X.", "X..", "XXX"], "3": ["XX.", "..X", ".X.", "..X", "XX."],
    "4": ["X.X", "X.X", "XXX", "..X", "..X"], "5": ["XXX", "X..", "XX.", "..X", "XX."],
    "6": [".XX", "X..", "XXX", "X.X", "XXX"], "7": ["XXX", "..X", ".X.", ".X.", ".X."],
    "8": ["XXX", "X.X", "XXX", "X.X", "XXX"], "9": ["XXX", "X.X", "XXX", "..X", "XX."],
    "%": ["X.X", "..X", ".X.", "X..", "X.X"], "+": ["...", ".X.", "XXX", ".X.", "..."],
    "#": ["X.X", "XXX", "X.X", "XXX", "X.X"], "-": ["...", "...", "XXX", "...", "..."],
    ".": ["...", "...", "...", "...", ".X."], ":": ["...", ".X.", "...", ".X.", "..."],
    "/": ["..X", "..X", ".X.", "X..", "X.."], " ": ["...", "...", "...", "...", "..."],
}


def text_width(s, size):
    return len(s) * 4 * size - size


def pixel_text(s, x, y, size, fill, anchor="start"):
    s = s.upper()
    if anchor == "end":
        x -= text_width(s, size)
    rects = []
    for i, ch in enumerate(s):
        for r, row in enumerate(FONT.get(ch, FONT[" "])):
            for c, v in enumerate(row):
                if v == "X":
                    rects.append(f'<rect x="{x + (i * 4 + c) * size}" y="{y + r * size}" width="{size}" height="{size}"/>')
    return f'<g fill="{fill}">{"".join(rects)}</g>'


def fmt(n):
    return f"{n / 1000:.1f}K" if n >= 10000 else str(n)


def build(u):
    cc = u["contributionsCollection"]
    cal = cc["contributionCalendar"]
    langs = {}
    for repo in u["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            name = e["node"]["name"]
            size, color = langs.get(name, (0, e["node"]["color"] or "#8b949e"))
            langs[name] = (size + e["size"], color)
    total = sum(s for s, _ in langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1][0])[:6]
    stats = [
        ("CONTRIBUTIONS", cal["totalContributions"], "#4cc9f0"),
        ("COMMITS", cc["totalCommitContributions"] + cc["restrictedContributionsCount"], "#ffd166"),
        ("PULL REQUESTS", cc["totalPullRequestContributions"], "#f72585"),
        ("LANGUAGES", len(langs), "#06d6a0"),
    ]

    W, H = 900, 236
    BLUES = ["#90e0ef", "#00b4d8", "#0096c7", "#3a86ff", "#4361ee", "#3f37c9"]
    out = []
    add = out.append
    add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">')
    add(f'<title id="t">{USER} GitHub stats</title>')
    add(f'<desc id="d">8-bit GitHub stats card for {USER}: {stats[0][1]} contributions, {stats[1][1]} commits and '
        f'{stats[2][1]} pull requests in the last 12 months, written in {stats[3][1]} languages; top languages: '
        f'{", ".join(n for n, _ in top)}.</desc>')
    add("<style>.tw{animation:tw 2s ease-in-out infinite}@keyframes tw{50%{opacity:.15}}"
        ".px{opacity:0;animation:show .01s linear forwards}@keyframes show{to{opacity:1}}"
        "@media (prefers-reduced-motion:reduce){*{animation:none!important}.px{opacity:1}}</style>")
    add('<defs><linearGradient id="rb" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="900" y2="0">'
        + "".join(f'<stop offset="{i / (len(BLUES) - 1):.3f}" stop-color="{c}"/>' for i, c in enumerate(BLUES))
        + '</linearGradient><linearGradient id="bgg" x1="0" y1="0" x2="0" y2="1">'
          '<stop offset="0" stop-color="#0b1d4f"/><stop offset="1" stop-color="#020617"/></linearGradient>'
          f'<clipPath id="clip"><rect x="2" y="2" width="{W - 4}" height="{H - 4}" rx="12"/></clipPath></defs>')
    add(f'<rect x="2" y="2" width="{W - 4}" height="{H - 4}" rx="12" fill="url(#bgg)" stroke="url(#rb)" stroke-width="3"/>')
    add('<g clip-path="url(#clip)">')

    rnd = random.Random(7)
    for _ in range(30):
        add(f'<rect class="tw" x="{rnd.randrange(10, W - 10, 2)}" y="{rnd.randrange(10, H - 10, 2)}" width="2" height="2" '
            f'fill="{rnd.choice(BLUES + ["#ffffff"])}" style="animation-duration:{rnd.uniform(1.4, 3.6):.2f}s;'
            f'animation-delay:-{rnd.uniform(0, 3):.2f}s"/>')

    # HUD + walls
    add(pixel_text("PLAYER STATS", 26, 16, 3, "#90e0ef"))
    add(pixel_text("LAST 12 MONTHS", W - 26, 18, 2, "#8b949e", anchor="end"))
    for y in (42, 200):
        add("".join(f'<rect x="{x}" y="{y}" width="6" height="6" fill="url(#rb)"/>' for x in range(14, W - 14, 9)))

    # stats row
    for i, (label, value, color) in enumerate(stats):
        x, y = 30 + i * 215, 62
        add(pixel_text(label, x, y, 2, "#8b949e"))
        add(pixel_text(fmt(value), x + 3, y + 21, 6, "#020617"))  # drop shadow
        add(pixel_text(fmt(value), x, y + 18, 6, color))

    # top languages: pixel loading bar that fills block by block, then a legend
    add(pixel_text("TOP LANGUAGES", 30, 126, 2, "#8b949e"))
    blocks = 84
    segs = []
    for name, (size, color) in top:
        segs += [color] * round(size / total * blocks)
    segs = segs[:blocks]
    add("".join(f'<rect x="{30 + i * 10}" y="144" width="8" height="14" fill="#152553"/>' for i in range(blocks)))
    add("".join(f'<rect class="px" x="{30 + i * 10}" y="144" width="8" height="14" fill="{c}" '
                f'style="animation-delay:{0.3 + i * 0.03:.2f}s"/>' for i, c in enumerate(segs)))
    for i, (name, (size, color)) in enumerate(top):
        lx = 30 + i * 140
        add(f'<rect x="{lx}" y="170" width="10" height="10" fill="{color}"/>')
        add(pixel_text(f"{name} {size / total * 100:.0f}%", lx + 16, 170, 2, "#e6edf3"))

    add(pixel_text(f"UPDATED {datetime.date.today().isoformat()}", W - 26, 216, 2, "#4361ee", anchor="end"))
    add("</g></svg>")
    return "".join(out)


svg = build(fetch())
with open(OUT, "w", encoding="utf-8") as f:
    f.write(svg)
print(f"wrote {OUT} ({len(svg) // 1024} KB)")
