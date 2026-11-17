"""Runs every question's program, stores the console output (output.txt),
renders a terminal-style screenshot of that run (screenshot_output.png) and
draws a result graph (screenshot_graph.png) for each question.

Usage:  python3 generate_all.py        (needs: Python 3, Pillow, matplotlib)
"""
import math, os, subprocess, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
JOBS = [
    ("Q1_Wireless_Mobility", "q1_mobility.py"),
    ("Q2_Mobile_IP", "q2_mobile_ip.py"),
    ("Q3_Cellular_vs_AdHoc", "q3_architecture.py"),
    ("Q4_Mobile_IP_Healthcare", "q4_healthcare.py"),
    ("Q5_DSDV", "q5_dsdv.py"),
    ("Q6_AODV", "q6_aodv.py"),
    ("Q7_Emergency_Network", "q7_emergency.py"),
]
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"


def terminal_png(cmd, text, path):
    f, fb = ImageFont.truetype(MONO, 15), ImageFont.truetype(MONO_B, 15)
    lines = text.rstrip("\n").split("\n")
    cw, lh, pad, bar = f.getlength("M"), 21, 18, 34
    w = int(max(len(l) for l in lines + ["$ " + cmd]) * cw + 2 * pad)
    h = bar + pad * 2 + lh * (len(lines) + 2)
    img = Image.new("RGB", (w, h), (30, 30, 30))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, bar], fill=(58, 58, 58))
    for i, c in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
        d.ellipse([14 + i * 22, 11, 26 + i * 22, 23], fill=c)
    d.text((w // 2 - 120, 8), "Terminal - " + cmd, font=f, fill=(200, 200, 200))
    y = bar + pad
    d.text((pad, y), "$ python3 " + cmd, font=fb, fill=(120, 220, 120))
    y += lh
    for l in lines:
        col = (235, 235, 235)
        if l.startswith(("PART", "Algorithm", "Failure", "Delivery", "Handoff", "Control", "Step", "[")):
            col = (120, 190, 255)
        d.text((pad, y), l, font=f, fill=col)
        y += lh
    d.text((pad, y + 4), "$ _", font=fb, fill=(120, 220, 120))
    img.save(path)


def g_q1(p):
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
    ax[0].bar(["Pedestrian\n1.5 m/s", "Slow vehicle\n15 m/s", "Fast vehicle\n30 m/s"], [0.11, 1.12, 2.25], color=["#4c9", "#fb4", "#e55"])
    ax[0].set_ylabel("Loss due to handoff (%)"); ax[0].set_title("Q1 Part A - handoff loss vs speed")
    for i, v in enumerate([0.11, 1.12, 2.25]): ax[0].text(i, v + .03, "%.2f %%" % v, ha="center")
    xs = list(range(0, 361, 2))
    for n, c in (("AP-1", 0), ("AP-2", 180), ("AP-3", 360)):
        ax[1].plot(xs, [-40 - 20 * math.log10(max(abs(x - c), 1)) for x in xs], label=n)
    ax[1].axhline(-80, color="k", ls="--", label="MIN_SIGNAL"); ax[1].set_ylim(-100, -40)
    for x in (115.5, 294.0): ax[1].axvline(x, color="r", ls=":")
    ax[1].set_xlabel("Position x (m)"); ax[1].set_ylabel("RSS (dBm)"); ax[1].set_title("RSS and handoff points (red) at 15 m/s"); ax[1].legend()
    fig.tight_layout(); fig.savefig(p, dpi=110); plt.close(fig)


def g_q2(p):
    sizes = [50, 100, 200, 500, 1000]
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(sizes, [2000 / s for s in sizes], "o-"); ax.set_xlabel("Payload (bytes)"); ax.set_ylabel("Tunnel overhead (%)")
    ax.set_title("Q2 - IP-in-IP overhead (20 B header)"); ax.grid(alpha=.3)
    for s in sizes: ax.annotate("%.0f %%" % (2000 / s), (s, 2000 / s), textcoords="offset points", xytext=(5, 6))
    fig.tight_layout(); fig.savefig(p, dpi=110); plt.close(fig)


def g_q3(p):
    ks = [1, 2, 3, 4, 5]
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.bar([str(k) for k in ks], [1 / k for k in ks], color="#58c"); ax.set_xlabel("Hops in ad hoc route"); ax.set_ylabel("Relative throughput")
    ax.set_title("Q3 - multi-hop capacity (ad hoc)")
    fig.tight_layout(); fig.savefig(p, dpi=110); plt.close(fig)


def g_q4(p):
    parts = [("access", 30), ("core", 30), ("HA detour", 40), ("tunnel", 5)]
    fig, ax = plt.subplots(figsize=(8, 3.2)); left = 0
    for (n, v), c in zip(parts, ("#58c", "#6b8", "#fb4", "#e66")):
        ax.barh(["one-way delay"], [v], left=left, color=c, label="%s %d ms" % (n, v)); left += v
    ax.axvline(150, color="k", ls="--"); ax.text(151, 0.32, "150 ms target"); ax.set_xlim(0, 200)
    ax.set_title("Q4 - delay budget = %d ms" % left); ax.legend(loc="lower right", ncol=2); ax.set_xlabel("ms")
    fig.tight_layout(); fig.savefig(p, dpi=110); plt.close(fig)


def g_q5(p):
    ns = list(range(10, 101, 10))
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(ns, [n * n * 12 / 15 for n in ns], "o-"); ax.set_xlabel("Nodes N"); ax.set_ylabel("Control overhead (B/s)")
    ax.set_title("Q5 - DSDV overhead grows as O(N^2)"); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(p, dpi=110); plt.close(fig)


def topo(ax, pos, links, hi=(), dead=(), title=""):
    for a, b in links:
        ax.plot(*zip(pos[a], pos[b]), color="#d33" if (a, b) in hi or (b, a) in hi else "#888", lw=3 if (a, b) in hi or (b, a) in hi else 1.5)
    for a, b in dead:
        ax.plot(*zip(pos[a], pos[b]), color="#d33", ls=":", lw=2)
    for n, (x, y) in pos.items():
        ax.scatter(x, y, s=900, color="#9cf", zorder=3, edgecolor="k"); ax.text(x, y, n, ha="center", va="center", fontweight="bold", zorder=4)
    ax.margins(0.15); ax.set_title(title); ax.axis("off")


def g_q6(p):
    pos = {"S": (0, 1), "A": (1, 2), "B": (1, 0), "C": (2, 0), "D": (3, 1)}
    links = [("S", "A"), ("A", "D"), ("S", "B"), ("B", "C"), ("C", "D")]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    topo(ax[0], pos, links, hi=[("S", "A"), ("A", "D")], title="RREQ id=1 -> RREP: route S-A-D (2 hops)")
    topo(ax[1], pos, [l for l in links if l != ("A", "D")], hi=[("S", "B"), ("B", "C"), ("C", "D")], dead=[("A", "D")],
         title="Link A-D breaks -> RERR -> RREQ id=2: S-B-C-D")
    fig.tight_layout(); fig.savefig(p, dpi=110); plt.close(fig)


def g_q7(p):
    sys.path.insert(0, os.path.join(ROOT, "Q7_Emergency_Network"))
    import q7_emergency as q
    fig, ax = plt.subplots(figsize=(9, 5.5))
    z = q.Zone()
    for a, nb in z.links().items():
        for b in nb:
            if a < b: ax.plot(*zip(z.pos[a], z.pos[b]), color="#aaa")
    for n, (x, y) in z.pos.items():
        gw = n in q.GATEWAYS
        ax.scatter(x, y, s=1100, color="#fc6" if gw else "#9cf", edgecolor="k", zorder=3)
        ax.text(x, y, n, ha="center", va="center", fontsize=8, fontweight="bold", zorder=4)
    ax.set_title("Q7 - emergency zone: ad hoc links (range %d m); gateways (orange) connect to EOC/HA" % q.RANGE); ax.axis("equal"); ax.axis("off")
    fig.tight_layout(); fig.savefig(p, dpi=110); plt.close(fig)


GRAPHS = {"Q1": g_q1, "Q2": g_q2, "Q3": g_q3, "Q4": g_q4, "Q5": g_q5, "Q6": g_q6, "Q7": g_q7}

for folder, script in JOBS:
    d = os.path.join(ROOT, folder)
    out = subprocess.run([sys.executable, script], cwd=d, capture_output=True, text=True, check=True).stdout
    open(os.path.join(d, "output.txt"), "w", encoding="utf-8").write(out)
    terminal_png(script, out, os.path.join(d, "screenshot_output.png"))
    GRAPHS[folder[:2]](os.path.join(d, "screenshot_graph.png"))
    print("done", folder)
