"""Tasks 6 & 7 - Cell-splitting recurrences, closed forms and minimum rounds."""
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from cellular_lib import *

HERE = os.path.dirname(os.path.abspath(__file__))
N0, R0, N_PATH = 19, 0.5, 4
C0 = N0 * traffic_at_blocking(TOTAL_CHANNELS // 7)         # 19 cells x Erlang-B capacity of 48 channels
P0 = 1.0                                                   # relative transmit power


def uniform_iter(rounds):
    out = [(0, N0, R0, C0, P0)]
    for k in range(1, rounds + 1):
        _, n, r, c, p = out[-1]
        out.append((k, 4 * n, r / 2, 4 * c, p / 2 ** N_PATH))      # N_k=4N, R_k=R/2, C_k=4C, P_k=P/2^n
    return out


def selective_iter(rounds, f):
    out = [(0, N0, C0)]
    for k in range(1, rounds + 1):
        _, n, c = out[-1]
        out.append((k, n * (1 + 3 * f), c * (1 + 3 * f)))
    return out


def min_rounds_uniform(D):
    return max(0, math.ceil(math.log(D / C0, 4) - 1e-12))


def min_rounds_selective(D, f):
    return max(0, math.ceil(math.log(D / C0) / math.log(1 + 3 * f) - 1e-12))


def main():
    print("Base case: N0=%d cells, R0=%.2f km, C0 = 19 x A(48 ch, 2%%) = %.2f Erl, P0 = 1 (relative)" % (N0, R0, C0))
    print("  (the report's provisional value is 729.41 Erl; the unrounded Erlang-B result is %.2f)" % C0)

    print("\nTASK 6.1 - Uniform splitting  (N_k=4N_(k-1), R_k=R_(k-1)/2, C_k=4C_(k-1), P_k=P_(k-1)/2^n, n=4)")
    print("  %-3s %-7s %-9s %-11s %-12s %-10s %-14s" % ("k", "cells", "R (km)", "C_k (Erl)", "P_k (rel.)", "new cells", "boundary load"))
    prev = None
    for k, n, r, c, p in uniform_iter(4):
        new = 0 if prev is None else n - prev
        print("  %-3d %-7d %-9.4f %-11.1f %-12.6f %-10d x%-4d" % (k, n, r, c, p, new, 2 ** k))
        prev = n
    print("  closed forms check: C_k = 4^k C0, N_k = 4^k N0 ->", all(abs(c - 4 ** k * C0) < 1e-6 and n == 4 ** k * N0 for k, n, _, c, _ in uniform_iter(4)))
    print("  boundary (handoff) load ~ 1/R_k = 2^k times the original (same user speed)")

    print("\nTASK 6.2 / 7.3 - Selective splitting  (C_k = C0 (1+3f)^k)")
    for f in (0.25, 0.5, 1.0):
        row = selective_iter(4, f)
        print("  f=%.2f : " % f + "  ".join("k=%d: %.1f Erl / %.0f cells" % (k, c, n) for k, n, c in row))

    print("\nTASK 7 - Minimum rounds  k_min = ceil(log(D/C0)/log(multiplier))")
    print("  %-14s %-10s %-10s %-14s %-14s" % ("subscribers", "D (Erl)", "uniform", "selective f=.5", "selective f=.25"))
    for users in (20000, 50000, 100000, 250000, 1000000):
        D = users * ERL_PER_USER
        print("  %-14d %-10.0f %-10d %-14d %-14d" % (users, D, min_rounds_uniform(D), min_rounds_selective(D, .5), min_rounds_selective(D, .25)))
    D = 2500
    print("\n  Worked example D = 100,000 x 0.025 = 2,500 Erl:")
    print("   uniform : log4(%.1f/%.2f) = %.3f -> k_min = %d   (C_1 = %.2f Erl)" % (D, C0, math.log(D / C0, 4), min_rounds_uniform(D), 4 * C0))
    print("   f = 0.5 : log(%.1f/%.2f)/log(2.5) = %.3f -> k_min = %d   (C_2 = %.2f Erl)" % (D, C0, math.log(D / C0) / math.log(2.5), min_rounds_selective(D, .5), C0 * 2.5 ** 2))
    print("  Note: capacity gain is idealised (assumes children can reuse the full channel pool without extra interference).")

    fig, ax = plt.subplots(1, 3, figsize=(16, 4.3))
    ks = list(range(0, 5))
    ax[0].plot(ks, [c for _, _, _, c, _ in uniform_iter(4)], "o-", label="uniform (x4)")
    for f in (0.25, 0.5):
        ax[0].plot(ks, [c for _, _, c in selective_iter(4, f)], "o-", label="selective f=%.2f" % f)
    ax[0].axhline(2500, color="k", ls="--", label="100,000 users = 2,500 Erl"); ax[0].set_yscale("log"); ax[0].set_xlabel("Splitting round k"); ax[0].set_ylabel("Capacity (Erl)"); ax[0].legend(fontsize=8); ax[0].set_title("Capacity vs rounds")
    ax[1].plot(ks, [n for _, n, _, _, _ in uniform_iter(4)], "o-", label="uniform")
    ax[1].plot(ks, [n for _, n, _ in selective_iter(4, .5)], "o-", label="f=0.5"); ax[1].set_yscale("log"); ax[1].set_xlabel("Round k"); ax[1].set_ylabel("Number of cells"); ax[1].set_title("Cell count growth"); ax[1].legend()
    ax[2].plot(ks, [p for _, _, _, _, p in uniform_iter(4)], "o-"); ax[2].set_yscale("log"); ax[2].set_xlabel("Round k"); ax[2].set_ylabel("Relative transmit power P_k/P_0"); ax[2].set_title("Power falls by 2^n = 16 per round (n=4)")
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "screenshot_graph.png"), dpi=110); plt.close(fig)


if __name__ == "__main__":
    main()
