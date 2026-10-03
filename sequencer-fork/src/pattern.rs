use serde::{Deserialize, Serialize};

use std::sync::Arc;

use crate::sound::Sample;

pub const MAX_STEPS: usize = 64;
pub const MAX_TRACKS: usize = 16;
pub const PATTERNS: usize = 8;

#[derive(Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum Cell {
    #[default]
    Off,
    On,
    Accent,
}

/// The notes of one track in one pattern.
#[derive(Clone, PartialEq, Serialize, Deserialize)]
pub struct Lane {
    pub cells: Vec<Cell>,
    /// Length in steps of the note starting at this step. 1 = one-shot, longer = cut off after that many steps.
    pub lens: Vec<u8>,
    /// Pitch offset in semitones per step, on top of the track pitch. Only read where a note starts;
    /// 0 everywhere is exactly the old behaviour. Old files without this field load as all zeros.
    #[serde(default = "default_notes")]
    pub notes: Vec<i8>,
}

fn default_notes() -> Vec<i8> {
    vec![0; MAX_STEPS]
}

impl Default for Lane {
    fn default() -> Self {
        Self { cells: vec![Cell::Off; MAX_STEPS], lens: vec![1; MAX_STEPS], notes: vec![0; MAX_STEPS] }
    }
}

impl Lane {
    /// The start step of the note covering step `s`, if any.
    pub fn note_at(&self, s: usize) -> Option<usize> {
        note_at_impl(&self.cells, &self.lens, s)
    }

    /// How many steps are free from `s` until the next note or the end of the grid.
    fn room(&self, s: usize, steps: usize) -> usize {
        (s + 1..steps).find(|&n| self.cells[n] != Cell::Off).unwrap_or(steps) - s
    }

    /// Places a note at `s`, as long as fits.
    pub fn place(&mut self, s: usize, cell: Cell, len: u8, steps: usize) {
        if s >= steps || self.note_at(s).is_some() {
            return;
        }
        self.cells[s] = cell;
        self.lens[s] = (len as usize).min(self.room(s, steps)).max(1) as u8;
    }

    pub fn erase(&mut self, s: usize) {
        if let Some(n) = note_at_impl(&self.cells, &self.lens, s) {
            self.cells[n] = Cell::Off;
            self.lens[n] = 1;
            self.notes[n] = 0;
        }
    }

    pub fn resize(&mut self, s: usize, delta: i32, steps: usize) {
        if let Some(n) = self.note_at(s) {
            let max = self.room(n, steps) as i32;
            self.lens[n] = (self.lens[n] as i32 + delta).clamp(1, max.min(16)) as u8;
        }
    }

    pub fn clear(&mut self) {
        self.cells.fill(Cell::Off);
        self.lens.fill(1);
        self.notes.fill(0);
    }

    fn sanitize(&mut self) {
        self.cells.resize(MAX_STEPS, Cell::Off);
        self.lens.resize(MAX_STEPS, 1);
        self.notes.resize(MAX_STEPS, 0);
        for l in &mut self.lens {
            *l = (*l).clamp(1, 16);
        }
        for n in &mut self.notes {
            *n = (*n).clamp(-24, 24);
        }
    }
}

#[derive(Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum FilterKind {
    #[default]
    Off,
    Low,
    High,
    Band,
}

/// The start step of the note covering step `s`, shared with the UI, which
/// shows and edits pitches on borrowed lanes it cannot call methods on.
pub fn note_at_impl(cells: &[Cell], lens: &[u8], s: usize) -> Option<usize> {
    (0..=s).rev().find(|&n| cells[n] != Cell::Off && n + lens[n] as usize > s)
}

/// Effects on one track, applied to everything the track plays before it goes to the mix.
#[derive(Clone, PartialEq, Serialize, Deserialize)]
#[serde(default)]
pub struct Fx {
    pub filter: FilterKind,
    /// 0..1, mapped exponentially from 40 Hz to 18 kHz.
    pub cutoff: f32,
    pub resonance: f32,
    /// Saturation, 0 = clean.
    pub drive: f32,
    /// Bit reduction, 0 = off, 1 = 2 bits.
    pub crush: f32,
    /// Sample rate reduction, 0 = off.
    pub downsample: f32,
    /// Hard clipping distortion, 0 = off.
    pub distort: f32,
    /// Fine tuning in cents, on top of the track pitch.
    pub fine: f32,
    /// Play the sample backwards.
    pub reverse: bool,
    /// Ring modulator mix and frequency (0..1, mapped from 30 Hz to 2 kHz).
    pub ring: f32,
    pub ring_freq: f32,
    /// Tempo synced gate: depth and length of one on/off cycle in steps.
    pub chop: f32,
    pub chop_steps: u8,
    /// Send to the reverb.
    pub reverb: f32,
    /// Delay time in sixteenth notes and how much of it comes back. The amount is `Track::send`.
    pub delay_steps: u8,
    pub feedback: f32,
    /// Three band EQ in dB: low shelf (100 Hz), mid peak (1 kHz), high shelf (8 kHz).
    pub eq_low: f32,
    pub eq_mid: f32,
    pub eq_high: f32,
}

