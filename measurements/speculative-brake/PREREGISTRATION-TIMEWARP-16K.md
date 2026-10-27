# Several drafters — the 16K pieces (addendum, frozen before the held-out run)

**Jesse Daniel Brown's prediction.** In the 16-byte run, corrections spread because the
pieces of space were small. With giant pieces (the Brown–Hilbert expansion), the
spreading still happens, but it is slowed locally by the other MTP agent localizations.

**What changes.** Only the segment size: `SEG = 16,384` bytes (`TW_SEG=16384`). Everything
else is identical to `PREREGISTRATION-TIMEWARP.md`:

- the same 83 hash-selected anchors (rule `TW-V1`, mod 65536)
- `M = 81` segments, `D = 3, 9, 27` drafters, each with its own draft and verifier from a
  disjoint training slice
- `L = 8, 64`, the same speeds and all four modes
- the same cascade definitions, gates C1–C4 and verdict rules

Two points follow from the larger pieces:

- **Latency:** at 16K a segment takes 16,384–65,536 ticks, so message latency is
  negligible next to the work. `L = 8` and `L = 64` are expected to behave almost alike.
- **How segments are generated:** for `SEG > 64`, a segment is the verifier's greedy text
  (identical to speculative greedy by gate C3 of the brake run). It is computed exactly by
  cycle-skipping: the next byte depends only on the last 5, so the text enters a cycle and
  is indexed ahead. Draft guesses roll forward the same way.

**New gate C5.** For every anchor and every `D`, the first segment computed by the
cycle-skipping path is byte-identical to full byte-by-byte speculative generation.

**Regression check, before the freeze.** With the edited code at `SEG = 16`, the frozen
held-out receipt `receipts/TIMEWARP.hbp` is reproduced byte-identical.

## Comparative verdict (fixed now)

For each optimistic mode and each `(D, L)`, compare the 16K run with the frozen 16-byte
run (`receipts/TIMEWARP.hbp`):

| verdict | condition |
|---|---|
| `SLOWED` | the fraction of cascade endings that reach the end of the timeline is strictly lower at 16K **and** the fraction ending absorbed or merged (stopped locally) is strictly higher |
| `NOT_SLOWED` | otherwise, when every gate passes in both runs |
| `INCONCLUSIVE` | any gate fails in either run |

The per-run verdicts (`SPEEDUP`, `CORRECTIONS_ABSORBED/SPREAD`) are reported as before.

## Smoke test (before the freeze)

`TW_SEG=16384 TW_SMOKE=1` (2 training-region anchors, `M = 27`): all gates, C5 included,
pass. Nothing from the held-out anchors was seen.
