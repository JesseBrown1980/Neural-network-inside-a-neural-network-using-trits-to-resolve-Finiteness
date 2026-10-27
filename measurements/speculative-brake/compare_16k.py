"""Comparative verdict, 16-byte run vs 16K run (PREREGISTRATION-TIMEWARP-16K.md). json=0
usage: python compare_16k.py RESULT_16 RESULT_16K"""
import sys


def load(path):
    rows, gates = {}, []
    for line in open(path):
        parts = line.strip().split("|")
        if parts[0] == "TWRESULT":
            f = dict(x.split("=", 1) for x in parts[1:] if "=" in x)
            e = {k: int(v) for k, v in (x.split(":") for x in f["ends"].split(","))}
            rows[(f["mode"], int(f["D"]), int(f["L"]))] = e
        elif parts[0] == "GATE":
            gates.append(parts[2] == "PASS")
    return rows, gates


a, ga = load(sys.argv[1])
b, gb = load(sys.argv[2])
ok = all(ga) and all(gb) and set(a) == set(b)
for key in sorted(a):
    ea, eb = a[key], b[key]
    na, nb = sum(ea.values()), sum(eb.values())
    end_lower = eb["end"] * na < ea["end"] * nb
    loc_a, loc_b = ea["absorbed"] + ea["merged"], eb["absorbed"] + eb["merged"]
    local_higher = loc_b * na > loc_a * nb
    v = "INCONCLUSIVE" if not ok else ("SLOWED" if end_lower and local_higher else "NOT_SLOWED")
    print("COMPARE|mode=%s|D=%d|L=%d|end_permille_16=%d|end_permille_16k=%d|local_permille_16=%d|"
          "local_permille_16k=%d|%s|json=0" % (key[0], key[1], key[2], ea["end"] * 1000 // na,
                                               eb["end"] * 1000 // nb, loc_a * 1000 // na, loc_b * 1000 // nb, v))