impl Default for Fx {
    fn default() -> Self {
        Self {
            filter: FilterKind::Off,
            cutoff: 0.6,
            resonance: 0.2,
            drive: 0.0,
            crush: 0.0,
            downsample: 0.0,
            distort: 0.0,
            fine: 0.0,
            reverse: false,
            ring: 0.0,
            ring_freq: 0.4,
            chop: 0.0,
            chop_steps: 1,
            reverb: 0.0,
            delay_steps: 3,
            feedback: 0.35,
            eq_low: 0.0,
            eq_mid: 0.0,
            eq_high: 0.0,
        }
    }
}

impl Fx {
    pub fn active(&self) -> bool {
        self.filter != FilterKind::Off
            || self.drive > 0.0
            || self.crush > 0.0
            || self.downsample > 0.0
            || self.distort > 0.0
            || self.fine != 0.0
            || self.reverse
            || self.ring > 0.0
            || self.chop > 0.0
            || self.reverb > 0.0
            || self.eq_low != 0.0
            || self.eq_mid != 0.0
            || self.eq_high != 0.0
    }

    fn sanitize(&mut self) {
        self.cutoff = self.cutoff.clamp(0.0, 1.0);
        self.resonance = self.resonance.clamp(0.0, 1.0);
        self.drive = self.drive.clamp(0.0, 1.0);
        self.crush = self.crush.clamp(0.0, 1.0);
        self.downsample = self.downsample.clamp(0.0, 1.0);
        self.distort = self.distort.clamp(0.0, 1.0);
        self.fine = self.fine.clamp(-100.0, 100.0);
        self.ring = self.ring.clamp(0.0, 1.0);
        self.ring_freq = self.ring_freq.clamp(0.0, 1.0);
        self.chop = self.chop.clamp(0.0, 1.0);
        self.chop_steps = self.chop_steps.clamp(1, 8);
        self.reverb = self.reverb.clamp(0.0, 1.0);
        self.delay_steps = self.delay_steps.clamp(1, 16);
        self.feedback = self.feedback.clamp(0.0, 0.9);
        self.eq_low = self.eq_low.clamp(-12.0, 12.0);
        self.eq_mid = self.eq_mid.clamp(-12.0, 12.0);
        self.eq_high = self.eq_high.clamp(-12.0, 12.0);
    }
}

#[derive(Clone, PartialEq, Serialize, Deserialize)]
pub struct Track {
    pub sample: usize,
    /// One lane per pattern (A to H).
    pub lanes: Vec<Lane>,
    /// Length for newly placed notes.
    pub note_len: u8,
    pub volume: f32,
    pub pitch: f32,
    /// -1 left, 0 center, 1 right.
    pub pan: f32,
    /// How much of this track goes to the delay.
    pub send: f32,
    #[serde(default)]
    pub fx: Fx,
    pub mute: bool,
    pub solo: bool,
}

impl Track {
    pub fn new(sample: usize, note_len: u8) -> Self {
        Self {
            sample,
            lanes: vec![Lane::default(); PATTERNS],
            note_len,
            volume: 0.8,
            pitch: 0.0,
            pan: 0.0,
            send: 0.0,
            fx: Fx::default(),
            mute: false,
            solo: false,
        }
    }
}

/// One entry of the song form: which pattern follows this one, if any.
#[derive(Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub struct ChainLink {
    pub next: Option<usize>,
}

