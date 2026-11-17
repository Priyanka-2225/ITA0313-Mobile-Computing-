"""Tasks 4 & 5 - Best/average/worst-case behaviour and scaling / sensitivity analysis."""
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from cellular_lib import *

HERE = os.path.dirname(os.path.abspath(__file__))
R, CELLS = 0.5, 19


def task4():
    print("TASK 4.1 - Mobile position (P_r ~ d^-n)")
    for n in (2.5, 3, 4):
        print("  n=%.1f: doubling distance -> power x %.4f = %.2f dB" % (n, 0.5 ** n, 10 * n * math.log10(0.5)))
    N, n = 7, 4
    D = reuse_distance(R, N)
    print("\n  SIR of a mobile at distance d from its BS, N=7, n=4, six first-tier interferers:")
    print("  best/avg/worst use the interferer geometry D+d / D / D-d")
    print("  %-26s %-8s %-10s" % ("Position", "d (km)", "SIR dB"))
    for name, d in (("Best (near BS)", 0.1 * R), ("Average (mid-cell)", 0.6 * R), ("Worst (cell edge)", R)):
        pr = d ** -n
        i_near = 2 * (D - d) ** -n + 2 * D ** -n + 2 * (D + d) ** -n     # simplified spread of the 6 interferers
        print("  %-26s %-8.3f %-10.2f" % (name, d, to_db(pr / i_near)))

    print("\n  Shadowing (log-normal, sigma = 6 dB), cell-edge mobile, 20000 samples, seed 1")
    rng = np.random.default_rng(1)
    d = R
    sh = rng.normal(0, 6, (20000, 7))
    p = 10 ** (sh[:, 0] / 10) * d ** -n
    i = sum(10 ** (sh[:, k] / 10) * D ** -n for k in range(1, 7))
    s = 10 * np.log10(p / i)
    print("  mean %.2f dB, 5th percentile %.2f dB, outage P(SIR<12 dB) = %.3f" % (s.mean(), np.percentile(s, 5), (s < SIR_MIN_DB).mean()))

    print("\nTASK 4.2 - Traffic and blocking per cell (19 cells, N=7 -> 48 channels/cell)")
    print("  %-28s %-12s %-12s %-10s" % ("Case", "Total Erl", "Erl / cell", "Blocking"))
    for name, users in (("1,000 subscribers", 1000), ("10,000 subscribers", 10000), ("20,000 subscribers", 20000), ("100,000 subscribers", 100000)):
        A = users * ERL_PER_USER
        print("  %-28s %-12.0f %-12.2f %-10.4f" % (name, A, A / CELLS, erlang_b(48, A / CELLS)))
    return rng


def task5():
    print("\nTASK 5.1 - Scaling relations: ch/cell ~ 1/N ; D/R = sqrt(3N) ; SIR ~ N^(n/2) ; cells ~ 1/R^2")
    print("\nTASK 5.2 - Subscriber growth: blocking per cell (uniform load over 19 cells)")
    users = [1000, 10000, 20000, 100000]
    print("  %-10s %-10s" % ("users", "Erlangs") + "".join("N=%-2d (%3d ch)  " % (N, TOTAL_CHANNELS // N) for N in (3, 4, 7, 12)))
    for u in users:
        A = u * ERL_PER_USER
        print("  %-10d %-10.0f" % (u, A) + "".join("%-16.4f" % erlang_b(TOTAL_CHANNELS // N, A / CELLS) for N in (3, 4, 7, 12)))
    print("\n  Practical limit = users served at <= 2 % blocking by the 19-cell macro layer")
    for N in (3, 4, 7, 12):
        cap = CELLS * traffic_at_blocking(TOTAL_CHANNELS // N)
        print("  N=%-2d : capacity %.1f Erl -> about %d subscribers; 100,000 users need x%.1f more capacity"
              % (N, cap, cap / ERL_PER_USER, 2500 / cap))
    print("\nTASK 5.3 - Path-loss sensitivity (N=7, six interferers)")
    for n in (2.5, 3, 4):
        print("  n = %-3s -> SIR = %.2f dB %s" % (n, to_db(sir_linear(7, n)), "(below 12 dB target)" if to_db(sir_linear(7, n)) < SIR_MIN_DB else ""))
    print("\n  Minimum N meeting 12 dB for each n (six interferers):")
    for n in (2.5, 3, 4):
        for N in (1, 3, 4, 7, 9, 12, 13, 19, 21):
            if to_db(sir_linear(N, n)) >= SIR_MIN_DB:
                print("  n = %-3s -> N = %d (SIR %.2f dB, %d ch/cell)" % (n, N, to_db(sir_linear(N, n)), TOTAL_CHANNELS // N)); break


def plots():
    fig, ax = plt.subplots(1, 3, figsize=(16, 4.3))
    ns = np.linspace(2, 5, 31)
    for N in (3, 4, 7, 12):
        ax[0].plot(ns, [to_db(sir_linear(N, n)) for n in ns], label="N=%d" % N)
    ax[0].axhline(12, color="k", ls="--"); ax[0].set_xlabel("Path-loss exponent n"); ax[0].set_ylabel("SIR (dB)"); ax[0].set_title("SIR vs path-loss exponent"); ax[0].legend()
    ax[1].set_yscale("log")
    us = np.array([1000, 5000, 10000, 20000, 50000, 100000])
    for N in (3, 4, 7, 12):
        ax[1].plot(us, [erlang_b(TOTAL_CHANNELS // N, u * ERL_PER_USER / CELLS) for u in us], "o-", label="N=%d" % N)
    ax[1].axhline(0.02, color="k", ls="--"); ax[1].set_xscale("log"); ax[1].set_xlabel("Subscribers"); ax[1].set_ylabel("Blocking per cell"); ax[1].set_title("Blocking vs subscribers (19 cells)"); ax[1].legend()
    xs = np.linspace(0.2, 3, 60)
    ax[2].plot(xs, [10 * 4 * math.log10(1 / x) for x in xs], label="n=4"); ax[2].plot(xs, [10 * 3 * math.log10(1 / x) for x in xs], label="n=3")
    ax[2].set_xlabel("Distance / reference distance"); ax[2].set_ylabel("Relative received power (dB)"); ax[2].set_title("Path loss: 12.04 dB per doubling (n=4)"); ax[2].legend(); ax[2].grid(alpha=.3)
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "screenshot_graph.png"), dpi=110); plt.close(fig)


if __name__ == "__main__":
    task4()
    task5()
    plots()
