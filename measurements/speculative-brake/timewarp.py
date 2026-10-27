"""Several drafters, own clocks, each verified by a different agent: how far do late
corrections spread between them? Exact integers, integer ticks, json=0.
See PREREGISTRATION-TIMEWARP.md.

usage:
  python timewarp.py build   ENWIK8 CACHE_DIR
  python timewarp.py run     ENWIK8 CACHE_DIR OUT
  python timewarp.py combine OUT
"""
import hashlib
import heapq
import os
import sys

import numpy as np

import spec_brake as sb

SEG = 16                 # bytes per segment
M = 81                   # segments per anchor run (one global virtual timeline)
DS = [3, 9, 27]          # number of drafters
LATS = [8, 64]           # message latency, ticks
KSPEC = 4                # inner draft depth (the brake point at r = 64)
ANCHOR_MOD = 65536
TRAIN_END = sb.TRAIN_END
MODES = ["optimistic", "optimistic_v", "conservative", "oracle"]
if os.environ.get("TW_SMOKE") == "1":            # smoke test only: training region, tiny
    sb.HELD_LO, sb.HELD_HI, ANCHOR_MOD, M = 1_000_000, 1_400_000, 131072, 27


def build(enwik, cache):
    if sb.md5(enwik) != sb.MD5:
        raise SystemExit("CORPUS|md5_mismatch|json=0")
    data = open(enwik, "rb").read()[:TRAIN_END]
    for D in DS:
        for i in range(D):
            lo, hi = i * TRAIN_END // D, (i + 1) * TRAIN_END // D
            a = np.frombuffer(data[lo:hi], dtype=np.uint8).astype(np.uint64)
            L = len(a)
            d = os.path.join(cache, "D%d" % D, "s%d" % i)
            os.makedirs(d, exist_ok=True)
            for n in range(sb.VER_N + 1):
                key = np.zeros(L - n, dtype=np.uint64)
                for j in range(n):
                    key = (key << np.uint64(8)) | a[j:L - n + j]
                key = (key << np.uint64(8)) | a[n:]
                k, c = np.unique(key, return_counts=True)
                np.save(os.path.join(d, "K%d.npy" % n), k)
                np.save(os.path.join(d, "C%d.npy" % n), c.astype(np.int64))
        print("SLICES|D=%d|bytes_per_slice=%d|json=0" % (D, TRAIN_END // D), flush=True)


class Agent:
    """One drafter (order 2) with its own verifier (order 5), both from its own slice."""

    def __init__(self, d):
        self.draft = sb.Model(d, sb.DRAFT_N)
        self.ver = sb.Model(d, sb.VER_N)
        self.seg_memo, self.roll_memo = {}, {}

    def segment(self, ctx):
        """Verified segment from a 5-byte context: speculative greedy, k = KSPEC."""
        if ctx not in self.seg_memo:
            out = bytearray(ctx)
            while len(out) - len(ctx) < SEG:
                h = bytearray(out[-sb.VER_N:])
                xs = []
                for _ in range(KSPEC):
                    x = self.draft.dist(h).greedy
                    xs.append(x)
                    h.append(x)
                    del h[:-sb.VER_N]
                h = bytearray(out[-sb.VER_N:])
                for i in range(KSPEC):
                    g = self.ver.dist(h).greedy
                    out.append(g)
                    h.append(g)
                    del h[:-sb.VER_N]
                    if g != xs[i]:
                        break
                else:
                    out.append(self.ver.dist(h).greedy)
            self.seg_memo[ctx] = bytes(out[len(ctx):len(ctx) + SEG])
        return self.seg_memo[ctx]

    def guess(self, ctx, steps, use_verifier=False):
        """The drafter's own guess: roll its draft (or its verifier) forward steps segments."""
        key = (ctx, steps, use_verifier)
        model = self.ver if use_verifier else self.draft
        if key not in self.roll_memo:
            out = bytearray(ctx)
            for _ in range(steps * SEG):
                out.append(model.dist(out[-sb.VER_N:]).greedy)
            self.roll_memo[key] = bytes(out[-sb.VER_N:])
        return self.roll_memo[key]


def speed(i):
    return 1 + hashlib.sha256(b"TW-SPEED|%d" % i).digest()[0] % 4    # ticks per byte, 1..4


def sequential(agents, D, ctx0):
    ctx, outs = ctx0, []
    for s in range(M):
        seg = agents[s % D].segment(ctx)
        outs.append(seg)
        ctx = (ctx + seg)[-sb.VER_N:]
    return outs


def simulate(agents, D, L, ctx0, mode, truth):
    """Discrete-event run. Drafter i owns segments s = i mod D and runs on its own clock.

    Cascade bookkeeping: a cascade starts when a first-time message rolls back a segment
    that was computed on a wrong guess (depth 1). When a rolled-back segment is recomputed:
      unchanged tail          -> ends ABSORBED at its depth (lazy cancellation)
      changed tail, last seg  -> ends at the END of the timeline (unabsorbed)
      changed tail            -> sends a correction carrying its depth
    A correction that reaches a segment not yet computed, or computed on the same input,
    ends IN_TIME; one that lands on a segment already rolled back ends MERGED; otherwise it
    rolls that segment back at depth + 1.
    """
    known = [dict() for _ in range(D)]
    proc, sent, depth_of = {}, {}, {}
    busy = [None] * D
    free_at = [0] * D
    ev, seq = [], [0]
    st = {"computations": 0, "rollbacks": 0, "mispredicts": 0, "messages": 0, "cascades": 0,
          "ends": {"absorbed": 0, "in_time": 0, "merged": 0, "end": 0}, "reach": [], "makespan": 0}

    def push(t, kind, data):
        seq[0] += 1
        heapq.heappush(ev, (t, seq[0], kind, data))

    def true_in(s):
        return ctx0 if s == 0 else truth[s - 1][-sb.VER_N:]

    def input_for(i, s):
        if s == 0:
            return ctx0
        if s - 1 in known[i]:
            return known[i][s - 1]
        if mode == "conservative":
            return None
        if mode == "oracle":
            return true_in(s)
        j = max([x for x in known[i] if x < s - 1] + [-1])
        base = ctx0 if j < 0 else known[i][j]
        return agents[i].guess(base, s - 1 - j, mode == "optimistic_v")

    def dirty(i, s):
        if s not in proc:
            return True
        return s - 1 in known[i] and proc[s][0] != known[i][s - 1]

    def end(kind, d):
        st["ends"][kind] += 1
        st["reach"].append(d)

    def start(i, t):
        if busy[i] is not None:
            return
        for s in range(i, M, D):
            if dirty(i, s):
                ctx = input_for(i, s)
                if ctx is None:
                    return
                busy[i] = (s, ctx)
                st["computations"] += 1
                if s in proc:
                    st["rollbacks"] += 1
                free_at[i] = max(t, free_at[i]) + SEG * speed(i)
                push(free_at[i], "done", i)
                return

    def hit(s, tail, d):
        """A message with this tail for segment s reached the owner of s + 1."""
        tgt = s + 1
        used = proc.get(tgt, (None,))[0]
        b = busy[tgt % D]
        if b is not None and b[0] == tgt and (tgt not in proc or b[1] != used):
            used = b[1]
        wrong = used is not None and used != tail
        if d is None:
            if wrong and tgt not in depth_of:
                st["cascades"] += 1
                depth_of[tgt] = 1
        elif not wrong:
            end("in_time", d)
        elif tgt in depth_of:
            end("merged", d)
        else:
            depth_of[tgt] = d + 1

    for i in range(D):
        start(i, 0)
    while ev:
        t, _, kind, data = heapq.heappop(ev)
        st["makespan"] = max(st["makespan"], t)
        if kind == "done":
            i = data
            s, ctx = busy[i]
            busy[i] = None
            first = s not in proc
            proc[s] = (ctx, agents[i].segment(ctx))
            if first and ctx != true_in(s):
                st["mispredicts"] += 1
            tail = (ctx + proc[s][1])[-sb.VER_N:]
            stale = s - 1 in known[i] and known[i][s - 1] != ctx
            d = None if stale else depth_of.pop(s, None)
            changed = sent.get(s) != tail
            if d is not None and not changed:
                end("absorbed", d)
            elif d is not None and s + 1 == M:
                end("end", d)
            if s + 1 < M and changed:
                sent[s] = tail
                st["messages"] += 1
                push(t + L, "msg", (s, tail, d))
            start(i, t)
        else:
            s, tail, d = data
            known[(s + 1) % D][s] = tail
            hit(s, tail, d)
            start((s + 1) % D, t)
    for i in range(D):
        if busy[i] is not None or any(dirty(i, s) for s in range(i, M, D)):
            raise RuntimeError("did not settle")
    st["unabsorbed"] = st["ends"]["end"]
    return [proc[s][1] for s in range(M)], st


def conservative_bound(D, L):
    return sum(SEG * speed(s % D) for s in range(M)) + (M - 1) * L


def run(enwik, cache, outpath):
    if sb.md5(enwik) != sb.MD5:
        raise SystemExit("CORPUS|md5_mismatch|json=0")
    data = open(enwik, "rb").read()
    an = []
    for p in range(sb.HELD_LO, sb.HELD_HI):
        h = hashlib.sha256(b"TW-V1|" + str(p).encode()).digest()
        if int.from_bytes(h[:8], "big") % ANCHOR_MOD == 0:
            an.append(p)
    lines = ["TWHDR|anchors=%d|M=%d|SEG=%d|KSPEC=%d|D=%s|L=%s|json=0"
             % (len(an), M, SEG, KSPEC, ",".join(map(str, DS)), ",".join(map(str, LATS)))]
    for D in DS:
        agents = [Agent(os.path.join(cache, "D%d" % D, "s%d" % i)) for i in range(D)]
        for L in LATS:
            for mode in MODES:
                tot = {"computations": 0, "rollbacks": 0, "mispredicts": 0, "messages": 0, "cascades": 0,
                       "absorbed": 0, "in_time": 0, "merged": 0, "unabsorbed": 0, "makespan": 0,
                       "exact_fail": 0, "done": 0}
                reach = []
                for p in an:
                    ctx0 = data[p - sb.VER_N:p]
                    truth = sequential(agents, D, ctx0)
                    final, st = simulate(agents, D, L, ctx0, mode, truth)
                    if final != truth:
                        tot["exact_fail"] += 1
                    for k in ("computations", "rollbacks", "mispredicts", "messages", "cascades",
                              "unabsorbed", "makespan"):
                        tot[k] += st[k]
                    for k in ("absorbed", "in_time", "merged"):
                        tot[k] += st["ends"][k]
                    reach += st["reach"]
                    tot["done"] += 1
                hist = {}
                for r in reach:
                    hist[r] = hist.get(r, 0) + 1
                lines.append("TW|D=%d|L=%d|mode=%s|anchors_done=%d|exact_fail=%d|computations=%d|segments=%d|"
                             "rollbacks=%d|mispredicts=%d|messages=%d|cascades=%d|absorbed=%d|in_time=%d|merged=%d|unabsorbed=%d|"
                             "makespan=%d|conservative_bound=%d|reach_hist=%s|json=0"
                             % (D, L, mode, tot["done"], tot["exact_fail"], tot["computations"], M * len(an),
                                tot["rollbacks"], tot["mispredicts"], tot["messages"], tot["cascades"],
                                tot["absorbed"], tot["in_time"], tot["merged"], tot["unabsorbed"], tot["makespan"],
                                conservative_bound(D, L) * len(an),
                                ",".join("%d:%d" % kv for kv in sorted(hist.items())) or "-"))
                print(lines[-1][:200], flush=True)
    with open(outpath, "w") as f:
        f.write("\n".join(lines) + "\n")


def combine(path):
    rows = {}
    for line in open(path):
        parts = line.strip().split("|")
        if parts[0] == "TW":
            f = dict(x.split("=", 1) for x in parts[1:] if "=" in x)
            rows[(int(f["D"]), int(f["L"]), f["mode"])] = f
    g = {}
    g["C1_exact_all_modes"] = all(int(f["exact_fail"]) == 0 for f in rows.values())
    g["C2_conservative_no_rollback"] = all(int(rows[(D, L, "conservative")]["rollbacks"]) == 0 and
                                           int(rows[(D, L, "conservative")]["makespan"]) ==
                                           int(rows[(D, L, "conservative")]["conservative_bound"])
                                           for D in DS for L in LATS)
    g["C3_oracle_no_rollback"] = all(int(rows[(D, L, "oracle")]["rollbacks"]) == 0 for D in DS for L in LATS)
    g["C4_coverage"] = len(rows) == len(DS) * len(LATS) * len(MODES) and \
        len({f["anchors_done"] for f in rows.values()}) == 1
    out = []
    for D in DS:
      for om in ("optimistic", "optimistic_v"):
        for L in LATS:
            o, c, orc = rows[(D, L, om)], rows[(D, L, "conservative")], rows[(D, L, "oracle")]
            segs = int(o["segments"])
            casc, un = int(o["cascades"]), int(o["unabsorbed"])
            ends = "absorbed:%s,in_time:%s,merged:%s,end:%s" % (o["absorbed"], o["in_time"], o["merged"], un)
            out.append("TWRESULT|mode=%s|D=%d|L=%d|speedup_milli=%d|oracle_speedup_milli=%d|waste_milli=%d|"
                       "mispredict_milli=%d|cascades=%d|ends=%s|reach_hist=%s|json=0"
                       % (om, D, L, int(c["makespan"]) * 1000 // int(o["makespan"]),
                          int(c["makespan"]) * 1000 // int(orc["makespan"]),
                          (int(o["computations"]) - segs) * 1000 // segs,
                          int(o["mispredicts"]) * 1000 // segs, casc, ends, o["reach_hist"]))
    for k, ok in g.items():
        out.append("GATE|%s|%s|json=0" % (k, "PASS" if ok else "FAIL"))
    allok = all(g.values())
    for D in DS:
      for om in ("optimistic", "optimistic_v"):
        for L in LATS:
            o, c = rows[(D, L, om)], rows[(D, L, "conservative")]
            if not allok:
                v1 = v2 = "INCONCLUSIVE"
            else:
                v1 = "SPEEDUP_MEASURED" if int(o["makespan"]) < int(c["makespan"]) else "NO_SPEEDUP"
                ne = sum(int(o[k]) for k in ("absorbed", "in_time", "merged", "unabsorbed"))
                un = int(o["unabsorbed"])
                v2 = "NO_CORRECTIONS" if int(o["cascades"]) == 0 else (
                    "CORRECTIONS_ABSORBED" if un * 100 <= ne else "CORRECTIONS_SPREAD")
            out.append("VERDICT|mode=%s|D=%d|L=%d|%s|%s|json=0" % (om, D, L, v1, v2))
    print("\n".join(out))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "build":
        build(sys.argv[2], sys.argv[3])
    elif cmd == "run":
        run(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "combine":
        combine(sys.argv[2])