#[derive(Clone, PartialEq, Serialize, Deserialize)]
pub struct Song {
    pub bpm: f32,
    pub swing: f32,
    pub master: f32,
    /// Number of steps per pattern.
    pub steps: Vec<usize>,
    /// The pattern that plays and that you edit.
    pub current: usize,
    /// Switches to this pattern at the end of the current one.
    pub queued: Option<usize>,
    /// Per-pattern successor: the song form. `queued` (and the UI) still override it;
    /// when both are unset the pattern loops. Old files without the field just loop.
    #[serde(default)]
    pub queued_chain: Option<Vec<ChainLink>>,
    pub tracks: Vec<Track>,
}

impl Song {
    fn empty(tracks: Vec<Track>, bpm: f32, steps: usize) -> Self {
        Self {
            bpm,
            swing: 0.0,
            master: 0.8,
            steps: vec![steps; PATTERNS],
            current: 0,
            queued: None,
            queued_chain: None,
            tracks,
        }
    }

    pub fn steps(&self) -> usize {
        self.steps[self.current]
    }

    pub fn demo(samples: &[Arc<Sample>]) -> Self {
        let idx = |name: &str| samples.iter().position(|s| s.name == name).unwrap_or(0);
        let tracks = ["kick", "snare", "clap", "hat_closed", "hat_open", "cowbell", "bass_hit", "plucks"]
            .iter()
            .map(|n| {
                let s = idx(n);
                Track::new(s, samples[s].default_len())
            })
            .collect();
        let mut song = Self::empty(tracks, 124.0, 16);
        song.swing = 0.08;
        let mut put = |t: usize, p: usize, hits: &[usize], accents: &[usize]| {
            let len = song.tracks[t].note_len;
            for &h in hits {
                let cell = if accents.contains(&h) { Cell::Accent } else { Cell::On };
                song.tracks[t].lanes[p].place(h, cell, len, 16);
            }
        };
        // A: basic groove.
        put(0, 0, &[0, 4, 8, 12], &[0]);
        put(1, 0, &[4, 12], &[]);
        put(3, 0, &[0, 2, 4, 6, 8, 10, 12, 14], &[2, 6, 10, 14]);
        put(4, 0, &[7, 15], &[]);
        put(6, 0, &[0, 6, 10], &[0]);
        // B: fuller, with clap, cowbell and plucks.
        put(0, 1, &[0, 4, 8, 12, 14], &[0]);
        put(1, 1, &[4, 12], &[]);
        put(2, 1, &[12], &[]);
        put(3, 1, &[0, 2, 4, 6, 8, 10, 12, 14], &[2, 6, 10, 14]);
        put(4, 1, &[7, 15], &[]);
        put(5, 1, &[3, 11], &[]);
        put(6, 1, &[0, 3, 6, 10], &[0]);
        put(7, 1, &[8], &[]);
        song.tracks[4].volume = 0.5;
        song.tracks[4].pan = 0.3;
        song.tracks[5].volume = 0.4;
        song.tracks[5].pan = -0.4;
        song.tracks[7].send = 0.4;
        song
    }

    /// A 135 BPM rave pattern with long notes for loop, stabs, hoover and acid.
    pub fn rave(samples: &[Arc<Sample>]) -> Self {
        let idx = |name: &str| samples.iter().position(|s| s.name == name).unwrap_or(0);
        let row = |name: &str, notes: &[(usize, u8, bool)], volume: f32, pan: f32, send: f32| {
            let sample = idx(name);
            let mut t = Track::new(sample, samples[sample].default_len());
            for &(s, len, accent) in notes {
                t.lanes[0].place(s, if accent { Cell::Accent } else { Cell::On }, len, 32);
            }
            t.volume = volume;
            t.pan = pan;
            t.send = send;
            t
        };
        let four = (0..32).step_by(4).map(|s| (s, 1, s % 16 == 0)).collect::<Vec<_>>();
        let hats = (2..32).step_by(4).map(|s| (s, 1, false)).collect::<Vec<_>>();
        let tracks = vec![
            row("kick", &four, 0.9, 0.0, 0.0),
            row("rave_loop_135", &[(0, 16, false), (16, 16, true)], 0.6, 0.0, 0.0),
            row("hat_open", &hats, 0.4, 0.35, 0.0),
            row("clap", &[(4, 1, false), (12, 1, false), (20, 1, false), (28, 1, true)], 0.6, 0.0, 0.2),
            row("hoover", &[(0, 8, true), (24, 8, false)], 0.5, -0.2, 0.2),
            row("rave_stab", &[(3, 2, true), (6, 2, false), (10, 4, false), (19, 2, true), (22, 2, false)], 0.6, 0.25, 0.45),
            row("acid_line", &[(8, 4, false), (12, 4, true), (16, 8, false)], 0.45, -0.3, 0.3),
            row("orch_hit", &[(0, 1, true), (16, 1, false)], 0.5, 0.0, 0.5),
            row("m1_organ", &[(14, 2, false), (30, 2, false)], 0.5, 0.2, 0.2),
            row("everybody", &[(28, 1, false)], 0.7, 0.0, 0.4),
        ];
        Self::empty(tracks, 135.0, 32)
    }

