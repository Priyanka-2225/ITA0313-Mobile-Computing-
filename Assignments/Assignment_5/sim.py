"""
ITA03-MP Assignment 5 - Part B simulation source
Models the Android background-work design of Part A (WorkManager-style scheduler),
the scrolling-feed optimiser (exact vs adaptive) and the video-upload strategy.
Pure Python 3, no third-party packages.  Run:  python3 sim.py
"""
import random, math, itertools, json, time
from dataclasses import dataclass

GOOD, POOR, NONE = "GOOD", "POOR", "NONE"
BW = {GOOD: 400, POOR: 60, NONE: 0}          # KB per tick shared by all running workers
CRIT, HIGH, NORM = 3, 2, 1
TTL = {CRIT: 40, HIGH: 70, NORM: 90}          # ticks before a work item expires
MIN_BATT = 20.0                               # % below which non-critical work is deferred
MAX_RETRY = 5
MAX_WORKERS = 3
PASSIVE_DRAIN = 0.05                          # % per tick
ENERGY_PER_KB = {GOOD: 0.0008, POOR: 0.0016}  # % battery per KB sent
ENC_COST = 0.02                               # % battery to encrypt one record


@dataclass
class Item:
    id: int
    arrive: int
    prio: int
    size: int
    sensitive: bool
    encrypted: bool
    state: str = "NEW"        # NEW, PENDING, RUNNING, DONE, CANCELLED
    retries: int = 0
    progress: int = 0
    done_tick: int = -1
    deferred_flag: bool = False


def make_env(T, net_segments, doze_segments, battery0, revoke_tick=None, logout_tick=None):
    net = [GOOD] * T
    for a, b, s in net_segments:
        for t in range(a, min(b, T)):
            net[t] = s
    doze = [False] * T
    for a, b in doze_segments:
        for t in range(a, min(b, T)):
            doze[t] = True
    return dict(T=T, net=net, doze=doze, battery0=battery0, revoke=revoke_tick, logout=logout_tick)


def standard_env():
    return make_env(150, [(30, 70, POOR), (45, 50, NONE), (95, 100, NONE)], [(35, 65), (100, 110)], 38.0)


def gen_workload(seed, n, arrive_lo, arrive_hi, sizes, p_crit=0.10, p_high=0.30,
                 p_sensitive=0.5, p_enc=0.6):
    r = random.Random(seed)
    items = []
    for i in range(n):
        x = r.random()
        prio = CRIT if x < p_crit else (HIGH if x < p_crit + p_high else NORM)
        sens = r.random() < p_sensitive
        enc = sens and (r.random() < p_enc)
        items.append(Item(i, r.randint(arrive_lo, arrive_hi), prio, r.randint(*sizes), sens, enc))
    items.sort(key=lambda it: (it.arrive, it.id))
    return items


def feasible(it, t, env, battery, perm, logged_in, policy):
    """Constraint test.  Returns ('OK'|'DEFER'|'CANCEL', reason)."""
    if not perm:
        return "CANCEL", "PERMISSION"
    if not logged_in:
        return "CANCEL", "LOGOUT"
    if t - it.arrive > TTL[it.prio]:
        return "CANCEL", "EXPIRED"
    if env["net"][t] == NONE:
        return "DEFER", "NETWORK"
    if env["doze"][t] and it.prio < CRIT:
        return "DEFER", "DOZE"
    if battery < MIN_BATT and it.prio < CRIT:
        return "DEFER", "BATTERY"
    if policy == "V2" and env["net"][t] == POOR and it.size > 200 and it.prio < CRIT:
        return "DEFER", "WAIT_GOOD_LINK"
    return "OK", ""


def order(pending, t, policy):
    if policy == "V1":
        return sorted(pending, key=lambda i: (i.arrive, i.id))
    # V2 rule: priority class first, then age (aging) and short-job-first
    return sorted(pending, key=lambda i: (-(100 * i.prio + (t - i.arrive) / 2.0 - i.size / 50.0), i.id))


