"""Speculative brake: MTP draft runs ahead, one verifier pass commits the agreeing prefix
and rolls back the rest. Exact integers throughout, json=0. See PREREGISTRATION.md.

usage:
  python spec_brake.py build   ENWIK8 CACHE_DIR
  python spec_brake.py run     ENWIK8 CACHE_DIR VARIANT OUT     VARIANT = order2|oracle|null|greedy
  python spec_brake.py combine OUT_order2 OUT_oracle OUT_null OUT_greedy
"""
import bisect
import hashlib
import os
import sys
import time

import numpy as np

TRAIN_END = 20_000_000
HELD_LO, HELD_HI = 95_000_000, 99_998_976
ANCHOR_MOD = 8192
T = 128
if os.environ.get("SPEC_SMOKE") == "1":          # smoke test only: training region, tiny
    HELD_LO, HELD_HI, ANCHOR_MOD, T = 1_000_000, 1_200_000, 65536, 16
DEPTHS = [1, 2, 3, 4, 6, 8, 12, 16, 27]
RS = [1, 4, 16, 64]
DRAFT_N, VER_N = 2, 5
MD5 = "a1fa5ffddb56f4953e226637dabbb36a"


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def build(enwik, cache):
    if md5(enwik) != MD5:
        raise SystemExit("CORPUS|md5_mismatch|json=0")
    data = open(enwik, "rb").read()[:TRAIN_END]
    a = np.frombuffer(data, dtype=np.uint8).astype(np.uint64)
    L = len(a)
    os.makedirs(cache, exist_ok=True)
    for n in range(VER_N + 1):
        key = np.zeros(L - n, dtype=np.uint64)
        for j in range(n):
            key = (key << np.uint64(8)) | a[j:L - n + j]
        key = (key << np.uint64(8)) | a[n:]
        k, c = np.unique(key, return_counts=True)
        np.save(os.path.join(cache, "K%d.npy" % n), k)
        np.save(os.path.join(cache, "C%d.npy" % n), c.astype(np.int64))
        print("TABLE|order=%d|keys=%d|positions=%d|json=0" % (n, len(k), L - n))


class Dist:
    __slots__ = ("d", "tot", "syms", "cum", "greedy")

    def __init__(self, syms, counts):
        self.syms = syms
        self.d = dict(zip(syms, counts))
        self.cum = []
        t = 0
        for c in counts:
            t += c
            self.cum.append(t)
        self.tot = t
        best = max(counts)
        self.greedy = min(s for s, c in zip(syms, counts) if c == best)


UNIFORM = Dist(list(range(256)), [1] * 256)


class Model:
    def __init__(self, cache, N):
        self.N = N
        self.K = [np.load(os.path.join(cache, "K%d.npy" % n)) for n in range(N + 1)]
        self.C = [np.load(os.path.join(cache, "C%d.npy" % n)) for n in range(N + 1)]
        self.memo = {}

    def dist(self, hist):
        for n in range(self.N, -1, -1):
            ctx = int.from_bytes(bytes(hist[len(hist) - n:]), "big") if n else 0
            key = (n, ctx)
            if key in self.memo:
                d = self.memo[key]
            else:
                K = self.K[n]
                lo = ctx << 8
                s = int(np.searchsorted(K, np.uint64(lo)))
                e = int(np.searchsorted(K, np.uint64(lo + 256)))
                d = Dist([int(x) & 255 for x in K[s:e]], [int(x) for x in self.C[n][s:e]]) if e > s else None
                self.memo[key] = d
            if d is not None:
                return d
        raise RuntimeError("order-0 table empty")


class NullModel:
    def dist(self, hist):
        return UNIFORM


