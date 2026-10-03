//! Headless render harness for the omainur spike.
//!
//! Loads WAVs from a directory as samples, reads a generated song JSON, renders the
//! full pattern chain through the real engine, writes a stereo WAV, and prints the
//! rendered pitch (MIDI note estimate) of every sample so the pitch chain is checkable.
//!
//! Usage:
//!   render <wav_dir> <song.json> <out.wav> <bars>
//!   render --analyze <wav_dir>          (just print sample pitches)

use omarchy_sequencer::engine::{Engine, Shared};
use omarchy_sequencer::pattern::Song;
use omarchy_sequencer::sound::{decode, Kind, Sample};
use std::fs::File;
use std::io::BufReader;
use std::sync::Arc;

fn guess_kind(name: &str) -> Kind {
    const DRUMS: [&str; 8] = ["kick", "snare", "hat", "clap", "tom", "ride", "crash", "perc"];
    if DRUMS.iter().any(|d| name.contains(d)) {
        Kind::Drum
    } else if name.contains("bass") {
        Kind::Riff
    } else {
        Kind::Pack
    }
}

fn load_dir(dir: &str) -> Vec<Arc<Sample>> {
    if !std::path::Path::new(dir).exists() {
        panic!("no wav dir {dir}");
    }
    // Walk recursively: packs may namespace their samples into subdirectories.
    let mut paths: Vec<_> = vec![std::path::PathBuf::from(dir)];
    let mut wavs = Vec::new();
    while let Some(dir) = paths.pop() {
        for entry in std::fs::read_dir(&dir).expect("read_dir").flatten() {
            let p = entry.path();
            if p.is_dir() {
                paths.push(p);
            } else if p.extension().is_some_and(|e| e.eq_ignore_ascii_case("wav")) {
                wavs.push(p);
            }
        }
    }
    wavs.sort();
    wavs
        .iter()
        .filter_map(|p| {
            // The id is the path relative to the wav dir (subdirs included), lowercased
            // with separators as underscores, matching how ids travel in song files.
            let rel = p.strip_prefix(dir).unwrap_or(p).to_string_lossy().to_lowercase();
            let stem = rel.trim_end_matches(".wav").replace('/', "_");
            let f = File::open(p).ok()?;
            decode(&stem, guess_kind(&stem), "omainur", BufReader::new(f))
        })
        .map(Arc::new)
        .collect()
}

/// Fundamental estimate by autocorrelation on a decimated analysis signal.
/// Returns the MIDI note number, or 0 when nothing periodic was found.
fn estimate_midi(s: &Sample) -> f32 {
    let decim = 6usize;
    let rate = s.rate as usize / decim;
    let data = &s.data;
    let skip = (s.rate as usize / 200).min(data.len() / 4); // ride out the onset
    let take = (s.rate as usize / 4).min(data.len() - skip);
    if take < 512 {
        return 0.0;
    }
    // Box-filter then decimate.
    let mut x = vec![0.0f32; take / decim];
    for (i, v) in x.iter_mut().enumerate() {
        let sum: f32 = data[skip + i * decim..skip + (i + 1) * decim].iter().sum();
        *v = sum / decim as f32;
    }
    let mean = x.iter().sum::<f32>() / x.len() as f32;
    for v in &mut x {
        *v -= mean;
    }
    let min_lag = (rate / 1100).max(2);
    let max_lag = (rate / 30).min(x.len() / 2);
    if min_lag >= max_lag {
        return 0.0;
    }
    let mut best = (0.0f32, 0usize);
    for lag in min_lag..=max_lag {
        let r: f32 = x[..x.len() - lag].iter().zip(&x[lag..]).map(|(a, b)| a * b).sum();
        if r > best.0 {
            best = (r, lag);
        }
    }
    if best.1 == 0 || best.0 <= 1e-9 {
        return 0.0;
    }
    // Parabolic refinement around the peak.
    let lag = best.1;
    let ym: f32 = x[..x.len() - (lag - 1)].iter().zip(&x[lag - 1..]).map(|(a, b)| a * b).sum();
    let y0: f32 = x[..x.len() - lag].iter().zip(&x[lag..]).map(|(a, b)| a * b).sum();
    let yp: f32 = x[..x.len() - (lag + 1)].iter().zip(&x[lag + 1..]).map(|(a, b)| a * b).sum();
    let denom = ym - 2.0 * y0 + yp;
    let delta = if denom.abs() > 1e-12 { 0.5 * (ym - yp) / denom } else { 0.0 };
    let refined = lag as f32 + delta.clamp(-1.0, 1.0);
    let f0 = rate as f32 / refined;
    69.0 + 12.0 * (f0 / 440.0).log2()
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let (wav_dir, song_path, out_path, bars) = match args.first().map(|s| s.as_str()) {
        Some("--analyze") => (args[1].clone(), String::new(), String::new(), 0),
        _ => (args[0].clone(), args[1].clone(), args[2].clone(), args[3].parse().expect("bars")),
    };
    let samples = load_dir(&wav_dir);
    for s in &samples {
        println!("SAMPLE name={} frames={} midi_est={:.2}", s.name, s.data.len(), estimate_midi(s));
    }
    if song_path.is_empty() {
        return;
    }
    let rate: u32 = 48_000;
    let text = std::fs::read_to_string(&song_path).expect("song json");
    // Accept both the app's file format ({song: ...}) and a bare Song.
    let wrapped: Result<omarchy_sequencer::pattern::Song, _> = serde_json::from_str(&text);
    let mut song: Song = match wrapped {
        Ok(s) => s,
        Err(_) => serde_json::from_str::<serde_json::Value>(&text)
            .ok()
            .and_then(|v| serde_json::from_value(v["song"].clone()).ok())
            .expect("parse song"),
    };
    let names: Vec<String> = samples.iter().map(|s| s.id.clone()).collect();
    song.sanitize(&names, &samples);

    let step_len = rate as f64 * 60.0 / song.bpm as f64 / 4.0;
    // One pattern (16 steps) is one bar of 4/4.
    let music = (bars as f64 * 16.0 * step_len) as usize;
    let frames = music + rate as usize * 2;

    let shared = Arc::new(Shared::new(song.clone()));
    shared.playing.store(true, std::sync::atomic::Ordering::Relaxed);
    let mut engine = Engine::new(samples, shared.clone(), rate);
    let mut out = vec![0.0f32; frames * 2];
    let mut done = 0;
    let mut last_active = song.current;
    while done < frames {
        let n = (frames - done).min(512);
        if done >= music {
            shared.playing.store(false, std::sync::atomic::Ordering::Relaxed);
        }
        engine.render(&mut out[done * 2..(done + n) * 2]);
        done += n;
        let act = shared.active.load(std::sync::atomic::Ordering::Relaxed);
        if act != last_active {
            let bar = done as f64 / (step_len * 16.0);
            println!("PATTERN_SWITCH bar={:.2} -> {}", bar, (b'A' + act as u8) as char);
            last_active = act;
        }
    }

    let peak = out.iter().fold(1e-9f32, |m, v| m.max(v.abs()));
    println!("RENDERED frames={frames} peak={peak:.3} bpm={} tracks={}", song.bpm, song.tracks.len());
    let spec = hound::WavSpec { channels: 2, sample_rate: rate, bits_per_sample: 16, sample_format: hound::SampleFormat::Int };
    let mut w = hound::WavWriter::create(&out_path, spec).expect("wav out");
    for v in &out {
        w.write_sample((v.clamp(-1.0, 1.0) * 32767.0) as i16).unwrap();
    }
    w.finalize().unwrap();
    println!("WROTE {out_path}");
}