def run(items_in, env, policy, log=None, verbose_every=0):
    items = [Item(**it.__dict__) for it in items_in]
    T = env["T"]
    battery = env["battery0"]
    perm, logged_in = True, True
    pending, running = [], []
    m = dict(enqueued=0, deferred=0, cancelled=0, success=0, peak=0, notifications=0,
             wasted_kb=0, retries=0, cleanups=0, plaintext_uploads=0, sent_kb=0)
    reasons = {}
    nxt = 0
    for t in range(T):
        while nxt < len(items) and items[nxt].arrive == t:
            it = items[nxt]; nxt += 1
            it.state = "PENDING"; pending.append(it); m["enqueued"] += 1
            if it.prio == CRIT:
                m["notifications"] += 1          # local critical alert is always shown
        if env["revoke"] == t:
            perm = False
        if env["logout"] == t:
            logged_in = False
        # cancellation of everything when permission / session lost
        if not perm or not logged_in:
            for it in running + pending:
                it.state = "CANCELLED"; m["cancelled"] += 1; m["cleanups"] += 1
                if it in running:
                    m["wasted_kb"] += it.progress
                reasons["PERMISSION" if not perm else "LOGOUT"] = reasons.get("PERMISSION" if not perm else "LOGOUT", 0) + 1
            running, pending = [], []
        # progress of running workers (bandwidth shared)
        net = env["net"][t]
        still = []
        for it in running:
            abort = None
            if net == NONE:
                abort = "NETWORK_LOST"
            elif env["doze"][t] and it.prio < CRIT:
                abort = "DOZE_ENTERED"
            if abort:
                m["wasted_kb"] += it.progress; it.progress = 0; it.retries += 1; m["retries"] += 1
                it.state = "PENDING"; it.deferred_flag = True; m["deferred"] += 1
                reasons[abort] = reasons.get(abort, 0) + 1
                if it.retries > MAX_RETRY:
                    it.state = "CANCELLED"; m["cancelled"] += 1; m["cleanups"] += 1
                    reasons["MAX_RETRY"] = reasons.get("MAX_RETRY", 0) + 1
                else:
                    pending.append(it)
                continue
            still.append(it)
        running = still
        if running:
            share = BW[net] / len(running)
            for it in list(running):
                step = min(share, it.size - it.progress)
                it.progress += step; m["sent_kb"] += step
                battery -= step * ENERGY_PER_KB[net]
                if it.progress >= it.size:
                    if it.sensitive and not it.encrypted:
                        m["plaintext_uploads"] += 1
                    it.state = "DONE"; it.done_tick = t; m["success"] += 1
                    running.remove(it)
        battery = max(0.0, battery - PASSIVE_DRAIN)
        # scheduling
        for it in order(pending, t, policy):
            verdict, why = feasible(it, t, env, battery, perm, logged_in, policy)
            if verdict == "CANCEL":
                it.state = "CANCELLED"; pending.remove(it); m["cancelled"] += 1; m["cleanups"] += 1
                reasons[why] = reasons.get(why, 0) + 1
                continue
            if verdict == "DEFER":
                if not it.deferred_flag:
                    it.deferred_flag = True; m["deferred"] += 1
                    reasons[why] = reasons.get(why, 0) + 1
                continue
            if len(running) >= MAX_WORKERS:
                break
            if it.sensitive and not it.encrypted:
                it.encrypted = True; battery -= ENC_COST
            it.state = "RUNNING"; it.deferred_flag = False
            pending.remove(it); running.append(it)
            if log is not None and (len(log) < 12):
                log.append("t=%3d  net=%-4s doze=%-5s batt=%5.1f%%  START item#%d prio=%d size=%dKB" %
                           (t, net, env["doze"][t], battery, it.id, it.prio, it.size))
        m["peak"] = max(m["peak"], len(running))
    backlog = [i for i in items if i.state in ("PENDING", "RUNNING")]
    crit_done = [i for i in items if i.prio == CRIT and i.state == "DONE"]
    crit_all = [i for i in items if i.prio == CRIT]
    m["backlog"] = len(backlog)
    m["final_battery"] = round(battery, 1)
    m["crit_total"] = len(crit_all)
    m["crit_delivered"] = len(crit_done)
    m["crit_latency"] = round(sum(i.done_tick - i.arrive for i in crit_done) / len(crit_done), 1) if crit_done else None
    m["high_latency"] = None
    hd = [i for i in items if i.prio == HIGH and i.state == "DONE"]
    if hd:
        m["high_latency"] = round(sum(i.done_tick - i.arrive for i in hd) / len(hd), 1)
    m["wasted_kb"] = int(m["wasted_kb"]); m["sent_kb"] = int(m["sent_kb"])
    m["reasons"] = reasons
    m["uploads_after_revoke"] = sum(1 for i in items if env["revoke"] is not None and i.state == "DONE" and i.done_tick >= env["revoke"])
    return m


