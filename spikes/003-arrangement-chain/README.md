# 003: the arrangement chain (full song form)

## Question

The engine plays ONE pattern (or a UI-queued jump). Can a song carry its own
FORM — intro / themes / tension / break / outro — and play it end-to-end?

## Approach

- `Song` gains `queued_chain: Option<Vec<ChainLink>>` (`ChainLink { next:
  Option<usize> }`, `#[serde(default)]`). Missing field = today's loop
  behaviour. `queued` (the UI's live jump) still overrides the chain.
- `Engine::step()` at pattern wrap: UI override first, else chain successor.
- `sanitize()` clamps chain length and link targets (song files are untrusted).
- Generator emits the form A(intro) B C D | E(tension) F G(break) H -> B.
  Because harmony is per-pattern, the B-progression (with its harmonic-minor V)
  is carried BY the chain.

## Evidence

```
PATTERN_SWITCH bar=1.01 -> B
PATTERN_SWITCH bar=2.01 -> C
PATTERN_SWITCH bar=3.01 -> D
PATTERN_SWITCH bar=4.01 -> E
PATTERN_SWITCH bar=5.01 -> F
PATTERN_SWITCH bar=6.01 -> G
PATTERN_SWITCH bar=7.01 -> H
RENDERED frames=710400 peak=0.700 bpm=150 tracks=10
```

Rendered through the real engine (headless harness), 8 patterns, ~14.8 s WAV
at 150 BPM = exactly 8 bars. Switches land on bar boundaries (the +0.01 is the
harness reporting after the 512-frame render block).

## Verdict: VALIDATED

The other missing engine concept (after per-note pitch) works. A generated
song is a real SONG, not a loop.

### Recommendation for the real build
- Ship `queued_chain` as spiked; UI needs zero changes (it overrides only when
  the user queues, and never writes the field).
- The community-site player (player/) gets this for free via the same lib.
