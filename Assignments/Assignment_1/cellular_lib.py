"""Shared helpers for ITA0313 Assignment 1 (hexagonal cellular network).
Everything here follows the formulas used in the report."""
import math
import numpy as np

TOTAL_CHANNELS = 336
ERL_PER_USER = 0.025
BLOCK_TARGET = 0.02
SIR_MIN_DB = 12.0


# ---------------------------------------------------------------- geometry
def cell_area(R):
    return 1.5 * math.sqrt(3) * R * R                  # (3*sqrt(3)/2) R^2


def cluster_size(i, j):
    return i * i + i * j + j * j                        # N = i^2 + ij + j^2


def reuse_distance(R, N):
    return R * math.sqrt(3 * N)                         # D = R sqrt(3N)


def sir_linear(N, n, interferers=6):
    return (3 * N) ** (n / 2) / interferers            # (D/R)^n / I0


def to_db(x):
    return 10 * math.log10(x)


# ---------------------------------------------------------------- traffic
def erlang_b(channels, traffic):
    """Recursive Erlang-B: B0 = 1, Bm = A*B(m-1) / (m + A*B(m-1))."""
    b = 1.0
    for m in range(1, channels + 1):
        b = traffic * b / (m + traffic * b)
    return b


def traffic_at_blocking(channels, target=BLOCK_TARGET):
    lo, hi = 0.0, float(channels) * 3
    for _ in range(100):
        mid = (lo + hi) / 2
        if erlang_b(channels, mid) > target:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def channels_needed(traffic, target=BLOCK_TARGET):
    c = max(1, int(traffic))
    while erlang_b(c, traffic) > target:
        c += 1
    return c


# ---------------------------------------------------------------- hex grid
def hex_grid(rings, R):
    """Axial-coordinate hex grid.  Returns list of (q, r) and an array of
    cell-centre coordinates (km) for flat-adjacent hexagons of radius R."""
    cells = [(q, r) for q in range(-rings, rings + 1) for r in range(-rings, rings + 1)
             if abs(q + r) <= rings]
    d = math.sqrt(3) * R                                  # distance between adjacent centres
    xy = np.array([[d * (q + r / 2), d * (math.sqrt(3) / 2) * r] for q, r in cells])
    return cells, xy


def colour_map(cells, i, j):
    """Frequency-group index 0..N-1 for every cell for cluster parameters (i, j).
    Two cells share a group when their axial-coordinate difference is an integer
    combination of the lattice vectors v1 = (i, j) and v2 = (-j, i + j)."""
    N = cluster_size(i, j)
    v1, v2 = (i, j), (-j, i + j)

    def same(c1, c2):
        dq, dr = c1[0] - c2[0], c1[1] - c2[1]
        s_num = dq * v2[1] - dr * v2[0]
        t_num = v1[0] * dr - v1[1] * dq
        return s_num % N == 0 and t_num % N == 0

    reps, colours = [], []
    for c in cells:
        for k, rep in enumerate(reps):
            if same(c, rep):
                colours.append(k)
                break
        else:
            reps.append(c)
            colours.append(len(reps) - 1)
    assert len(reps) == N, "grid too small for this cluster size"
    return colours, N


def random_points_in_hex(n, R, rng):
    """Uniform points inside the regular hexagon of circumradius R centred at the origin,
    oriented like hex_grid() (neighbour centres lie along +x, vertices on +/- y)."""
    apothem = math.sqrt(3) / 2 * R
    normals = [(1.0, 0.0), (0.5, math.sqrt(3) / 2), (-0.5, math.sqrt(3) / 2)]
    pts = []
    while len(pts) < n:
        p = rng.uniform(-R, R, size=(2 * n, 2))
        ok = np.ones(len(p), dtype=bool)
        for nx, ny in normals:
            ok &= np.abs(p[:, 0] * nx + p[:, 1] * ny) <= apothem
        pts.extend(p[ok].tolist())
    return np.array(pts[:n])
