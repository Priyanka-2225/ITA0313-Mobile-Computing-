"""Tasks 8, 9 & 10 - Simulator, experimental results and theory-vs-simulation comparison.

Modules (as listed in the report, section 8.1):
  hex-grid generator   -> common/cellular_lib.hex_grid
  channel assignment   -> common/cellular_lib.colour_map  (cluster colouring, sectors share the cell's channels 3 ways)
  SIR evaluator        -> sir_samples()   Monte-Carlo, finite 127-cell grid (6 rings), actual distances
  Erlang-B calculator  -> common/cellular_lib.erlang_b  + event-driven call simulation simulate_blocking()

Model: path loss d^-n, optional log-normal shadowing, 3-sector antenna pattern
G(theta) = -min(12 (theta/65 deg)^2, 20) dB.  Users are uniform in the centre cell; co-channel
interferers are *all* same-group cells of the finite grid (not an equal-distance approximation).
Random seed, trial counts and configuration are printed with the results.
"""
import heapq, math, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from cellular_lib import *

HERE = os.path.dirname(os.path.abspath(__file__))
R, RINGS, SEED, USERS = 0.5, 6, 2026, 20000
SIGMA_DB = 6.0
IJ = {3: (1, 1), 4: (2, 0), 7: (2, 1), 12: (2, 2)}
BORESIGHT = np.radians([90.0, 210.0, 330.0])
CELLS_N = 19

CELLS, XY = hex_grid(RINGS, R)
CENTRE = CELLS.index((0, 0))


def antenna_gain(delta):                          # linear gain relative to boresight
    delta = (delta + np.pi) % (2 * np.pi) - np.pi
    db = -np.minimum(12 * (np.degrees(delta) / 65.0) ** 2, 20.0)
    return 10 ** (db / 10)


def sir_samples(N, n, sectored=False, sigma_db=0.0, users=USERS, seed=SEED):
    colours, _ = colour_map(CELLS, *IJ[N])
    colours = np.array(colours)
    rng = np.random.default_rng(seed)                       # same seed -> same mobile positions for every strategy
    pts = random_points_in_hex(users, R, rng)
    # verification: every sampled point must be nearest to the centre cell (i.e. inside it)
    dist_all = np.linalg.norm(pts[:, None, :] - XY[None, :, :], axis=2)
    assert (np.argmin(dist_all, axis=1) == CENTRE).all()
    shadow = np.random.default_rng(seed + 1)
    co = [k for k in range(len(CELLS)) if colours[k] == colours[CENTRE] and k != CENTRE]
    d0 = np.maximum(dist_all[:, CENTRE], 0.01)
    p_des = d0 ** -n
    p_int = np.maximum(dist_all[:, co], 0.01) ** -n
    if sectored:
        vec0 = pts - XY[CENTRE]
        ang0 = np.arctan2(vec0[:, 1], vec0[:, 0])
        gains0 = np.stack([antenna_gain(ang0 - b) for b in BORESIGHT], axis=1)
        s = np.argmax(gains0, axis=1)                           # serving sector of each mobile
        p_des = p_des * gains0[np.arange(users), s]
        vec = pts[:, None, :] - XY[None, co, :]
        angi = np.arctan2(vec[..., 1], vec[..., 0])
        p_int = p_int * antenna_gain(angi - BORESIGHT[s][:, None])    # same-sector co-channel cells only
    if sigma_db > 0:
        p_des = p_des * 10 ** (shadow.normal(0, sigma_db, users) / 10)
        p_int = p_int * 10 ** (shadow.normal(0, sigma_db, p_int.shape) / 10)
    return 10 * np.log10(p_des / p_int.sum(axis=1))


def stats(sir):
    return dict(mean=sir.mean(), median=np.median(sir), p5=np.percentile(sir, 5), outage=(sir < SIR_MIN_DB).mean())


def simulate_blocking(channels, A, calls=200000, seed=SEED):
    """Event-driven loss system: Poisson arrivals (rate A, mean holding time 1)."""
    rng = np.random.default_rng(seed)
    t, busy, blocked, counted = 0.0, [], 0, 0
    warm = calls // 20
    for c in range(calls):
        t += rng.exponential(1.0 / A)
        while busy and busy[0] <= t:
            heapq.heappop(busy)
        if c >= warm:
            counted += 1
        if len(busy) < channels:
            heapq.heappush(busy, t + rng.exponential(1.0))
        elif c >= warm:
            blocked += 1
    return blocked / counted


