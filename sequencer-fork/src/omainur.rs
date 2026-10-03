//! The omainur layer, in Rust: ontology as code, one language with the app.
//!
//! Faithful port of `omainur/generator/omainur_gen.py` + `hook_form.py`
//! (spikes 002 and 005-009; python original preserved on `dev-history`).
//! Each item cites its python twin. The contract this port must hold:
//! the same (genre, seed) produces a Song equal, after serde round-trip,
//! to what the python generator wrote — asserted by tests/determinism.

use crate::pattern::{ChainLink, Cell, Fx, Song, Track};

/// The theory core (py: PC, SCALES, CHORD_DEGREES usage in chord_tones()).
pub const PC: &[(&str, i32); 16] = &[
    ("c", 0), ("c#", 1), ("db", 1), ("d", 2), ("d#", 3), ("eb", 4), ("e", 4), ("f", 5),
    ("f#", 6), ("gb", 6), ("g", 7), ("g#", 8), ("ab", 8), ("a", 9), ("bb", 10), ("b", 11),
];

pub const NATURAL_MIN: [i32; 7] = [0, 2, 3, 5, 7, 8, 10];
pub const HARMONIC_MIN: [i32; 7] = [0, 2, 3, 5, 7, 8, 11];
pub const DORIAN: [i32; 7] = [0, 2, 3, 5, 7, 9, 10];
pub const MIXOLYDIAN: [i32; 7] = [0, 2, 4, 5, 7, 9, 10];
pub const MAJOR: [i32; 7] = [0, 2, 4, 5, 7, 9, 11];

pub fn pc_of(name: &str) -> i32 {
    PC.iter().find(|(n, _)| *n == name).map(|(_, v)| *v).unwrap_or(0)
}

/// The LCG (py: class LCG) — masking arithmetic preserved exactly.
pub struct Lcg(u32);

impl Lcg {
    pub fn new(seed: u32) -> Self {
        Lcg(seed & 0xFFFF_FFFF)
    }
    pub fn next(&mut self) -> u32 {
        self.0 = self.0.wrapping_mul(1664525).wrapping_add(1013904223) & 0xFFFF_FFFF;
        self.0 >> 8
    }
    pub fn pick(&mut self, n: usize) -> usize {
        (self.next() as usize) % n.max(1)
    }
    pub fn chance(&mut self, pct: u32) -> bool {
        (self.next() % 100) < pct
    }
}

/// Scale degrees of each chord tone (py: CHORD_DEGREES).
const CHORD_DEGREES_SEVENTH: [usize; 4] = [0, 2, 4, 6];
const CHORD_DEGREES_TRIAD: [usize; 3] = [0, 2, 4];

/// Pitch classes of the diatonic 7th (or triad) on `degree` (py: chord_tones).
pub fn chord_tones(root: i32, scale: &[i32; 7], degree: usize, seventh: bool) -> Vec<i32> {
    let steps = if seventh { &CHORD_DEGREES_SEVENTH[..] } else { &CHORD_DEGREES_TRIAD[..] };
    let mut set: Vec<i32> = steps
        .iter()
        .map(|&i| (root + scale[(degree + i) % 7]) % 12)
        .collect();
    set.sort_unstable();
    set.dedup();
    set
}

/// All midi notes in [lo, hi] on the scale, ascending (py: scale_range).
pub fn scale_range(root: i32, scale: &[i32; 7], lo: i32, hi: i32) -> Vec<i32> {
    (lo..=hi).filter(|m| (m - root).rem_euclid(12) != -1 && scale.contains(&(m - root).rem_euclid(12))).collect()
}

/// (degree 0-6, seventh?, scale override) — py: P() entries.
pub type ProgEntry = (usize, bool, Option<&'static [i32; 7]>);

pub struct Groove {
    pub kick: &'static [usize],
    pub snare: &'static [usize],
    pub clap: &'static [usize],
    pub hat: &'static [usize],
}

/// One fx assignment: (role, key, value) triples (py: genre["mix"] dicts).
pub enum FxVal {
    F(f32),
    Filter(&'static str),
    B(bool),
}
pub type FxSpec = (&'static str, &'static str, FxVal);

pub struct LeadRange {
    pub lo: i32,
    pub hi: i32,
    pub anchor: i32,
}

pub struct Genre {
    pub bpm: f32,
    pub swing: f32,
    pub steps: usize,
    pub root: i32,
    pub scale: &'static [i32; 7],
    pub prog: [ProgEntry; 4],
    pub prog_b: [ProgEntry; 4],
    pub groove: Groove,
    pub bass_fig: &'static [(usize, i32)],
    pub lead: LeadRange,
    pub bass_range: (i32, i32),
    pub bass_anchor: i32,
    pub stab: &'static [(usize, usize)],
    pub mix: &'static [FxSpec],
}

/// The castle lane (py: GENRES["castle"]; added this series, spike-series 005+).
pub static CASTLE: Genre = Genre {
    bpm: 140.0,
    swing: 0.0,
    steps: 16,
    root: pc_of("e"),
    scale: &HARMONIC_MIN,
    // Em C D Em / Em Am C B7 — harmonic-minor modal rock (i VI VII, i iv VI V7)
    prog: [(0, true, None), (5, true, None), (6, true, None), (0, true, None)],
    prog_b: [(0, true, None), (3, true, None), (5, true, None), (4, true, Some(&HARMONIC_MIN))],
    groove: Groove { kick: &[0, 8], snare: &[4, 12], clap: &[], hat: &[0, 2, 4, 6, 8, 10, 12, 14] },
    // octave-gallop bass
    bass_fig: &[(0, 0), (2, 12), (4, 0), (6, 12), (8, 0), (10, 12), (12, 0), (14, 12)],
    lead: LeadRange { lo: 59, hi: 80, anchor: 64 },
    bass_range: (28, 43),
    bass_anchor: 33,
    stab: &[(0, 4), (6, 2), (8, 4), (14, 2)],
    mix: &[
        ("lead", "crush", FxVal::F(0.45)),
        ("lead", "reverb", FxVal::F(0.4)),
        ("lead", "delay_steps", FxVal::F(3.0)),
        ("lead", "feedback", FxVal::F(0.35)),
        ("lead", "send", FxVal::F(0.4)),
        ("bass", "filter", FxVal::Filter("Low")),
        ("bass", "cutoff", FxVal::F(0.5)),
        ("stab", "reverb", FxVal::F(0.55)),
        ("arp", "reverb", FxVal::F(0.35)),
        ("arp", "send", FxVal::F(0.3)),
    ],
};