class Rng:
    def __init__(self, seed):
        self.seed = seed
        self.ctr = 0

    def u64(self):
        h = hashlib.sha256(self.seed + self.ctr.to_bytes(8, "big")).digest()
        self.ctr += 1
        return int.from_bytes(h[:8], "big")

    def below(self, m):
        if m <= 0:
            raise ValueError("below(%d)" % m)
        lim = ((1 << 64) // m) * m
        while True:
            x = self.u64()
            if x < lim:
                return x % m

    def pick(self, dist):
        u = self.below(dist.tot)
        return dist.syms[bisect.bisect_right(dist.cum, u)]

    def pick_weights(self, syms, weights):
        cum, t = [], 0
        for w in weights:
            t += w
            cum.append(t)
        u = self.below(t)
        return syms[bisect.bisect_right(cum, u)]


def anchors():
    out = []
    for p in range(HELD_LO, HELD_HI):
        h = hashlib.sha256(b"SPEC-BRAKE-V1|" + str(p).encode()).digest()
        if int.from_bytes(h[:8], "big") % ANCHOR_MOD == 0:
            out.append(p)
    return out


def spec_sample(prefix, k, draft, ver, rng, st):
    out = bytearray(prefix)
    produced = 0
    while produced < T:
        st["cycles"] += 1
        xs, ps = [], []
        h = bytearray(out[-VER_N:])
        for _ in range(k):
            p = draft.dist(h)
            x = rng.pick(p)
            xs.append(x)
            ps.append(p)
            h.append(x)
            del h[:-VER_N]
        h = bytearray(out[-VER_N:])
        commit, a, rejected = [], 0, False
        for i in range(k):
            q = ver.dist(h)
            st["reached"][i] += 1
            x, p = xs[i], ps[i]
            cp, Np, cq, Nq = p.d[x], p.tot, q.d.get(x, 0), q.tot
            if rng.below(cp * Nq) < cq * Np:
                st["accpos"][i] += 1
                commit.append(x)
                h.append(x)
                del h[:-VER_N]
                a += 1
            else:
                ys = sorted(set(q.syms) | set(p.syms))
                ws = [max(0, q.d.get(y, 0) * Np - p.d.get(y, 0) * Nq) for y in ys]
                commit.append(rng.pick_weights(ys, ws))
                rejected = True
                break
        if not rejected:
            commit.append(rng.pick(ver.dist(h)))
        st["accepted"] += a
        st["rolled_back"] += k - a
        out.extend(commit)
        produced += len(commit)
    st["bytes"] += produced


def greedy_plain(prefix, ver, n):
    out = bytearray(prefix)
    for _ in range(n):
        out.append(ver.dist(out[-VER_N:]).greedy)
    return bytes(out[len(prefix):])


def spec_greedy(prefix, k, draft, ver, st):
    out = bytearray(prefix)
    produced = 0
    while produced < T:
        st["cycles"] += 1
        h = bytearray(out[-VER_N:])
        xs = []
        for _ in range(k):
            x = draft.dist(h).greedy
            xs.append(x)
            h.append(x)
            del h[:-VER_N]
        h = bytearray(out[-VER_N:])
        commit, a = [], 0
        for i in range(k):
            g = ver.dist(h).greedy
            st["reached"][i] += 1
            if g == xs[i]:
                st["accpos"][i] += 1
                commit.append(g)
                h.append(g)
                del h[:-VER_N]
                a += 1
            else:
                commit.append(g)
                break
        else:
            commit.append(ver.dist(h).greedy)
        st["accepted"] += a
        st["rolled_back"] += k - a
        out.extend(commit)
        produced += len(commit)
    st["bytes"] += produced
    return bytes(out[len(prefix):])


def run(enwik, cache, variant, outpath):
    if md5(enwik) != MD5:
        raise SystemExit("CORPUS|md5_mismatch|json=0")
    data = open(enwik, "rb").read()
    ver = Model(cache, VER_N)
    draft = {"order2": Model(cache, DRAFT_N), "oracle": ver, "null": NullModel(),
             "greedy": Model(cache, DRAFT_N)}[variant]
    an = anchors()
    lines = ["SPECHDR|variant=%s|anchors=%d|T=%d|draft_order=%s|verifier_order=%d|json=0"
             % (variant, len(an), T, {"oracle": VER_N, "null": "uniform"}.get(variant, DRAFT_N), VER_N)]
    for k in DEPTHS:
        st = {"cycles": 0, "bytes": 0, "accepted": 0, "rolled_back": 0,
              "reached": [0] * k, "accpos": [0] * k, "done": 0, "exact_fail": 0}
        t0 = time.perf_counter_ns()
        for p in an:
            prefix = data[p - VER_N:p]
            if variant == "greedy":
                got = spec_greedy(prefix, k, draft, ver, st)
                if got[:T] != greedy_plain(prefix, ver, T):
                    st["exact_fail"] += 1
            else:
                rng = Rng(b"SPEC-BRAKE-V1|rng|%s|%d|%d|" % (variant.encode(), p, k))
                spec_sample(prefix, k, draft, ver, rng, st)
            st["done"] += 1
        ns = time.perf_counter_ns() - t0
        lines.append("SPEC|variant=%s|k=%d|anchors_done=%d|cycles=%d|bytes=%d|accepted=%d|rolled_back=%d|"
                     "exact_fail=%d|ns=%d|reached=%s|accpos=%s|json=0"
                     % (variant, k, st["done"], st["cycles"], st["bytes"], st["accepted"], st["rolled_back"],
                        st["exact_fail"], ns, ",".join(map(str, st["reached"])), ",".join(map(str, st["accpos"]))))
        print(lines[-1][:160], flush=True)
    with open(outpath, "w") as f:
        f.write("\n".join(lines) + "\n")


def parse(path):
    hdr, rows = None, {}
    for line in open(path):
        parts = line.strip().split("|")
        f = dict(x.split("=", 1) for x in parts[1:] if "=" in x)
        if parts[0] == "SPECHDR":
            hdr = f
        elif parts[0] == "SPEC":
            rows[int(f["k"])] = f
    return hdr, rows


def best_k(rows, r):
    best = None
    for k in DEPTHS:
        b, c = int(rows[k]["bytes"]), int(rows[k]["cycles"])
        if best is None:
            best = (k, b, c)
            continue
        kb, bb, cb = best
        if b * (cb * (kb + r)) > bb * (c * (k + r)):
            best = (k, b, c)
    return best[0]


def thr_lt(rows, k1, k2, r):   # throughput(k1) < throughput(k2), exact
    b1, c1 = int(rows[k1]["bytes"]), int(rows[k1]["cycles"])
    b2, c2 = int(rows[k2]["bytes"]), int(rows[k2]["cycles"])
    return b1 * (c2 * (k2 + r)) < b2 * (c1 * (k1 + r))


def combine(paths):
    names = ["order2", "oracle", "null", "greedy"]
    data = {n: parse(p) for n, p in zip(names, paths)}
    gates = {}
    na = {int(h["anchors"]) for h, _ in data.values()}
    gates["C4_coverage"] = len(na) == 1 and all(
        set(rows) == set(DEPTHS) and all(int(rows[k]["anchors_done"]) == next(iter(na)) for k in DEPTHS)
        for _, rows in data.values())
    o = data["oracle"][1]
    gates["C1_oracle_all_accepted"] = all(int(o[k]["accepted"]) == k * int(o[k]["cycles"]) for k in DEPTHS)
    gates["C1_oracle_no_interior_max"] = all(not thr_lt(o, DEPTHS[-1], k, r) for r in RS for k in DEPTHS)
    m, nl = data["order2"][1], data["null"][1]
    gates["C2_null_below_order2"] = all(
        int(nl[k]["accepted"]) * int(m[k]["cycles"]) < int(m[k]["accepted"]) * int(nl[k]["cycles"]) for k in DEPTHS)
    g = data["greedy"][1]
    gates["C3_greedy_exact"] = all(int(g[k]["exact_fail"]) == 0 for k in DEPTHS)
    out = ["SPECRESULT|anchors=%d|T=%d|depths=%s|r=%s|json=0" % (next(iter(na)), T, ",".join(map(str, DEPTHS)),
                                                                ",".join(map(str, RS)))]
    for name in names:
        rows = data[name][1]
        for k in DEPTHS:
            f = rows[k]
            b, c, a = int(f["bytes"]), int(f["cycles"]), int(f["accepted"])
            reached = list(map(int, f["reached"].split(",")))
            accpos = list(map(int, f["accpos"].split(",")))
            alpha = ",".join(str(x * 1000 // y) if y else "-" for x, y in zip(accpos, reached))
            gain = ",".join("r%d:%d" % (r, b * r * 1000 // (c * (k + r))) for r in RS)
            out.append("THROUGHPUT|variant=%s|k=%d|bytes_per_cycle_milli=%d|accepted_per_cycle_milli=%d|"
                       "rolled_back=%d|speedup_vs_verifier_milli=%s|alpha_by_position_milli=%s|ns=%s|json=0"
                       % (name, k, b * 1000 // c, a * 1000 // c, int(f["rolled_back"]), gain, alpha, f["ns"]))
    for g_, ok in gates.items():
        out.append("GATE|%s|%s|json=0" % (g_, "PASS" if ok else "FAIL"))
    allok = all(gates.values())
    for r in RS:
        rows = data["order2"][1]
        k = best_k(rows, r)
        if not allok:
            v = "INCONCLUSIVE"
        elif k != DEPTHS[-1] and thr_lt(rows, DEPTHS[-1], k, r):
            v = "BRAKE_MEASURED"
        else:
            v = "NO_BRAKE_IN_RANGE"
        out.append("VERDICT|variant=order2|r=%d|k_star=%d|%s|json=0" % (r, k, v))
    for r in RS:
        out.append("REPORT|variant=greedy|r=%d|k_star=%d|json=0" % (r, best_k(data["greedy"][1], r)))
    print("\n".join(out))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "build":
        build(sys.argv[2], sys.argv[3])
    elif cmd == "run":
        run(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    elif cmd == "combine":
        combine(sys.argv[2:6])
