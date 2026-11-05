#!/usr/bin/env python3
"""Render assets/github-stats.svg from the GitHub GraphQL API.

Self-hosted replacement for the public github-readme-stats instance, which is
frequently rate-limited. Runs in a GitHub Action with GITHUB_TOKEN.
Shows activity and languages only (no star counts).
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

USER = os.environ.get("GH_USER", "vivtiw")
TOKEN = os.environ["GITHUB_TOKEN"]
OUT = sys.argv[1] if len(sys.argv) > 1 else "assets/github-stats.svg"

QUERY = """
query($login: String!) {
  user(login: $login) {
    createdAt
    contributionsCollection {
      contributionCalendar { totalContributions }
      totalCommitContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      totalIssueContributions
    }
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100, privacy: PUBLIC) {
      totalCount
      nodes {
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


def gql():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(data["errors"])
    return data["data"]["user"]


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main():
    u = gql()
    cc = u["contributionsCollection"]
    langs = {}
    for repo in u["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            n = e["node"]
            cur = langs.setdefault(n["name"], [0, n["color"] or "#8b949e"])
            cur[0] += e["size"]
    top = sorted(langs.items(), key=lambda kv: -kv[1][0])[:6]
    total = sum(v[0] for _, v in top) or 1

    stats = [
        ("Contributions (last year)", cc["contributionCalendar"]["totalContributions"]),
        ("Commits", cc["totalCommitContributions"]),
        ("Pull requests", cc["totalPullRequestContributions"]),
        ("Reviews", cc["totalPullRequestReviewContributions"]),
        ("Public repos", u["repositories"]["totalCount"]),
    ]

    W, H = 840, 200
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        "<style>.t{font:600 15px 'Segoe UI',Inter,Arial,sans-serif;fill:#e2e8f0}"
        ".l{font:400 13px 'Segoe UI',Inter,Arial,sans-serif;fill:#94a3b8}"
        ".v{font:700 13px 'SFMono-Regular',Consolas,Menlo,monospace;fill:#5eead4}</style>",
        f'<rect width="{W}" height="{H}" rx="14" fill="#0f172a" stroke="#1e293b"/>',
        '<text class="t" x="28" y="38">Activity</text>',
        '<text class="t" x="440" y="38">Languages (public repos)</text>',
    ]
    for i, (label, val) in enumerate(stats):
        y = 70 + i * 26
        out.append(f'<text class="l" x="28" y="{y}">{esc(label)}</text>')
        out.append(f'<text class="v" x="380" y="{y}" text-anchor="end">{val:,}</text>')

    # stacked bar
    x = 440
    bar_w = 372
    for name, (size, color) in top:
        w = bar_w * size / total
        out.append(f'<rect x="{x:.1f}" y="54" width="{w:.1f}" height="10" fill="{color}"/>')
        x += w
    for i, (name, (size, color)) in enumerate(top):
        col, row = i % 2, i // 2
        lx, ly = 440 + col * 190, 92 + row * 26
        pct = 100 * size / total
        out.append(f'<circle cx="{lx + 5}" cy="{ly - 4}" r="5" fill="{color}"/>')
        out.append(f'<text class="l" x="{lx + 16}" y="{ly}">{esc(name)} <tspan class="v">{pct:.0f}%</tspan></text>')

    stamp = datetime.now(timezone.utc).strftime("%d %b %Y")
    out.append(f'<text class="l" x="{W - 28}" y="{H - 16}" text-anchor="end" font-size="11">updated {stamp}</text>')
    out.append("</svg>")

    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w") as f:
        f.write("\n".join(out))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
