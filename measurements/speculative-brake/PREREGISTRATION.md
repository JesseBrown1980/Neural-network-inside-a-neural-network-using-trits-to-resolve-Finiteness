# Speculative brake — pre-registration (frozen before any run)

**Question.** When a small drafting agent (MTP) runs ahead of a large verifying agent and
the verifier keeps only the prefix it agrees with, rolling back the rest, is there a
measured braking point: a draft depth beyond which running further ahead lowers
throughput?

This integrates what `rime_agents.py` in the universe simulator demonstrates separately.
The MTP agent drafts; one verifier pass checks the whole draft in parallel; the longest
agreeing prefix is committed; everything after the first disagreement is rolled back.

## Corpus

`enwik8`, 100,000,000 bytes, MD5 `a1fa5ffddb56f4953e226637dabbb36a`,
SHA-256 `2b49720ec4d78c3c9fabaee6e4179a5e997302b3a70029f30f2d582218c024a8`.

- Train: bytes `[0, 20,000,000)`.
- Held out: anchors are drawn only from `[95,000,000, 99,998,976)`.

## Agents (frozen after training, never retrained)

Count tables are exact sorted address files: for order `n`, key = `(context << 8) | next`,
where the context is the previous `n` bytes read big-endian. No hashing and no collisions.
A model of order `N` backs off `N → N−1 → … → 0` to the first context seen in training.

- **Draft (MTP):** order 2, the same frozen order-2 table as the simulator's MTP agent.
- **Verifier (big agent):** order 5.
- Distributions are the raw counts at the chosen context. Greedy picks the largest count,
  breaking ties by the smallest byte.

## Hash-sampled anchors (the hash trick)

A held-out position `p` is an anchor iff the first 8 bytes of
`SHA-256("SPEC-BRAKE-V1|" + decimal(p))`, read big-endian, are `≡ 0 (mod 8192)`.
Each anchor starts from the true 5 bytes before `p` and generates `T = 128` bytes.

## Protocol (speculative sampling, exact integers)

Each cycle at draft depth `k`:

1. **Draft:** the draft samples `x₁ … x_k` autoregressively from its own counts.
2. **Verify:** the verifier gives its counts at positions `1 … k+1`. That is one verifier
   pass.
3. **Accept or reject:** for `i = 1 … k`, with draft count `c_p` of `N_p` and verifier
   count `c_q` of `N_q`, draw an integer `u` uniformly from `[0, c_p·N_q)` and accept iff
   `u < c_q·N_p`. This is `min(1, q/p)` exactly.
   - On the first reject, sample from the residual weights `max(0, c_q(y)·N_p − c_p(y)·N_q)`
     and end the cycle.
   - If all `k` are accepted, sample a bonus byte from the verifier at position `k+1`.
4. **Commit and roll back:** commit the accepted bytes plus one. Roll back `k − a`
   draft bytes.

Random draws come from a SHA-256 counter stream seeded by `(anchor, k, variant)`, using
rejection so that no modulo bias enters. This is the Leviathan–Kalman–Matias
speculative-sampling rule (2023), with integer weights. It leaves the verifier's
distribution unchanged.

**Depths:** `k ∈ {1, 2, 3, 4, 6, 8, 12, 16, 27}`.

## Measured per depth (exact integer counts)

- cycles, bytes committed, accepted draft bytes, rolled-back draft bytes
- acceptance at draft position `i`: accepted_i out of reached_i
- wall time in integer nanoseconds (secondary: table lookups are cheap here, so wall time
  does not model an expensive verifier)

## Cost model and the braking point (primary)

Each cycle costs `k·D + V`, with `D = 1` per draft byte and `V = r` per verifier pass.
Throughput is `bytes / (cycles · (k + r))`. A verifier with no draft gives `1/r`.

For each `r ∈ {1, 4, 16, 64}`, `k*(r)` is the depth with the highest throughput among the
tested depths. Comparisons are made by exact integer cross-multiplication.

## Controls and gates

- **C1 oracle draft:** the draft is the verifier itself. Every draft byte must be
  accepted (`accepted = k · cycles`), and no depth may have strictly higher throughput
  than `k = 27`. (At `r = 1` the oracle's throughput is exactly 1 at every depth, a tie.)
- **C2 null draft:** a uniform draft over 256 bytes. This is reported, and its mean
  accepted bytes per cycle must fall below the order-2 draft's at every `k`.
- **C3 exactness:** greedy speculative decoding, in which the verifier commits its own
  byte at the first disagreement, must produce output byte-identical to plain greedy
  decoding by the verifier, at every anchor and every `k`.
- **C4 coverage:** every hash-selected anchor completes at every `k`, in every variant.

## Verdicts, fixed now

| Condition | Verdict |
|---|---|
| any gate fails | `INCONCLUSIVE` |
| `k*(r)` is interior (below 27) and throughput at 27 is strictly below throughput at `k*(r)` | `BRAKE_MEASURED(r) at k*` |
| `k*(r) = 27` | `NO_BRAKE_IN_RANGE(r)` |

**Expected beforehand.** If each draft byte were accepted independently with probability
`α`, a cycle would commit `(1 − α^(k+1)) / (1 − α)` bytes on average, and any `α < 1`
gives a finite best depth that grows with `r`. The measurement tests where the brake
falls and whether acceptance actually decays with draft position, which the independent
model does not allow.

## Smoke test (before the freeze)

A smoke test ran on two anchors from the training region (`SPEC_SMOKE=1`: positions
1,000,000–1,200,000, `T = 16`). It never touches the held-out anchors. It found that the
first version of the C1 gate misread the oracle's exact ties at `r = 1` as an interior
maximum, and the gate was corrected to the form above before this freeze.

## Scope

This measures an agent system on text. Local clocks, late messages and state restoration
(Time Warp) are not measured. Nothing here measures physical spacetime.
