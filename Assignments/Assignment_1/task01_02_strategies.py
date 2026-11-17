"""Tasks 1 & 2 - Frequency-planning strategies and governing design parameters.
 * Strategy 1 (iterative): enumerate valid (i, j) cluster sizes, test SIR >= 12 dB
 * Strategy 2: three-sector reuse (two dominant interferers model)
 * Strategy 3 (recursive / hierarchical): repeated cell splitting until demand is met
 * Task 2: how the governing parameter (N, sector discrimination, R) responds to demand
"""
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from cellular_lib import *

HERE = os.path.dirname(os.path.abspath(__file__))
R, AREA = 0.5, 12.0


def strategy1():
    print("STRATEGY 1 - Fixed cluster reuse (iterative procedure)")
    print("  Step 1-2: generate (i,j) -> N, channels/cell, D, Q, SIR (n=4, six interferers)")
    print("  %-6s %-4s %-10s %-9s %-7s %-9s %s" % ("(i,j)", "N", "ch/cell", "D (km)", "Q", "SIR dB", "SIR >= 12 dB ?"))
    rows = []
    seen = set()
    for i in range(1, 4):
        for j in range(0, i + 1):
            N = cluster_size(i, j)
            if N in seen:
                continue
            seen.add(N)
            sdb = to_db(sir_linear(N, 4))
            rows.append((i, j, N, TOTAL_CHANNELS // N, reuse_distance(R, N), math.sqrt(3 * N), sdb))
    rows.sort(key=lambda r: r[2])
    for i, j, N, ch, D, Q, sdb in rows:
        print("  %-6s %-4d %-10d %-9.3f %-7.3f %-9.2f %s" % ((i, j), N, ch, D, Q, sdb, "ACCEPT" if sdb >= SIR_MIN_DB else "reject"))
    ok = [r for r in rows if r[6] >= SIR_MIN_DB]
    best = min(ok, key=lambda r: r[2])
    print("  Step 3-5: smallest accepted cluster = N=%d -> %d channels/cell, SIR %.2f dB" % (best[2], best[3], best[6]))
    return rows


def strategy2():
    print("\nSTRATEGY 2 - Sectorised reuse (3 x 120 deg, two dominant interferers)")
    print("  %-4s %-18s %-18s %s" % ("N", "omni SIR (6 I) dB", "sector SIR (2 I) dB", "gain dB"))
    for N in (3, 4, 7, 12):
        o, s = to_db(sir_linear(N, 4, 6)), to_db(sir_linear(N, 4, 2))
        print("  %-4d %-18.2f %-18.2f %.2f" % (N, o, s, s - o))
    print("  (simplified: real sector SIR needs antenna patterns - see Tasks 8-10 simulator)")


def strategy3(demand=2500.0):
    print("\nSTRATEGY 3 - Hierarchical macro-micro, recursive cell splitting")
    cap0 = 19 * traffic_at_blocking(TOTAL_CHANNELS // 7)

    def split(level, cells, radius, capacity):
        print("  level %d: cells=%-5d R=%.4f km  capacity=%8.2f Erl  demand=%.0f Erl" % (level, cells, radius, capacity, demand))
        if capacity >= demand:
            return level
        return split(level + 1, 4 * cells, radius / 2, 4 * capacity)       # each cell -> 4 children, R/2

    k = split(0, 19, R, cap0)
    print("  recursion stops at level k = %d (ceil(log4(D/C0)) = %d)" % (k, math.ceil(math.log(demand / cap0, 4))))


def task2():
    print("\nTASK 2 - Governing parameter behaviour")
    print("  Fixed reuse: N  -> channels/cell ~ 336/N, D = R*sqrt(3N)")
    print("  %-4s %-9s %-9s %-9s" % ("N", "ch/cell", "D (km)", "SIR dB"))
    for N in (3, 4, 7, 12):
        print("  %-4d %-9d %-9.3f %-9.2f" % (N, TOTAL_CHANNELS // N, reuse_distance(R, N), to_db(sir_linear(N, 4))))
    print("  Macro-micro: cell radius R -> cells for 12 km^2 (area-based count; the splitting recurrence uses 4 x 19 = 76 at R=0.25)")
    print("  %-9s %-10s %-8s" % ("R (km)", "A (km^2)", "cells"))
    for r in (0.5, 0.25, 0.125, 0.0625):
        print("  %-9.4f %-10.5f %-8d" % (r, cell_area(r), math.ceil(AREA / cell_area(r))))


def plots(rows):
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
    Ns = [r[2] for r in rows]
    ax[0].bar([str(n) for n in Ns], [r[6] for r in rows], color="#58c")
    ax[0].axhline(SIR_MIN_DB, color="r", ls="--", label="12 dB target"); ax[0].set_xlabel("Cluster size N"); ax[0].set_ylabel("SIR (dB), n=4")
    ax[0].set_title("Strategy 1: SIR vs N"); ax[0].legend()
    ax[1].bar([str(n) for n in Ns], [r[3] for r in rows], color="#6b8"); ax[1].set_xlabel("Cluster size N"); ax[1].set_ylabel("Channels per cell")
    ax[1].set_title("Strategy 1: channels per cell vs N")
    Rs = [0.5, 0.25, 0.125, 0.0625]
    ax[2].plot(Rs, [math.ceil(AREA / cell_area(r)) for r in Rs], "o-"); ax[2].set_xscale("log", base=2); ax[2].set_yscale("log")
    ax[2].set_xlabel("Cell radius R (km)"); ax[2].set_ylabel("Cells needed for 12 km^2"); ax[2].set_title("Strategy 3: cells vs R"); ax[2].grid(alpha=.3)
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "screenshot_graph.png"), dpi=110); plt.close(fig)


if __name__ == "__main__":
    rows = strategy1()
    strategy2()
    strategy3()
    task2()
    plots(rows)
