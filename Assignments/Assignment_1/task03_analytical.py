"""Task 3 - Analytical capacity and interference functions (all formulas of Section 3)."""
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from cellular_lib import *

HERE = os.path.dirname(os.path.abspath(__file__))
R, AREA = 0.5, 12.0


def main():
    print("3.1 Hexagonal geometry and coverage")
    a = cell_area(R)
    print("  A_cell = (3*sqrt(3)/2) R^2 = %.4f km^2  (R = %.1f km)" % (a, R))
    print("  cells = 12 / %.4f = %.2f -> plan %d cells" % (a, AREA / a, math.ceil(AREA / a)))

    print("\n3.2 Cluster size and reuse distance (i=2, j=1)")
    N = cluster_size(2, 1)
    print("  N = i^2 + ij + j^2 = %d" % N)
    print("  D = R*sqrt(3N) = %.3f km ;  Q = D/R = %.3f" % (reuse_distance(R, N), math.sqrt(3 * N)))

    print("\n3.3 Channels per cell")
    ch = TOTAL_CHANNELS // N
    print("  S/N = %d/%d = %d channels per cell" % (TOTAL_CHANNELS, N, ch))

    print("\n3.4 Erlang-B")
    A2 = traffic_at_blocking(ch)
    print("  B(48, A) = 2 %% -> offered traffic per cell A = %.3f Erlangs" % A2)
    print("  check: erlang_b(48, %.3f) = %.5f" % (A2, erlang_b(ch, A2)))
    cap = math.ceil(AREA / a) * A2
    print("  ideal system capacity = 19 x %.3f = %.2f Erlangs  (~%d subscribers at 0.025 Erl)" % (A2, cap, cap / ERL_PER_USER))

    print("\n3.5 Co-channel SIR")
    s = sir_linear(7, 4, 6)
    print("  omni  : (3N)^(n/2)/I0 = 21^2/6 = %.1f -> %.2f dB" % (s, to_db(s)))
    s2 = sir_linear(7, 4, 2)
    print("  sector: 21^2/2 = %.1f -> %.2f dB (simplified two-interferer model)" % (s2, to_db(s2)))

    print("\n3.6 Strategy interpretation (numbers for n=4, I0=6)")
    print("  %-4s %-9s %-11s %-9s %-14s" % ("N", "ch/cell", "A@2% (Erl)", "SIR dB", "system Erl (19 cells)"))
    for n_ in (3, 4, 7, 12):
        c = TOTAL_CHANNELS // n_
        A_ = traffic_at_blocking(c)
        print("  %-4d %-9d %-11.2f %-9.2f %-14.1f" % (n_, c, A_, to_db(sir_linear(n_, 4)), 19 * A_))
    print("\n3.7 Cost-capacity: C_total = C_survey + N_sites*C_site + C_antenna + C_backhaul + C_maintenance;")
    print("    cost per Erlang = C_total / A_system.  Needs local price quotations, so no figures are invented here.")

    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
    xs = [x * 0.5 for x in range(1, 121)]
    for c in (12, 28, 48, 84, 112):
        ax[0].plot(xs, [erlang_b(c, x) for x in xs], label="C=%d" % c)
    ax[0].axhline(0.02, color="k", ls="--"); ax[0].set_xlabel("Offered traffic A (Erlangs)"); ax[0].set_ylabel("Blocking B(C,A)")
    ax[0].set_title("Erlang-B blocking curves (2 % target dashed)"); ax[0].legend(); ax[0].set_xlim(0, 60)
    Ns = [3, 4, 7, 12]
    ax[1].bar([str(n_) for n_ in Ns], [19 * traffic_at_blocking(TOTAL_CHANNELS // n_) for n_ in Ns], color="#58c")
    ax[1].set_xlabel("Cluster size N"); ax[1].set_ylabel("System capacity at 2 % blocking (Erlangs)"); ax[1].set_title("19-cell capacity vs N")
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "screenshot_graph.png"), dpi=110); plt.close(fig)


if __name__ == "__main__":
    main()