# ------------------------------------------------------------------ B1 / B2
def part_b1_b2():
    out = {}
    # B1.1 tests
    env1 = make_env(100, [], [], 90.0)
    w1 = gen_workload(11, 30, 0, 40, (20, 300))
    env2 = make_env(120, [], [(10, 60)], 18.0)
    w2 = gen_workload(12, 30, 0, 40, (20, 300))
    env3 = make_env(80, [], [], 90.0, revoke_tick=12)
    w3 = gen_workload(13, 30, 0, 25, (300, 800))
    tests = {}
    for name, e, w in (("T1_good", env1, w1), ("T2_doze_lowbatt", env2, w2), ("T3_permission_revoked", env3, w3)):
        log = []
        r = run(w, e, "V2", log)
        r["log"] = log[:5]
        tests[name] = r
    out["tests"] = tests
    # B1.3/B1.4 standard comparison
    env = standard_env()
    wl = gen_workload(7, 60, 0, 90, (20, 800))
    out["std"] = {p: run(wl, env, p) for p in ("V1", "V2")}
    # B2 adversarial
    wA = gen_workload(21, 60, 0, 25, (20, 80), p_crit=0.1, p_high=0.3, p_sensitive=0.3, p_enc=1.0)
    wB = gen_workload(22, 60, 36, 64, (450, 850), p_crit=0.1, p_high=0.3, p_sensitive=0.8, p_enc=0.0)
    wC = gen_workload(22, 60, 0, 25, (450, 850), p_crit=0.1, p_high=0.3, p_sensitive=0.8, p_enc=0.0)   # control: B's sizes, early arrivals
    out["B2"] = {"C": {p: run(wC, env, p) for p in ("V1", "V2")}, "C_kb": sum(i.size for i in wC),
                 "A": {p: run(wA, env, p) for p in ("V1", "V2")},
                 "B": {p: run(wB, env, p) for p in ("V1", "V2")},
                 "A_kb": sum(i.size for i in wA), "B_kb": sum(i.size for i in wB)}
    return out


# ------------------------------------------------------------------ B3
QCOST = [0.5, 1.0, 1.7, 2.6, 3.6, 4.8]
QMEM = [1, 2, 4, 7, 11, 16]
QENG = [1.0, 2.2, 3.8, 6.0, 9.0, 13.0]
CACHE = [1, 2, 3, 4, 6]
PREF = [0, 1, 2, 3]
WSET = 6                                   # working-set size of visible+nearby items


