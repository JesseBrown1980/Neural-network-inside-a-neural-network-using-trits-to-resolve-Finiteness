# The 16K pieces — results

Addendum: [PREREGISTRATION-TIMEWARP-16K.md](PREREGISTRATION-TIMEWARP-16K.md), frozen in
`18c2234` before the held-out run. The run used the same 83 hash-selected anchors, now with
segments of 16,384 bytes. Receipts: `receipts/TIMEWARP-16K.hbp`,
`receipts/TIMEWARP-16K-RESULT.hbp`, `receipts/COMPARE-16-vs-16K.hbp`.

## Gates

```
C1  final timeline byte-identical to the sequential one, every mode   PASS
C2  conservative: no rollbacks, exact makespan                         PASS
C3  oracle: no rollbacks                                               PASS
C4  coverage                                                           PASS
C5  cycle-skipping path = byte-by-byte generation (83 × 3 checks)      PASS
```

## The comparative verdict (Jesse's prediction)

**SLOWED in 9 of 12 configurations, NOT_SLOWED in 3.**

| mode | D | L | reached the end, 16 B → 16K | stopped locally, 16 B → 16K | verdict |
|---|---:|---:|---:|---:|---|
| draft | 3 | 8 | 2.4% → 2.2% | 92.5% → 76.3% | NOT_SLOWED |
| draft | 3 | 64 | 10.3% → 2.2% | 45.5% → 76.3% | SLOWED |
| draft | 9 | 8 | 11.1% → 9.8% | 66.5% → 66.0% | NOT_SLOWED |
| draft | 9 | 64 | 21.2% → 9.8% | 57.0% → 66.0% | SLOWED |
| draft | 27 | 8 | 13.7% → 10.5% | 75.7% → 77.7% | SLOWED |
| draft | 27 | 64 | 46.3% → 10.5% | 47.5% → 77.7% | SLOWED |
| verifier | 3 | 8 | 2.3% → 2.2% | 90.9% → 72.8% | NOT_SLOWED |
| verifier | 3 | 64 | 10.9% → 2.2% | 46.1% → 72.8% | SLOWED |
| verifier | 9 | 8 | 11.9% → 8.4% | 64.2% → 72.3% | SLOWED |
| verifier | 9 | 64 | 22.6% → 8.4% | 55.6% → 72.3% | SLOWED |
| verifier | 27 | 8 | 13.3% → 11.0% | 76.9% → 77.1% | SLOWED |
| verifier | 27 | 64 | 46.4% → 11.0% | 46.4% → 77.1% | SLOWED |

"Stopped locally" means the cascade ended absorbed or merged.

## What it shows

1. **Fewer corrections reach the end with giant pieces, in all 12 configurations.**
2. **Self-healing about doubles.** The share of corrections absorbed on their own goes from
   4.5% to 9.0% (`D = 3`), 3.4% to 5.3% (`D = 9`) and 5.3% to 11.5% (`D = 27`), for the
   draft-guess mode at `L = 8`.
3. **Read the big drops with care.** At 16K a segment takes 16,384–65,536 ticks, so the
   message latency (8 or 64 ticks) almost vanishes next to the work. The large drops at
   `L = 64` (for example 46% → 11%) come partly from that, because slow messages stop
   mattering. The like-for-like comparison is the fast-message row (`L = 8`):
   - the end fraction falls more modestly, from 2.4 to 2.2%, 11.1 to 9.8% and 13.7 to
     10.5%;
   - it is SLOWED at `D = 27` and with verifier guesses at `D = 9`;
   - it is NOT_SLOWED at `D = 3`, where more corrections end "in time" rather than
     stopped locally.
4. **There is still no speed-up.** The guesses are wrong 83–94% of the time, so optimism
   still costs more than waiting. The oracle ceiling stays at 2.0× to 17.8×.

## Scope

Giant pieces slow the spreading of late corrections in this agent system: fewer reach the
end, and more heal on their own. The effect is clear when messages are slow and modest
when they are fast. Nothing here measures physical spacetime.
