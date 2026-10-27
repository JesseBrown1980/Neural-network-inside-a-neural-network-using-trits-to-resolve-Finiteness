# Several drafters, own clocks — results

Protocol: [PREREGISTRATION-TIMEWARP.md](PREREGISTRATION-TIMEWARP.md), frozen in commit
`54bc978` before the held-out run. Receipts: `receipts/TIMEWARP.hbp`,
`receipts/TIMEWARP-RESULT.hbp`.

- **Anchors:** 83 hash-selected held-out anchors.
- **Timeline:** 81 segments of 16 bytes, 6,723 segments per configuration.
- **Configurations:** `D = 3, 9, 27` drafters × latency `L = 8, 64` ticks × four modes.

## Gates

```
C1  every mode's final timeline byte-identical to the sequential one   PASS
C2  conservative: no rollbacks, makespan = Σ SEG·speed + (M−1)·L       PASS
C3  oracle: no rollbacks                                               PASS
C4  every anchor completed in every mode and every (D, L)              PASS
```

Rollback always restored the correct timeline: every optimistic run, however many
corrections it went through, ended byte-identical to the sequential answer.

## Verdicts

| mode | D | L | speed-up vs waiting | oracle ceiling | verdict |
|---|---:|---:|---:|---:|---|
| draft guesses | 3 | 8 | 0.815× | 2.37× | NO_SPEEDUP · CORRECTIONS_SPREAD |
| draft guesses | 3 | 64 | 0.877× | 4.96× | NO_SPEEDUP · CORRECTIONS_SPREAD |
| verifier guesses | 3 | 8 | 0.839× | 2.37× | NO_SPEEDUP · CORRECTIONS_SPREAD |
| verifier guesses | 3 | 64 | 0.899× | 4.96× | NO_SPEEDUP · CORRECTIONS_SPREAD |
| draft guesses | 9 | 8 | 0.872× | 7.01× | NO_SPEEDUP · CORRECTIONS_SPREAD |
| draft guesses | 9 | 64 | 0.972× | 13.40× | NO_SPEEDUP · CORRECTIONS_SPREAD |
| verifier guesses | 9 | 8 | 0.889× | 7.01× | NO_SPEEDUP · CORRECTIONS_SPREAD |
| verifier guesses | 9 | 64 | 1.004× | 13.40× | SPEEDUP_MEASURED · CORRECTIONS_SPREAD |
| draft guesses | 27 | 8 | 0.948× | 20.24× | NO_SPEEDUP · CORRECTIONS_SPREAD |
| draft guesses | 27 | 64 | 1.009× | 33.31× | SPEEDUP_MEASURED · CORRECTIONS_SPREAD |
| verifier guesses | 27 | 8 | 0.969× | 20.24× | NO_SPEEDUP · CORRECTIONS_SPREAD |
| verifier guesses | 27 | 64 | 1.034× | 33.31× | SPEEDUP_MEASURED · CORRECTIONS_SPREAD |

## How far corrections spread

How each cascade ended, in per mille, with the median reach (segments rolled back in a
row):

| mode | D | L | absorbed | in time | merged | **reached the end** | median reach | reach ≤ 5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| draft | 3 | 8 | 45 | 50 | 880 | **24** | 2 | 98% |
| draft | 3 | 64 | 93 | 441 | 361 | **103** | 2 | 86% |
| draft | 9 | 8 | 34 | 223 | 631 | **111** | 3 | 71% |
| draft | 9 | 64 | 57 | 217 | 512 | **212** | 7 | 48% |
| draft | 27 | 8 | 53 | 105 | 704 | **137** | 3 | 62% |
| draft | 27 | 64 | 132 | 60 | 343 | **463** | 8 | 41% |
| verifier | 27 | 64 | 120 | 71 | 344 | **464** | 9 | 42% |

1. **Corrections almost never heal on their own.** Only 3–13% of cascades are absorbed,
   meaning a recomputed segment comes out with the same ending. A wrong 5-byte input
   changes the whole continuation, so a correction keeps travelling.
2. **What usually stops a correction is another correction.** Most cascades end merged:
   they run into a segment already rolled back by a different correction. Next most
   often, they arrive in time, before the next drafter has gone ahead.
3. **The reach grows with more drafters and slower messages.** With 3 drafters and fast
   messages, 98% of corrections stop within 5 hops and 2.4% reach the end of the
   timeline. With 27 drafters and slow messages, the median reach is 8–9 hops and 46%
   reach the end.
4. **The guesses are the bottleneck, not the mechanism.** The drafters' guesses of the
   next input were wrong 86–96% of the time. Guessing with the drafter's own verifier
   instead of its draft lowered that only slightly (to 86–93%). With perfect guesses (the
   oracle), the same machinery would be 2.4× to 33× faster. With these guesses, the
   rolled-back work is 2.3× to 26.5× the useful work, and optimism only breaks even, at
   best 1.034× faster, when there are many drafters and messages are slow.

## Scope

- **What this measures:** Time Warp-style optimistic execution on an agent system working
  on text, with drafters on their own clocks, each verified by a different agent, late
  messages, rollback and lazy cancellation. In a chained timeline whose links are this
  sensitive, late corrections do not stay local: they travel until they meet another
  correction or the end.
- **What it does not measure:** anything about physical spacetime.
