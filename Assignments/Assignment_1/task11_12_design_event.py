"""Tasks 11 & 12 - Final hybrid design numbers and the Day-4 stadium-event re-evaluation."""
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "common"))
sys.path.insert(0, os.path.join(HERE, "..", "Task08_09_10_Simulator"))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from cellular_lib import *
from task08_09_10_simulator import sir_samples, stats

R, CELLS = 0.5, 19
A48 = traffic_at_blocking(48)


def task11():
    print("TASK 11.1 - Recommended hybrid design: planning parameters")
    rows = [("Township area", "12 km^2"), ("Available duplex channels", "336"), ("Illustrative cell radius", "0.5 km"),
            ("Cluster size N (baseline)", "7  (i=2, j=1)"), ("Channels per cell", "%d" % (336 // 7)),
            ("Target blocking", "2 %"), ("Minimum SIR", "12 dB"), ("Macro cells (area based)", "%d" % math.ceil(12 / cell_area(R))),
            ("Reference omni SIR (n=4)", "%.2f dB" % to_db(sir_linear(7, 4)))]
    for k, v in rows:
        print("  %-30s %s" % (k, v))

    print("\n  Expected performance of the baseline layer")
    omni, sec = stats(sir_samples(7, 4.0)), stats(sir_samples(7, 4.0, True))
    omni6, sec6 = stats(sir_samples(7, 4.0, False, 6.0)), stats(sir_samples(7, 4.0, True, 6.0))
    print("  capacity at 2 %% blocking : 19 x %.2f = %.1f Erl  (~%d subscribers)" % (A48, CELLS * A48, CELLS * A48 / ERL_PER_USER))
    print("  simulated SIR, omni   N=7 n=4 : mean %.2f dB, 5th pct %.2f dB, outage %.4f (sigma=0) | outage %.4f (sigma=6 dB)" % (omni["mean"], omni["p5"], omni["outage"], omni6["outage"]))
    print("  simulated SIR, sector N=7 n=4 : mean %.2f dB, 5th pct %.2f dB, outage %.4f (sigma=0) | outage %.4f (sigma=6 dB)" % (sec["mean"], sec["p5"], sec["outage"], sec6["outage"]))
    print("  blocking of baseline at 20,000 users: %.4f ; at 30,000 users: %.4f ; at 100,000 users: %.4f"
          % tuple(erlang_b(48, u * ERL_PER_USER / CELLS) for u in (20000, 30000, 100000)))

    print("\n  Alternatives compared (idealised capacity, 100,000 subscribers = 2,500 Erl)")
    print("  %-34s %-12s %-14s %-s" % ("Option", "Capacity", "Users @2%", "Meets 2,500 Erl?"))
    opts = [("Fixed reuse N=7 (baseline)", CELLS * A48), ("Fixed reuse N=4", CELLS * traffic_at_blocking(84)),
            ("Fixed reuse N=3 (SIR 11.3 dB < 12)", CELLS * traffic_at_blocking(112)),
            ("N=7, 3 sectors x 16 ch", CELLS * 3 * traffic_at_blocking(16)), ("Macro-micro, 1 uniform split (x4)", 4 * CELLS * A48),
            ("Selective split f=0.5, 2 rounds", CELLS * A48 * 2.5 ** 2)]
    for name, cap in opts:
        print("  %-34s %-12.1f %-14d %s" % (name, cap, cap / ERL_PER_USER, "yes" if cap >= 2500 else "no"))
    print("  Beyond 100,000 subscribers (idealised, uniform x4 per round, base %.1f Erl):" % (CELLS * A48))
    for k in range(0, 5):
        c = CELLS * A48 * 4 ** k
        print("    after %d round(s): %.0f Erl ~ %d subscribers, %d cells" % (k, c, c / ERL_PER_USER, CELLS * 4 ** k))


def task12():
    print("\nTASK 12.A - Impact analysis")
    ev = 25000 * 0.05
    normal = 20000 * ERL_PER_USER
    print("  event traffic         = 25,000 x 0.05 = %.0f Erl" % ev)
    print("  event traffic density = %.0f / 1 km^2 = %.0f Erl/km^2" % (ev, ev))
    print("  normal traffic        = 20,000 x 0.025 = %.0f Erl ; density = %.0f / 12 = %.2f Erl/km^2" % (normal, normal, normal / 12))
    print("  ratio event/normal density = %.1f (about 30x)" % ((ev / 1) / (normal / 12)))
    hrs = 2 * 4
    print("  event time share = %d h per month of ~730 h = %.1f %%" % (hrs, 100 * hrs / 730))

    print("\nTASK 12.B - Original design under the event (assumptions stated)")
    zone_cells = math.ceil(1.0 / cell_area(R))
    per = ev / zone_cells
    b = erlang_b(48, per)
    print("  assumption: stadium zone (1 km^2) is served by ceil(1/%.4f) = %d original cells, 48 channels each, traffic split equally" % (cell_area(R), zone_cells))
    print("  offered per cell = %.1f Erl -> Erlang-B blocking = %.4f ; carried traffic = %.1f of %.0f Erl (%.1f %%)"
          % (per, b, zone_cells * per * (1 - b), ev, 100 * (1 - b)))
    print("  event cannot be carried by the entire licensed pool in one cell: channels for 1,250 Erl at 2 %% = %d  (> 336 available)" % channels_needed(ev))
    print("  event traffic (%.0f Erl) > whole-township baseline capacity (%.1f Erl)" % (ev, CELLS * A48))

    print("\nTASK 12.C - Temporary micro-cell / COW plan (cell count by reuse option)")
    print("  %-4s %-8s %-12s %-13s %-9s %-14s %-9s %s" % ("N", "ch/cell", "A@2% (Erl)", "cells needed", "R (km)", "reuse D (km)", "SIR dB", "SIR >= 12 dB"))
    plan = {}
    for N in (3, 4, 7, 12):
        ch = TOTAL_CHANNELS // N
        A = traffic_at_blocking(ch)
        m = math.ceil(ev / A)
        r = math.sqrt(1.0 / (m * 1.5 * math.sqrt(3)))
        sdb = to_db(sir_linear(N, 4))
        plan[N] = m
        print("  %-4d %-8d %-12.2f %-13d %-9.3f %-14.3f %-9.2f %s" % (N, ch, A, m, r, reuse_distance(r, N), sdb, "yes" if sdb >= SIR_MIN_DB else "no"))
    print("  With N=7 reuse: %d temporary micro cells of ~%.0f m radius, each with 48 channels, reuse distance ~%.0f m." % (plan[7], 1000 * math.sqrt(1.0 / (plan[7] * 1.5 * math.sqrt(3))), 1000 * reuse_distance(math.sqrt(1.0 / (plan[7] * 1.5 * math.sqrt(3))), 7)))
    print("  Blocking vs number of identical temporary cells (48 ch each, 1,250 Erl split equally):")
    for m in (2, 10, 20, 30, 33, 40):
        print("    %2d cells -> %.1f Erl/cell -> blocking %.4f" % (m, ev / m, erlang_b(48, ev / m)))

    print("\nTASK 12.D - Decision logic")
    print("  retain unchanged   : blocking %.2f in the stadium zone      -> rejected" % b)
    print("  temporary modify   : needs ~%d micro cells / COWs for %d h, 2x per month -> RECOMMENDED" % (plan[7], 4))
    print("  permanent redesign : would idle %.1f %% of the time as event capacity -> not justified by events alone" % (100 - 100 * hrs / 730))

    fig, ax = plt.subplots(1, 3, figsize=(16, 4.3))
    ax[0].bar(["Normal township\n(500 Erl / 12 km^2)", "Stadium event\n(1,250 Erl / 1 km^2)"], [normal / 12, ev], color=["#58c", "#e55"])
    ax[0].set_ylabel("Traffic density (Erl/km^2)"); ax[0].set_title("Event is ~30x denser"); ax[0].set_yscale("log")
    ms = np.arange(2, 61)
    ax[1].plot(ms, [erlang_b(48, ev / m) for m in ms]); ax[1].axhline(.02, color="r", ls="--"); ax[1].axvline(plan[7], color="k", ls=":")
    ax[1].set_xlabel("Number of temporary 48-channel cells"); ax[1].set_ylabel("Blocking"); ax[1].set_title("Event blocking vs temporary cells (N=7)"); ax[1].set_yscale("log"); ax[1].set_ylim(1e-4, 1)
    Ns = [3, 4, 7, 12]
    ax[2].bar([str(n) for n in Ns], [plan[n] for n in Ns], color="#6b8"); ax[2].set_xlabel("Cluster size N"); ax[2].set_ylabel("Cells needed for 1,250 Erl"); ax[2].set_title("Temporary cells needed vs reuse plan")
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "screenshot_graph.png"), dpi=110); plt.close(fig)


if __name__ == "__main__":
    task11()
    task12()