def main():
    print("SIMULATOR CONFIGURATION")
    print("  grid: %d cells (%d rings), R = %.2f km, users per test = %d, seed = %d, shadowing sigma = %.0f dB, SIR target = %d dB"
          % (len(CELLS), RINGS, R, USERS, SEED, SIGMA_DB, SIR_MIN_DB))
    print("  grid check: nearest co-channel distance equals D = R*sqrt(3N):")
    for N in IJ:
        colours = np.array(colour_map(CELLS, *IJ[N])[0])
        co = [k for k in range(len(CELLS)) if colours[k] == colours[CENTRE] and k != CENTRE]
        print("    N=%-2d  simulated %.4f km  analytic %.4f km" % (N, min(np.linalg.norm(XY[k] - XY[CENTRE]) for k in co), reuse_distance(R, N)))

    tests = [(1, 3, 2.5, False), (2, 4, 3.0, False), (3, 7, 4.0, False), (4, 12, 4.0, False), (5, 7, 4.0, True)]
    print("\nTASK 8.3 / 9 - Required test cases (no shadowing, then sigma = 6 dB)")
    hdr = "  %-5s %-3s %-4s %-12s %-9s %-9s %-9s %-10s %-9s | %-9s %-9s %-10s"
    print(hdr % ("Test", "N", "n", "Config", "ch/cell", "meanSIR", "5th pct", "outage", "runtime", "meanSIR", "5th pct", "outage"))
    print("  " + " " * 59 + "(sigma = 0 dB)" + " " * 34 + "(sigma = 6 dB)")
    results, samples = {}, {}
    for tid, N, n, sec in tests:
        t0 = time.perf_counter()
        s0 = sir_samples(N, n, sec, 0.0)
        rt = time.perf_counter() - t0
        s6 = sir_samples(N, n, sec, SIGMA_DB)
        a, b = stats(s0), stats(s6)
        results[tid], samples[tid] = (a, b), (s0, s6)
        print(hdr % (tid, N, n, "3-sector" if sec else "omni", "%d%s" % (TOTAL_CHANNELS // N, "(3x%d)" % (TOTAL_CHANNELS // N // 3) if sec else ""),
                     "%.2f" % a["mean"], "%.2f" % a["p5"], "%.4f" % a["outage"], "%.3f s" % rt, "%.2f" % b["mean"], "%.2f" % b["p5"], "%.4f" % b["outage"]))
    print("  (SIR in dB; mean taken in dB; outage = fraction of users below 12 dB; runtime = SIR evaluation of %d users)" % USERS)

    print("\nExtended matrix - omni, sigma = 0 (N x n)   [mean SIR dB / outage]")
    print("  %-6s" % "N" + "".join("n=%-14s" % n for n in (2.5, 3, 4)))
    for N in IJ:
        row = ""
        for n in (2.5, 3.0, 4.0):
            st = stats(sir_samples(N, n))
            row += "%-6.2f/%-8.4f  " % (st["mean"], st["outage"])
        print("  %-6d%s" % (N, row))

    print("\nBlocking probability per cell (Erlang-B, uniform load over 19 cells)")
    print("  %-12s" % "subscribers" + "".join("N=%-2d(%3d ch)  " % (N, TOTAL_CHANNELS // N) for N in IJ) + "N=7 3-sector (3x16)")
    for u in (1000, 10000, 20000, 30000, 50000, 100000):
        A = u * ERL_PER_USER / CELLS_N
        print("  %-12d" % u + "".join("%-14.4f  " % erlang_b(TOTAL_CHANNELS // N, A) for N in IJ) + "%.4f" % erlang_b(16, A / 3))

    print("\nTASK 10 - Theory vs simulation: SIR (dB), n and N as in tests")
    print("  %-5s %-3s %-4s %-9s %-14s %-12s %-12s %-9s" % ("Test", "N", "n", "Config", "analytic (6I/2I)", "sim median", "sim mean", "diff (median-analytic)"))
    for tid, N, n, sec in tests:
        an = to_db(sir_linear(N, n, 2 if sec else 6))
        a = results[tid][0]
        print("  %-5d %-3d %-4s %-9s %-14.2f %-12.2f %-12.2f %+.2f" % (tid, N, n, "sector" if sec else "omni", an, a["median"], a["mean"], a["median"] - an))
    print("  Reasons for deviation: real interferers are at different distances, more than six interferers (2nd tier),")
    print("  users are spread over the cell (not at the edge), and the sector pattern is directional, not a '2 interferer' count.")

    print("\n  Blocking: Erlang-B vs event-driven simulation (%d calls per point, seed %d)" % (200000, SEED))
    print("  %-9s %-14s %-14s %-12s" % ("channels", "A (Erlangs)", "Erlang-B", "simulated"))
    cases = [(48, 30.0), (48, traffic_at_blocking(48)), (48, 45.0), (48, 50.0), (16, traffic_at_blocking(48) / 3), (28, 20.15), (112, 99.62)]
    sim_pts = {}
    for c, A in cases:
        sb = simulate_blocking(c, A)
        sim_pts[(c, round(A, 2))] = sb
        print("  %-9d %-14.3f %-14.4f %-12.4f" % (c, A, erlang_b(c, A), sb))
    print("  Note: 16 channels at A/3 shows the trunking-efficiency loss of sectorisation (blocking above 2 %).")

    print("\n  Decision using BOTH forms of evidence (outage at sigma = 6 dB <= 25 %, omni, n = 4):")
    for N in IJ:
        st = stats(sir_samples(N, 4.0, False, SIGMA_DB))
        cap = CELLS_N * traffic_at_blocking(TOTAL_CHANNELS // N)
        ok = st["outage"] <= 0.25
        print("   N=%-2d outage %.3f  capacity %.0f Erl (%d users)  -> %s" % (N, st["outage"], cap, cap / ERL_PER_USER, "meets quality, capacity ranked" if ok else "fails outage limit"))

    # ------------------------------------------------------------ plots
    fig, ax = plt.subplots(2, 2, figsize=(14, 10))
    for tid, N, n, sec in tests:
        s0, s6 = samples[tid]
        lab = "T%d N=%d n=%s%s" % (tid, N, n, " sector" if sec else "")
        xs = np.sort(s0); ys = np.arange(1, len(xs) + 1) / len(xs)
        l, = ax[0, 0].plot(xs, ys, label=lab)
        xs6 = np.sort(s6); ax[0, 0].plot(xs6, ys, ls="--", color=l.get_color(), alpha=.6)
    ax[0, 0].axvline(12, color="k", ls=":"); ax[0, 0].set_xlim(-10, 50); ax[0, 0].set_xlabel("SIR (dB)"); ax[0, 0].set_ylabel("CDF")
    ax[0, 0].set_title("SIR CDF (solid sigma=0, dashed sigma=6 dB)"); ax[0, 0].legend(fontsize=8); ax[0, 0].grid(alpha=.3)
    xs = np.linspace(1, 70, 140)
    for c in (28, 48, 84, 112):
        ax[0, 1].plot(xs, [erlang_b(c, x) for x in xs], label="Erlang-B C=%d" % c)
    for (c, A), sb in sim_pts.items():
        if c == 48:
            ax[0, 1].plot(A, sb, "ko")
    ax[0, 1].plot([], [], "ko", label="simulation (C=48)"); ax[0, 1].axhline(.02, color="r", ls="--")
    ax[0, 1].set_xlabel("Offered traffic per cell (Erlangs)"); ax[0, 1].set_ylabel("Blocking probability"); ax[0, 1].set_title("Blocking vs offered traffic"); ax[0, 1].legend(fontsize=8)
    Ns = list(IJ)
    ax[1, 0].bar([str(N) for N in Ns], [CELLS_N * traffic_at_blocking(TOTAL_CHANNELS // N) for N in Ns], color="#58c")
    ax[1, 0].set_xlabel("Cluster size N"); ax[1, 0].set_ylabel("System capacity (Erl) at 2 % blocking"); ax[1, 0].set_title("System capacity vs N")
    users = np.array([1000, 3000, 10000, 30000, 100000])
    cap7 = traffic_at_blocking(48)
    ax[1, 1].plot(users, [max(19, math.ceil(u * ERL_PER_USER / cap7)) for u in users], "o-")
    ax[1, 1].set_xscale("log"); ax[1, 1].set_yscale("log"); ax[1, 1].set_xlabel("Subscribers"); ax[1, 1].set_ylabel("Sites required (macro, N=7)")
    ax[1, 1].set_title("Sites vs demand (coverage floor = 19)"); ax[1, 1].grid(alpha=.3)
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "screenshot_graph.png"), dpi=100); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4.3))
    labels = ["T1", "T2", "T3", "T4", "T5\n(sector)"]
    w = 0.35
    ax.bar(np.arange(5) - w / 2, [results[t][0]["mean"] for t in range(1, 6)], w, label="mean SIR")
    ax.bar(np.arange(5) + w / 2, [results[t][0]["p5"] for t in range(1, 6)], w, label="5th percentile SIR")
    ax.axhline(12, color="r", ls="--"); ax.set_xticks(range(5)); ax.set_xticklabels(labels); ax.set_ylabel("SIR (dB)"); ax.set_title("Mean and 5th-percentile SIR (sigma = 0)"); ax.legend()
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "screenshot_graph_sir_summary.png"), dpi=110); plt.close(fig)


if __name__ == "__main__":
    main()
