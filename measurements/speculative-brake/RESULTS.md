# Speculative brake — results

Protocol: [PREREGISTRATION.md](PREREGISTRATION.md), frozen in commit `7ba9485` before
any held-out run. Code: `spec_brake.py`, sha256 `b6abf800…b081a5`.
Receipts: [`receipts/`](receipts/), with `SHA256SUMS`.

- **Anchors:** 635 held-out positions in enwik8, selected by the hash rule.
- **Output:** 128 bytes per anchor.
- **Depths:** 1–27, nine depths.
- **Variants:** four.

## Gates

```
C1  oracle draft: every draft byte accepted            PASS
C1  oracle draft: no depth beats k = 27                PASS
C2  null draft below the order-2 draft at every k      PASS
C3  greedy speculation byte-identical to the verifier  PASS   (635 anchors × 9 depths)
C4  every anchor completed at every k, every variant   PASS
```

## Verdicts (primary: the order-2 MTP draft, speculative sampling)

| verifier cost `r` | brake at `k*` | best speed-up over the verifier alone | at `k = 27` |
|---:|---:|---:|---:|
| 1  | 1 | 0.733× (slower) | 0.070× |
| 4  | 1 | 1.173× | 0.256× |
| 16 | 3 | 1.531× | 0.739× |
| 64 | 4 | 1.784× | 1.396× |

`BRAKE_MEASURED` at all four cost ratios. Running ahead pays up to `k*`, and every depth
past it loses throughput. The more expensive the verifier, the further ahead it pays to run.

## What causes the brake

Bytes committed per cycle (order-2 draft):

```
k        1      2      3      4      6      8      12     16     27
bytes  1.466  1.695  1.818  1.895  1.946  1.970  1.981  1.987  1.986
```

The committed bytes saturate just under 2 per cycle, while the cost of a cycle keeps
growing as `k + r`. Past the brake, extra drafting is pure rollback: 29,631 bytes are
rolled back at `k = 1` and 1,073,688 at `k = 27`, for the same output.

**Acceptance does not worsen with position.** It is measured conditionally, as the
fraction of draft bytes accepted among those that reached position `i`:

```
position   1     2     3     4     5     6
accepted  0.428 0.526 0.595 0.599 0.589 0.597      (k = 27 run)
```

It *rises* from 0.43 toward about 0.6, because the drafts that survive the first
positions are in easier stretches of text. The brake comes from compounding instead. The
chance of reaching position `i` is the product of the acceptances before it
(0.43 · 0.53 · 0.60 · …), and that product falls geometrically. So the "decay with depth"
the simulator's MTP agent reported is a decay of joint reliability, not of per-step skill,
and that compounding alone is enough to set a finite braking point.

## Controls

- **Oracle draft** (the draft is the verifier itself): it accepts every byte and commits
  `k + 1` bytes per cycle, so it has no brake. Its throughput at `r = 1` is exactly 1 at
  every depth.
- **Null draft** (uniform over 256 bytes): it accepts about 0.04 bytes per cycle and never
  beats the verifier alone, except by 1.023× at `r = 64, k = 1`.
- **Greedy:** speculation reproduced plain greedy decoding byte for byte at every anchor
  and depth. Its brake falls at `k* = 1, 1, 2, 4` for `r = 1, 4, 16, 64`.

## Wall time (secondary)

Here the verifier is a table lookup about as cheap as the draft, so the hardware sits in
the `r ≈ 1` regime. Measured time per committed byte is lowest at `k = 1` (29,983 ns) and
highest at `k = 27` (61,494 ns). That is the same brake the `r = 1` row predicts.

## Scope

- **What this measures:** a draft-and-verify agent system on text, in which a small agent
  runs ahead, a large agent verifies, and disagreement rolls back. A braking depth
  exists, its location is measured, and it moves out as verification gets more expensive.
- **What it does not measure:** local clocks, late messages or state restoration across
  agents, or anything about physical spacetime.
