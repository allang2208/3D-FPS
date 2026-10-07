"""Author the eight S_M10_* creature sounds from CC0 source recordings.

Sources are freesound.org preview MP3s (CC0) plus one OpenGameArt WAV already
staged under ../AudioScout. Every output is 44100 Hz mono 16-bit PCM. Segment
choices are deterministic envelope picks so the build reproduces byte-exact.
"""
import json, subprocess, wave
from pathlib import Path
import numpy as np
import imageio_ffmpeg
from scipy.signal import butter, sosfilt, resample_poly

ROOT = Path(__file__).resolve().parent
PREV = ROOT.parent / "AudioScout" / "Previews"
OGA = ROOT.parent / "AudioScout" / "OGA_Packs"
OUT = ROOT / "Wav"; OUT.mkdir(parents=True, exist_ok=True)
(ROOT / "Records").mkdir(exist_ok=True)
SR = 44100
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
rng = np.random.default_rng(104)


def load(path):
    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(path),
           "-ac", "1", "-ar", str(SR), "-f", "f32le", "pipe:1"]
    raw = subprocess.run(cmd, check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype="<f4").astype(np.float64)


def env_rms(y, win=0.05):
    n = max(1, int(win * SR))
    count = len(y) // n
    return np.sqrt((y[:count * n].reshape(count, n) ** 2).mean(axis=1))


def window(y, seconds, mode, offset=0.0):
    """Pick a deterministic segment: 'loud' = max RMS, 'calm' = 35th pct RMS,
    'steady' = median RMS, 'attack' = largest RMS derivative onset."""
    n = int(seconds * SR)
    if len(y) <= n:
        return y.copy()
    e = env_rms(y)
    w = max(1, int(seconds / 0.05))
    if mode == "attack":
        d = np.diff(e)
        i = int(np.argmax(d[int(offset / 0.05):-w]) + offset / 0.05)
    else:
        score = np.convolve(e, np.ones(w) / w, "valid")
        lo = int(offset / 0.05)
        if mode == "loud":
            i = int(np.argmax(score[lo:]) + lo)
        else:
            pct = 35.0 if mode == "calm" else 55.0
            target = np.percentile(score, pct)
            i = int(np.argmin(np.abs(score[lo:] - target)) + lo)
    return y[int(i * 0.05 * SR):int(i * 0.05 * SR) + n].copy()