    /// A laid-back 98 BPM groove with lots of room: kick, snare, offbeat hats, bass and a Rhodes chord.
    pub fn late_night(samples: &[Arc<Sample>]) -> Self {
        let idx = |name: &str| samples.iter().position(|s| s.name == name).unwrap_or(0);
        let row = |name: &str, lanes: &[&[(usize, u8, bool)]], volume: f32, pan: f32, fx: Fx, send: f32| {
            let sample = idx(name);
            let mut t = Track::new(sample, samples[sample].default_len());
            for (p, notes) in lanes.iter().enumerate() {
                for &(s, len, accent) in notes.iter() {
                    t.lanes[p].place(s, if accent { Cell::Accent } else { Cell::On }, len, 16);
                }
            }
            t.volume = volume;
            t.pan = pan;
            t.fx = fx;
            t.send = send;
            t
        };
        let hats: &[(usize, u8, bool)] = &[(2, 1, false), (6, 1, false), (10, 1, false), (14, 1, false)];
        let tracks = vec![
            row("kick", &[&[(0, 1, true), (10, 1, false)], &[(0, 1, true), (10, 1, false)], &[]], 0.9, 0.0, Fx { eq_low: 3.0, ..Fx::default() }, 0.0),
            row("snare", &[&[(4, 1, false), (12, 1, false)], &[(4, 1, false), (12, 1, false)], &[(12, 1, false)]], 0.6, 0.0, Fx { reverb: 0.3, ..Fx::default() }, 0.0),
            row("hat_closed", &[hats, hats, hats], 0.35, 0.2, Fx { filter: FilterKind::High, cutoff: 0.45, ..Fx::default() }, 0.0),
            row(
                "bass_hit",
                &[&[(0, 2, true), (10, 2, false)], &[(0, 2, true), (7, 1, false), (10, 2, false)], &[(0, 4, true)]],
                0.7,
                0.0,
                Fx { drive: 0.15, ..Fx::default() },
                0.0,
            ),
            row(
                "rhodes_chord",
                &[&[(2, 8, false)], &[(2, 8, false)], &[(2, 12, false)]],
                0.45,
                -0.1,
                Fx { filter: FilterKind::Low, cutoff: 0.7, resonance: 0.2, reverb: 0.4, delay_steps: 3, feedback: 0.4, ..Fx::default() },
                0.3,
            ),
            row("plucks", &[&[], &[(8, 4, false)], &[(8, 4, false)]], 0.3, 0.35, Fx { reverb: 0.35, delay_steps: 6, feedback: 0.45, ..Fx::default() }, 0.45),
        ];
        let mut song = Self::empty(tracks, 98.0, 16);
        song.swing = 0.14;
        song.tracks[3].pitch = -2.0;
        song
    }

    /// An empty song to start from: a few drum tracks and nothing on the grid.
    pub fn blank(samples: &[Arc<Sample>]) -> Self {
        let idx = |name: &str| samples.iter().position(|s| s.name == name).unwrap_or(0);
        let tracks = ["kick", "snare", "clap", "hat_closed", "hat_open", "bass_hit"]
            .iter()
            .map(|n| {
                let s = idx(n);
                Track::new(s, samples[s].default_len())
            })
            .collect();
        Self::empty(tracks, 120.0, 16)
    }

