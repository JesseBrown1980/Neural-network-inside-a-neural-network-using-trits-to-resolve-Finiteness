# Several drafters, own clocks — pre-registration (frozen before any held-out run)

**Question.** Several drafters each own part of one shared timeline and run ahead
optimistically, each on its own clock and each verified by a different agent. When a late
correction arrives, how far does it spread between them before it is absorbed?

## Setup

- **Corpus:** `enwik8` (MD5 `a1fa5ffd…`), the same as `PREREGISTRATION.md`.
- **Agents:** with `D ∈ {3, 9, 27}` drafters, the training bytes `[0, 20,000,000)` are cut
  into `D` disjoint equal slices. Drafter `i` has its own draft (order 2) and its own
  verifier (order 5), both built only from slice `i`, so every drafter is checked by a
  different agent.
- **One shared timeline:** `M = 81` segments of `SEG = 16` bytes. Segment `s` belongs to
  drafter `s mod D`, and its input is the last 5 bytes of segment `s − 1`. A segment's
  output is its owner's verified text (speculative greedy decoding with draft depth 4,
  the measured brake at `r = 64`). The correct timeline is the sequential one: each
  segment computed from the true end of the one before it.
- **Own clocks:** drafter `i` takes `1 + (SHA-256("TW-SPEED|i")[0] mod 4)` ticks per byte.
  Messages take `L ∈ {8, 64}` ticks. Everything is an integer, discrete-event and
  deterministic.
- **Anchors (the hash trick):** held-out positions `p ∈ [95,000,000, 99,998,976)` whose
  first 8 bytes of `SHA-256("TW-V1|" + decimal(p))` are `≡ 0 (mod 65536)`.

## Modes

| mode | how a drafter starts a segment whose input has not arrived |
|---|---|
| `optimistic` | guesses it by rolling its own draft model forward from the latest end it has received |
| `optimistic_v` | the same, but rolling its own verifier forward |
| `conservative` | waits (control) |
| `oracle` | is told the true input (control) |

A drafter always works on its lowest-numbered segment that is either not yet computed or
was computed on an input that has since been contradicted. When a segment finishes, its
end is sent to the next owner only if it differs from what was last sent (lazy
cancellation). A message that contradicts the input a segment was computed on rolls that
segment back.

## Cascades, defined now

A cascade starts when a first-time message rolls back a segment computed on a wrong guess
(depth 1). When a rolled-back segment is recomputed:

- **absorbed:** its end is unchanged (it ends at its depth).
- **end:** its end changed and it is the last segment (it reached the end of the
  timeline, unabsorbed).
- otherwise it sends a correction carrying its depth.

A correction ends **in time** if the next segment has not been computed yet or was
computed on the same input. It ends **merged** if that segment is already rolled back.
Otherwise it rolls that segment back at depth + 1.

**Reach** is the depth at which a cascade ends: how many drafters' segments one late
correction rolled back in a row.

## Measured

- **Work and messages:** computations, rollbacks, mispredicted first guesses, messages.
- **Cascades:** how each one ended, and the reach histogram.
- **Makespan:** in ticks, against the conservative and oracle runs.

## Gates

- **C1 exact:** every mode's final timeline is byte-identical to the sequential timeline,
  at every anchor and every `(D, L)`.
- **C2 conservative:** zero rollbacks, and makespan equals `Σ SEG·speed + (M−1)·L`.
- **C3 oracle:** zero rollbacks.
- **C4 coverage:** every anchor completes in every mode and every `(D, L)`.

## Verdicts, fixed now (per optimistic mode, `D` and `L`)

If any gate fails, every verdict is `INCONCLUSIVE`. Otherwise:

| verdict | condition |
|---|---|
| `SPEEDUP_MEASURED` | optimistic makespan < conservative makespan (summed over anchors) |
| `NO_SPEEDUP` | otherwise |
| `CORRECTIONS_ABSORBED` | at most 1% of cascade endings reach the end of the timeline |
| `CORRECTIONS_SPREAD` | more than 1% reach the end |
| `NO_CORRECTIONS` | no cascades |

## Smoke test (before the freeze)

A smoke test ran on 2 anchors from the training region (`TW_SMOKE=1`: positions
1,000,000–1,400,000, `M = 27`), with all gates passing. It showed that the drafters'
guesses of the next input were wrong about 95% of the time. That is why the
`optimistic_v` mode was added before this freeze: to test whether better prediction
contains the spreading.

## Scope

Drafters, clocks, late messages, rollback and re-sending: Time Warp on an agent system
working on text. Nothing here measures physical spacetime.