def pitch(y, f):
    """Speed change: f < 1 lowers pitch and stretches the clip."""
    if abs(f - 1.0) < 1e-4:
        return y
    from math import gcd
    num, den = 1000, int(round(1000 * f))
    g = gcd(num, den)
    return resample_poly(y, num // g, den // g)


def band(y, lo, hi):
    return sosfilt(butter(3, [lo, hi], btype="bandpass", fs=SR, output="sos"), y)


def lowp(y, hi):
    return sosfilt(butter(3, hi, btype="lowpass", fs=SR, output="sos"), y)


def highp(y, lo):
    return sosfilt(butter(3, lo, btype="highpass", fs=SR, output="sos"), y)


def fade(y, fin=0.0, fout=0.0):
    t = np.arange(len(y)) / SR
    g = np.ones(len(y))
    if fin > 0:
        g *= np.clip(t / fin, 0, 1)
    if fout > 0:
        g *= np.clip((len(y) / SR - t) / fout, 0, 1)
    return y * g


def loopify(y, xf):
    """Rotate the loop start xf into the segment, then fold the last xf onto
    the head continuation. Every join is a consecutive source sample, so the
    wrap is click-free by construction."""
    n = int(xf * SR)
    m = len(y) - n
    if m <= n:
        return y
    r = np.arange(n) / max(1, n - 1)
    out = np.empty(m)
    out[:m - n] = y[n:m]
    out[m - n:] = y[m:m + n] * (1 - r) + y[:n] * r
    return out


def place(base, layer, at, gain=1.0):
    i = int(at * SR)
    j = min(len(base), i + len(layer))
    if j > i:
        base[i:j] += layer[:j - i] * gain
    return base


def norm(y, peak):
    m = float(np.max(np.abs(y))) or 1.0
    return y * (peak / m)


def tanh_drive(y, k=1.6):
    return np.tanh(y * k) / np.tanh(k)


def save(name, y):
    y = y - np.mean(y)
    peak = float(np.max(np.abs(y)))
    data = (np.clip(y, -1, 1) * 32767).astype("<i2")
    f = OUT / (name + ".wav")
    with wave.open(str(f), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(data.tobytes())
    print(f"{name}: {len(y)/SR:.2f}s peak={peak:.2f}")
    return {"file": str(f), "seconds": round(len(y) / SR, 3)}


SRC = {
    "roars": load(PREV / "479380_breviceps_dragon_roars_60s_CC0.mp3"),
    "snarl_attack": load(PREV / "466830_breviceps_dragon_snarl_roar_attack_3s_CC0.mp3"),
    "growl": load(PREV / "621005_samsterbirdies_deep_scary_growl_9s_CC0.mp3"),
    "rumble": load(PREV / "431527_hgsbsn_monster_rumble_8s_CC0.mp3"),
    "cave_growl": load(PREV / "368255_mburgess1_deep_growl_cave_5s_CC0.mp3"),
    "gut": load(PREV / "695999_samanthacastleberry_stomach_growls_61s_CC0.mp3"),
    "squelch": load(PREV / "635042_sillygrizzlies_blood_gush_squelch_51s_CC0.mp3"),
    "wetmove": load(PREV / "834075_federicoy_wet_slimy_movement_96s_CC0.mp3"),
    "bite": load(PREV / "467701_lucasduff_monster_bite_2s_CC0.mp3"),
    "oga_roar": load(OGA / "monster_roar.wav"),
}
manifest = {}

# --- S_M10_Idle: 3.2 s cavity-resonance loop ----------------------------------
dur = 3.2
gut = pitch(window(SRC["gut"], 3.6, "calm"), 0.85)
gut = highp(lowp(gut[: int((dur + 0.45) * SR)], 600), 25)
gut = loopify(gut, 0.45)
breath = 0.78 + 0.22 * np.sin(2 * np.pi * np.arange(len(gut)) / (dur * SR))
gut *= breath
bed = pitch(SRC["rumble"], 0.8)
bed = loopify(lowp(bed[: int((dur + 0.6) * SR)], 260), 0.6)
y = norm(gut + bed * 0.30, 0.45)
manifest["S_M10_Idle"] = save("S_M10_Idle", y)

# --- S_M10_Crawl: 2.4 s wet eight-pad loop ------------------------------------
dur = 2.4
wet = pitch(window(SRC["wetmove"], 2.7, "steady", offset=8.0), 0.9)
wet = band(wet, 90, 3000)[: int(2.7 * SR)]
wet = loopify(wet, 0.3)
y = norm(wet, 0.5)
manifest["S_M10_Crawl"] = save("S_M10_Crawl", y)

# --- S_M10_Bite: 1.6 s, jaw snap lands at the 0.70 s contact -------------------
dur = 1.6
y = np.zeros(int(dur * SR))
grow = pitch(SRC["snarl_attack"], 0.8)[: int(0.72 * SR)]
grow = fade(grow, 0.10, 0.30)
place(y, grow, 0.0, 0.8)
snap = pitch(SRC["bite"], 0.85)
e = env_rms(snap)
onset = int(np.argmax(np.diff(e)) * 0.05 * SR)
snap = band(snap[onset:onset + int(0.9 * SR)], 120, 6000)
peak_at = int(np.argmax(np.abs(snap[: int(0.5 * SR)])))
place(y, snap, 0.71 - peak_at / SR, 1.0)
wet = window(SRC["squelch"], 0.4, "attack", offset=2.0)
place(y, lowp(wet, 2200), 0.74, 0.45)
y = fade(y, 0.02, 0.35)
manifest["S_M10_Bite"] = save("S_M10_Bite", norm(y, 0.85))

# --- S_M10_Howl: 3.0 s sustained resonant roar (channel voice) ----------------
dur = 3.0
roar = pitch(window(SRC["roars"], 3.4, "loud"), 0.85)
roar = roar[: int(dur * SR)]
roar = tanh_drive(roar, 1.7)
bed = pitch(SRC["rumble"], 0.9)[: int(dur * SR)]
y = roar + lowp(bed, 320) * 0.28
y = fade(y, 0.14, 0.45)
manifest["S_M10_Howl"] = save("S_M10_Howl", norm(y, 0.9))

# --- S_M10_Gas: 7.0 s wet pressurized hiss ------------------------------------
dur = 7.0
t = np.arange(int(dur * SR)) / SR
noise = rng.normal(0, 1, len(t))
hiss = band(noise, 700, 4200) * 0.8 + band(noise, 240, 900) * 0.5
gate = np.clip(t / 0.55, 0, 1) ** 1.4 * np.clip((dur - t) / 0.95, 0, 1) ** 1.2
y = hiss * gate
for at in (0.9, 2.1, 3.4, 4.6, 5.6):
    burst = window(SRC["gut"], 0.5, "attack", offset=float(rng.uniform(0, 40)))
    place(y, lowp(burst, 900), at, 0.35)
y += lowp(pitch(SRC["rumble"], 0.7)[: len(t)], 200) * 0.22
manifest["S_M10_Gas"] = save("S_M10_Gas", norm(y, 0.55))

# --- S_M10_Hit: 0.85 s wet impact ---------------------------------------------
dur = 0.85
y = np.zeros(int(dur * SR))
sq = pitch(window(SRC["squelch"], 0.55, "attack"), 0.9)
sq = band(sq, 150, 4500)[: int(0.5 * SR)]
place(y, sq, 0.02, 1.0)
tt = np.arange(int(0.30 * SR)) / SR
thump = np.sin(2 * np.pi * (54 - 14 * tt) * tt) * np.exp(-tt * 11)
place(y, thump, 0.015, 0.7)
manifest["S_M10_Hit"] = save("S_M10_Hit", norm(y, 0.8))

# --- S_M10_Death: 2.5 s, collapse lands near the 60% physics handoff ----------
dur = 2.5
y = np.zeros(int(dur * SR))
moan = pitch(SRC["growl"], 0.72)[: int(1.5 * SR)]
moan = lowp(moan, 700) * np.clip(1.15 - np.arange(len(moan)) / (1.5 * SR), 0, 1)
place(y, moan, 0.0, 0.8)
splat = pitch(window(SRC["wetmove"], 0.6, "attack", offset=20.0), 0.8)
place(y, band(splat, 90, 3200), 1.42, 1.0)
tt = np.arange(int(0.45 * SR)) / SR
thump = np.sin(2 * np.pi * (46 - 10 * tt) * tt) * np.exp(-tt * 8)
place(y, thump, 1.44, 0.9)
y = fade(y, 0.03, 0.55)
manifest["S_M10_Death"] = save("S_M10_Death", norm(y, 0.85))

# --- S_M10_Threat: 2.4 s attack bark ------------------------------------------
dur = 2.4
roar = pitch(SRC["snarl_attack"], 0.78)
roar = window(roar, dur, "loud")
roar = tanh_drive(roar, 1.5)
y = fade(roar, 0.10, 0.45)
manifest["S_M10_Threat"] = save("S_M10_Threat", norm(y, 0.85))

provenance = {
    "pipeline": "CC0 previews staged in AudioScout -> deterministic slice/pitch/layer in prepare_audio.py -> 44100 Hz mono PCM",
    "note": "freesound.org previews are lossy MP3; swap for the original WAV when a freesound account download is available. OGA monster_roar.wav is final quality.",
    "sources": {
        "479380": {"author": "Breviceps", "license": "CC0", "url": "https://freesound.org/s/479380/", "used_in": ["S_M10_Howl"]},
        "466830": {"author": "Breviceps", "license": "CC0", "url": "https://freesound.org/s/466830/", "used_in": ["S_M10_Bite", "S_M10_Threat"]},
        "621005": {"author": "SamsterBirdies", "license": "CC0", "url": "https://freesound.org/s/621005/", "used_in": ["S_M10_Death"]},
        "431527": {"author": "hgsbsn", "license": "CC0", "url": "https://freesound.org/s/431527/", "used_in": ["S_M10_Idle", "S_M10_Howl", "S_M10_Gas"]},
        "368255": {"author": "mburgess1", "license": "CC0", "url": "https://freesound.org/s/368255/", "used_in": []},
        "695999": {"author": "SamanthaCastleberry", "license": "CC0", "url": "https://freesound.org/s/695999/", "used_in": ["S_M10_Idle", "S_M10_Gas"]},
        "635042": {"author": "sillygrizzlies", "license": "CC0", "url": "https://freesound.org/s/635042/", "used_in": ["S_M10_Bite", "S_M10_Hit"]},
        "834075": {"author": "Federicoy", "license": "CC0", "url": "https://freesound.org/s/834075/", "used_in": ["S_M10_Crawl", "S_M10_Death"]},
        "467701": {"author": "LucasDuff", "license": "CC0", "url": "https://freesound.org/s/467701/", "used_in": ["S_M10_Bite"]},
    },
    "outputs": manifest,
    "tested": False,
}
(ROOT / "Records" / "audio_source.json").write_text(
    json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
print("M10_AUDIO_V1_PREPARED")