    /// Clamps everything that came from a file into range and resolves sample names to indexes.
    pub fn sanitize(&mut self, names: &[String], samples: &[Arc<Sample>]) {
        self.tracks.truncate(MAX_TRACKS);
        for (t, name) in self.tracks.iter_mut().zip(names) {
            t.sample = samples.iter().position(|s| &s.id == name).or_else(|| samples.iter().position(|s| &s.name == name)).unwrap_or(0);
        }
        for t in &mut self.tracks {
            t.sample = t.sample.min(samples.len() - 1);
            t.lanes.resize(PATTERNS, Lane::default());
            t.lanes.iter_mut().for_each(Lane::sanitize);
            t.volume = t.volume.clamp(0.0, 1.0);
            t.pitch = t.pitch.clamp(-24.0, 24.0);
            t.pan = t.pan.clamp(-1.0, 1.0);
            t.send = t.send.clamp(0.0, 1.0);
            t.note_len = t.note_len.clamp(1, 16);
            t.fx.sanitize();
        }
        self.steps.resize(PATTERNS, 16);
        for s in &mut self.steps {
            *s = (*s).clamp(1, MAX_STEPS);
        }
        self.current = self.current.min(PATTERNS - 1);
        self.queued = None;
        match &mut self.queued_chain {
            Some(chain) => {
                chain.resize(PATTERNS, ChainLink::default());
                for link in chain.iter_mut() {
                    if let Some(n) = link.next {
                        link.next = Some(n.min(PATTERNS - 1));
                    }
                }
            }
            None => {}
        }
        self.bpm = self.bpm.clamp(40.0, 300.0);
        self.swing = self.swing.clamp(0.0, 0.5);
        self.master = self.master.clamp(0.0, 1.0);
    }

    pub fn any_solo(&self) -> bool {
        self.tracks.iter().any(|t| t.solo)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Arc;

    fn lane_with(cells: &[(usize, i8)]) -> Lane {
        let mut lane = Lane::default();
        for &(s, note) in cells {
            lane.place(s, Cell::On, 1, 16);
            lane.notes[s] = note;
        }
        lane
    }

    #[test]
    fn notes_roundtrip_through_json() {
        let mut lane = lane_with(&[(0, -7), (4, 12)]);
        let json = serde_json::to_string(&lane).unwrap();
        assert!(json.contains("\"notes\""));
        let back: Lane = serde_json::from_str(&json).unwrap();
        assert_eq!(back.notes[0], -7);
        assert_eq!(back.notes[4], 12);
        assert_eq!(back.notes[1], 0);
    }

    #[test]
    fn old_files_without_notes_load_as_zero() {
        // A 1.2.1-era lane carried only cells and lens.
        let old = r#"{"cells":["On","Off"],"lens":[1,1]}"#;
        let lane: Lane = serde_json::from_str(old).unwrap();
        assert_eq!(lane.notes, vec![0; MAX_STEPS]);
    }

    #[test]
    fn sanitize_clamps_note_offsets() {
        let mut lane = lane_with(&[(0, 99), (2, -99)]);
        lane.sanitize();
        assert_eq!(lane.notes[0], 24);
        assert_eq!(lane.notes[2], -24);
    }

    #[test]
    fn clear_resets_notes() {
        let mut lane = lane_with(&[(0, 5)]);
        lane.clear();
        assert!(lane.notes.iter().all(|&n| n == 0));
    }

    fn song_with_chain(next: &[Option<usize>]) -> Song {
        let sample = Arc::new(crate::sound::Sample {
            name: "x".into(),
            pack: "classic".into(),
            id: "x".into(),
            kind: crate::sound::Kind::Drum,
            data: vec![0.0; 8],
            rate: 44_100,
        });
        let mut song = Song::blank(&[sample]);
        song.queued_chain = Some(next.iter().map(|&n| ChainLink { next: n }).collect());
        song
    }

    #[test]
    fn song_without_chain_field_still_loads() {
        let old = r#"{"bpm":120.0,"swing":0.0,"master":0.8,"steps":[16,16,16,16,16,16,16,16],"current":0,"queued":null,"tracks":[]}"#;
        let song: Song = serde_json::from_str(old).unwrap();
        assert!(song.queued_chain.is_none());
    }

    #[test]
    fn sanitize_clamps_the_chain() {
        let mut song = song_with_chain(&[Some(20), None, None, None, None, None, None, None, Some(1), Some(2)]);
        let samples = vec![Arc::new(crate::sound::Sample {
            name: "x".into(),
            pack: "classic".into(),
            id: "x".into(),
            kind: crate::sound::Kind::Drum,
            data: vec![0.0; 8],
            rate: 44_100,
        })];
        song.sanitize(&["x".into()], &samples);
        let chain = song.queued_chain.unwrap();
        // Truncated to one link per pattern, out-of-range targets clamped.
        assert_eq!(chain.len(), PATTERNS);
        assert_eq!(chain[0].next, Some(PATTERNS - 1));
        assert_eq!(chain[7].next, None);
    }
}