def item_terms(b, q, Q, c, p):
    hit = min(1.0, c / WSET)
    pf = min(0.8, 0.22 * min(p, c // 2))     # prefetch helps only if cache can hold it
    ft = 4.0 + b * QCOST[q] * (1 - hit) * (1 - pf)
    return max(0.0, ft - 16.0) / 16.0, 0.1 * b * QENG[q], QMEM[q], (Q - 1 - q)


def total_cost(D, E, Mm, Ql, n, ci, pi):
    c, p = CACHE[ci], PREF[pi]
    E = E + 0.8 * c + 0.45 * p * n
    mem_over = max(0.0, Mm + 2 * c - 3.5 * n)   # memory budget: 3.5 units per item
    return 10 * D + 0.5 * E + 3 * Ql + 0.05 * mem_over ** 2


def config_cost(base, Q, qs, ci, pi):
    D = E = Mm = Ql = 0.0
    for b, q in zip(base, qs):
        d, e, m_, ql = item_terms(b, q, Q, CACHE[ci], PREF[pi])
        D += d; E += e; Mm += m_; Ql += ql
    return total_cost(D, E, Mm, Ql, len(base), ci, pi)


def exact(base, Q):
    best = (1e18, None); evals = 0
    for ci in range(len(CACHE)):
        for pi in range(len(PREF)):
            for qs in itertools.product(range(Q), repeat=len(base)):
                evals += 1
                c = config_cost(base, Q, qs, ci, pi)
                if c < best[0] - 1e-12:
                    best = (c, (list(qs), ci, pi))
    return best[0], best[1], evals


def adaptive(base, Q, start=None, trace=None):
    n = len(base)
    qs = [Q - 1] * n; ci, pi = 1, 0          # start: highest quality, small cache, no prefetch
    if start:
        qs, ci, pi = start
    c = None
    def terms(ci_, pi_):
        D = E = Mm = Ql = 0.0
        per = []
        for b, q in zip(base, qs):
            d, e, m_, ql = item_terms(b, q, Q, CACHE[ci_], PREF[pi_])
            D += d; E += e; Mm += m_; Ql += ql
        return D, E, Mm, Ql
    D, E, Mm, Ql = terms(ci, pi)
    cur = total_cost(D, E, Mm, Ql, n, ci, pi)
    evals = 1; qchg = cchg = pchg = 0; iters = 0
    while True:
        iters += 1
        best = (cur, None)
        # quality moves (O(1) each through aggregate deltas)
        for i in range(n):
            for dq in (-1, 1):
                nq = qs[i] + dq
                if 0 <= nq < Q:
                    d0, e0, m0, l0 = item_terms(base[i], qs[i], Q, CACHE[ci], PREF[pi])
                    d1, e1, m1, l1 = item_terms(base[i], nq, Q, CACHE[ci], PREF[pi])
                    cc = total_cost(D - d0 + d1, E - e0 + e1, Mm - m0 + m1, Ql - l0 + l1, n, ci, pi)
                    evals += 1
                    if cc < best[0] - 1e-12:
                        best = (cc, ("q", i, nq))
        for dc in (-1, 1):
            nci = ci + dc
            if 0 <= nci < len(CACHE):
                a = terms(nci, pi); cc = total_cost(*a, n, nci, pi); evals += 1
                if cc < best[0] - 1e-12:
                    best = (cc, ("c", nci))
        for dp in (-1, 1):
            npi = pi + dp
            if 0 <= npi < len(PREF):
                a = terms(ci, npi); cc = total_cost(*a, n, ci, npi); evals += 1
                if cc < best[0] - 1e-12:
                    best = (cc, ("p", npi))
        if best[1] is None:
            break                                   # steady state: no single move improves cost
        mv = best[1]
        if mv[0] == "q":
            qs[mv[1]] = mv[2]; qchg += 1
        elif mv[0] == "c":
            ci = mv[1]; cchg += 1
        else:
            pi = mv[1]; pchg += 1
        D, E, Mm, Ql = terms(ci, pi)
        cur = total_cost(D, E, Mm, Ql, n, ci, pi)
        if trace is not None:
            trace.append((iters, mv, round(cur, 3)))
    return cur, (qs, ci, pi), dict(evals=evals, qchg=qchg, cchg=cchg, pchg=pchg, iters=iters)


def lru_evictions(n, c):
    """Scroll down through n items, then back up 3 items, then down again; count LRU evictions."""
    seq = list(range(n)) + list(range(max(0, n - 3), max(0, n - 6), -1)) + list(range(max(0, n - 6), n))
    cache, ev = [], 0
    for x in seq:
        if x in cache:
            cache.remove(x); cache.append(x)
        else:
            if len(cache) >= c:
                cache.pop(0); ev += 1
            cache.append(x)
    return ev


def gen_base(seed, n):
    r = random.Random(seed)
    return [r.choice([6, 10, 14, 20, 28, 36]) for _ in range(n)]   # decode ms at quality-cost 1.0


def part_b3():
    out = {}
    # B3.1 small instances (seeds fixed in advance, not cherry-picked)
    small = []
    for seed in (1, 2, 3, 4, 5, 6):
        base = gen_base(seed, 5); Q = 3
        ec, ecfg, _ = exact(base, Q)
        ac, acfg, st = adaptive(base, Q)
        small.append(dict(seed=seed, base=base, exact=round(ec, 3), approx=round(ac, 3),
                          match=abs(ec - ac) < 1e-6, ecfg=(ecfg[0], CACHE[ecfg[1]], PREF[ecfg[2]]),
                          acfg=(acfg[0], CACHE[acfg[1]], PREF[acfg[2]])))
    out["small"] = small
    # B3.2 counter-example: search seeds for the largest gap
    worst = None
    for seed in range(1, 80):
        base = gen_base(seed, 5)
        ec, ecfg, _ = exact(base, 3)
        tr = []
        ac, acfg, st = adaptive(base, 3, trace=tr)
        gap = ac - ec
        if worst is None or gap > worst["gap"] + 1e-9:
            worst = dict(seed=seed, base=base, exact=ec, approx=ac, gap=gap, ecfg=ecfg, acfg=acfg, trace=tr)
    out["counter"] = dict(seed=worst["seed"], base=worst["base"], exact=round(worst["exact"], 3),
                          approx=round(worst["approx"], 3), gap=round(worst["gap"], 3),
                          ecfg=(worst["ecfg"][0], CACHE[worst["ecfg"][1]], PREF[worst["ecfg"][2]]),
                          acfg=(worst["acfg"][0], CACHE[worst["acfg"][1]], PREF[worst["acfg"][2]]),
                          trace=[(i, str(mv), c) for i, mv, c in worst["trace"]])
    # fraction matching across 79 seeds
    mism = 0; rel = []
    for seed in range(1, 80):
        base = gen_base(seed, 5)
        ec, _, _ = exact(base, 3); ac, _, _ = adaptive(base, 3)
        if ac - ec > 1e-6:
            mism += 1; rel.append((ac - ec) / ec * 100)
    out["mismatch_rate"] = (mism, 79)
    out["gap_pct"] = dict(mean=round(sum(rel) / len(rel), 1), max=round(max(rel), 1))
    # B3.3 scaling
    scale = []
    for n, Q, run_exact in ((4, 3, True), (6, 3, True), (8, 3, True), (10, 3, True), (8, 4, True),
                            (50, 4, False), (200, 6, False), (500, 6, False)):
        base = gen_base(100 + n, n)
        row = dict(n=n, Q=Q)
        if run_exact:
            t0 = time.time(); ec, ecfg, ev = exact(base, Q); row.update(exact_evals=ev, exact_cost=round(ec, 2),
                                                                     exact_time=round(time.time() - t0, 2),
                                                                     exact_evict=lru_evictions(n, CACHE[ecfg[1]]))
        else:
            row.update(exact_evals=None,
                       exact_cost=None, exact_time=None, exact_evict=None)
            row["exact_evals_str"] = "about 10^%d" % round(n * math.log10(Q) + math.log10(len(CACHE) * len(PREF)))
        t0 = time.time(); ac, acfg, st = adaptive(base, Q)
        row.update(ad_evals=st["evals"], ad_cost=round(ac, 2), ad_time=round(time.time() - t0, 2),
                   ad_qchg=st["qchg"], ad_cchg=st["cchg"], ad_pchg=st["pchg"], ad_iters=st["iters"],
                   ad_evict=lru_evictions(n, CACHE[acfg[1]]))
        scale.append(row)
    out["scale"] = scale
    return out


# ------------------------------------------------------------------ B4
RES = {"480p": dict(q=1.0, cx=0.6, mbps=1.0), "720p": dict(q=2.0, cx=1.0, mbps=2.5), "1080p": dict(q=3.0, cx=2.2, mbps=5.0)}
CLIP_S = 15


def estimate(dev, res, timing):
    r = RES[res]
    enc_t = CLIP_S * r["cx"] / dev["cpu"]                      # seconds
    enc_e = enc_t * dev["cpu_w"]                               # joules
    size_mb = r["mbps"] * CLIP_S / 8
    bw = dev["wifi_mbps"] if timing == "wait_wifi" and dev["wifi_avail"] else dev["net_mbps"]
    up_t = size_mb * 8 / bw
    up_e = up_t * (0.8 if (timing == "wait_wifi" and dev["wifi_avail"]) else dev["radio_w"])
    wait = dev["wifi_wait_s"] if timing == "wait_wifi" and not dev["wifi_avail"] else 0
    total_t = enc_t + up_t + wait
    e = enc_e + up_e
    batt_pct = e / (dev["cap_wh"] * 3600) * 100
    return dict(enc_t=enc_t, up_t=up_t, size_mb=size_mb, energy_j=e, total_t=total_t, batt_pct=batt_pct)


def heuristic(dev):
    """Rule: highest resolution whose total time <= deadline and battery impact <= budget.
       Low battery & not charging -> 480p; metered cellular and size > 15 MB -> wait for wifi."""
    budget = 1.5 if dev["battery"] >= 30 else 0.6
    timing = "wait_wifi" if dev["wifi_avail"] else "now"      # use Wi-Fi immediately when it is available
    order_ = ["1080p", "720p", "480p"]
    if dev["battery"] < 15 and not dev["charging"]:
        order_ = ["480p"]
    for res in order_:
        e = estimate(dev, res, timing)
        if e["size_mb"] > 8 and dev["metered"] and not dev["wifi_avail"]:
            e2 = estimate(dev, res, "wait_wifi")
            if e2["total_t"] <= dev["deadline_s"] and e2["batt_pct"] <= budget:
                return res, "wait_wifi", e2
            continue
        if e["total_t"] <= dev["deadline_s"] and e["batt_pct"] <= budget:
            return res, timing, e
    e = estimate(dev, "480p", "now")
    return "480p", "now", e


def utility(dev, res, timing):
    e = estimate(dev, res, timing)
    if e["total_t"] > dev["deadline_s"]:
        return -1e9, e
    scarcity = 8.0 if (dev["battery"] < 15 and not dev["charging"]) else 1.0   # energy is worth more when battery is nearly empty
    data_cost = 1.2 * e["size_mb"] if (dev["metered"] and not (timing == "wait_wifi")) else 0.0   # metered data is charged
    return 10 * RES[res]["q"] - 0.15 * e["total_t"] - 12 * scarcity * e["batt_pct"] - data_cost, e


def exhaustive(dev):
    best = None
    for res in RES:
        for timing in ("now", "wait_wifi"):
            if timing == "wait_wifi" and not (dev["wifi_avail"] or dev["wifi_wait_s"] > 0):
                continue
            u, e = utility(dev, res, timing)
            if best is None or u > best[0]:
                best = (u, res, timing, e)
    return best


DEVICES = [
    dict(name="Flagship-WiFi", cpu=3.0, cpu_w=2.5, battery=80, charging=False, cap_wh=17, net_mbps=40, wifi_mbps=80, wifi_avail=True, radio_w=1.4, metered=False, wifi_wait_s=0, deadline_s=60),
    dict(name="Mid-range-4G", cpu=1.6, cpu_w=2.0, battery=55, charging=False, cap_wh=15, net_mbps=8, wifi_mbps=30, wifi_avail=False, radio_w=1.6, metered=True, wifi_wait_s=900, deadline_s=60),
    dict(name="Low-end-3G", cpu=0.7, cpu_w=1.6, battery=40, charging=False, cap_wh=11, net_mbps=2, wifi_mbps=20, wifi_avail=False, radio_w=1.8, metered=True, wifi_wait_s=1800, deadline_s=90),
    dict(name="Low-battery", cpu=2.0, cpu_w=2.2, battery=12, charging=False, cap_wh=15, net_mbps=15, wifi_mbps=40, wifi_avail=False, radio_w=1.5, metered=False, wifi_wait_s=0, deadline_s=60),
    dict(name="Charging-4G", cpu=2.2, cpu_w=2.3, battery=22, charging=True, cap_wh=16, net_mbps=12, wifi_mbps=40, wifi_avail=False, radio_w=1.5, metered=False, wifi_wait_s=0, deadline_s=60),
]
CHALLENGE = dict(name="Slow-CPU-fast-5G", cpu=0.9, cpu_w=2.6, battery=70, charging=False, cap_wh=16, net_mbps=100, wifi_mbps=100, wifi_avail=False, radio_w=1.2, metered=False, wifi_wait_s=0, deadline_s=60)


def random_device(r, i):
    wifi = r.random() < 0.35
    return dict(name="rnd%d" % i, cpu=r.choice([0.6, 0.9, 1.3, 1.8, 2.5, 3.2]), cpu_w=r.choice([1.5, 2.0, 2.5]),
                battery=r.choice([8, 14, 22, 35, 55, 80]), charging=r.random() < 0.15,
                cap_wh=r.choice([5, 9, 12, 16]), net_mbps=r.choice([1.5, 3, 8, 20, 60]), wifi_mbps=40, wifi_avail=wifi,
                radio_w=r.choice([1.2, 1.6, 2.4]), metered=(not wifi) and r.random() < 0.6,
                wifi_wait_s=r.choice([600, 1800]), deadline_s=r.choice([45, 60, 90]))


def part_b4_study(n=2000):
    r = random.Random(2024)
    same = 0; losses = []; worst = None
    for i in range(n):
        d = random_device(r, i)
        res, tm, e = heuristic(d)
        u, _ = utility(d, res, tm)
        bu, bres, btm, be = exhaustive(d)
        if (res, tm) == (bres, btm) or abs(u - bu) < 1e-6:
            same += 1
        else:
            loss = bu - u
            losses.append(loss)
            if worst is None or loss > worst[0]:
                worst = (loss, d, (res, tm), (bres, btm), round(u, 2), round(bu, 2))
    return dict(n=n, same=same, mean_loss=round(sum(losses) / max(1, len(losses)), 2), worst=worst)


def part_b4():
    rows = []
    for d in DEVICES:
        res, tm, e = heuristic(d)
        u, _ = utility(d, res, tm)
        bu, bres, btm, be = exhaustive(d)
        rows.append(dict(name=d["name"], res=res, timing=tm, enc_t=round(e["enc_t"], 1), up_t=round(e["up_t"], 1),
                         total_t=round(e["total_t"], 1), energy_j=round(e["energy_j"], 1), batt_pct=round(e["batt_pct"], 3),
                         batt_after=round(d["battery"] - e["batt_pct"], 2), utility=round(u, 2),
                         best_res=bres, best_timing=btm, best_utility=round(bu, 2)))
    return rows


if __name__ == "__main__":
    res = dict(b1b2=part_b1_b2(), b3=part_b3(), b4=part_b4(), b4study=part_b4_study())
    json.dump(res, open("results.json", "w"), indent=1, default=str)
    print(json.dumps(res["b1b2"]["tests"], indent=1, default=str)[:1500])
    print("STD", {k: {x: v[x] for x in v if x not in ("reasons",)} for k, v in res["b1b2"]["std"].items()})
    print("B2", json.dumps(res["b1b2"]["B2"], default=str)[:2500])
    print("B3 small", res["b3"]["small"])
    print("B3 counter", res["b3"]["counter"], res["b3"]["mismatch_rate"])
    for r in res["b3"]["scale"]:
        print(r)
    for r in res["b4"]:
        print(r)
    print("B4 study", res["b4study"])
