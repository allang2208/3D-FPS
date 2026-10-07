"""Author the six S_M08_* creature sounds for the Lurker (surface ambusher).

The lurker is a low-slung wet-flesh quadruped with a dorsal bore ring. Flesh
layers reuse the CC0 freesound previews staged for M-10 in
../../../M10ChenXia20261003/AudioScout; bore-membrane flutter, cartilage
creaks and air whooshes are synthesized locally with numpy, so all outputs
stay license-clean. Air-cannon charge/release already ship as V06/V11 assets
and are not re-authored here. Output: 48000 Hz mono 16-bit PCM.
"""
import json, subprocess, wave
from pathlib import Path
import numpy as np
import imageio_ffmpeg
from scipy.signal import butter, sosfilt, resample_poly

ROOT = Path(__file__).resolve().parent
SCOUT = ROOT.parents[2] / "M10ChenXia20261003" / "AudioScout"
PREV = SCOUT / "Previews"
OUT = ROOT / "Audio"; OUT.mkdir(parents=True, exist_ok=True)
(ROOT / "Records").mkdir(exist_ok=True)
SR = 48000
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
rng = np.random.default_rng(1408)


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
    n = int(round(xf * SR))
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


def fit(y, seconds):
    n = int(round(seconds * SR))
    if len(y) < n:
        y = np.concatenate([y, np.zeros(n - len(y))])
    return y[:n]


def noise(dur):
    return rng.normal(0, 1, int(round(dur * SR)))


def chirp(dur, f0, f1, amp=1.0):
    t = np.arange(int(round(dur * SR))) / SR
    phase = 2 * np.pi * (f0 * t + (f1 - f0) * t * t / (2 * dur))
    return np.sin(phase) * amp


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


# --- lurker helpers (fully synthesized, no external source) -------------------
def membrane(dur, rate, depth=.8, f0=55, amp=1.0):
    """Dorsal bore-membrane flutter: slow AM tremor on a low organ tone."""
    t = np.arange(int(round(dur * SR))) / SR
    am = (1 - depth) + depth * np.abs(np.sin(np.pi * rate * t)) ** 1.4
    tone = np.sin(2 * np.pi * f0 * t) + .45 * np.sin(2 * np.pi * f0 * 1.53 * t)
    return tone * am * amp


def creak(dur, f0, f1, amp=1.0):
    """Wet cartilage creak: strained chirp plus rubbing noise."""
    t = np.arange(int(round(dur * SR))) / SR
    env = np.exp(-((t - dur * .55) / (dur * .42)) ** 2)
    rub = lowp(band(noise(dur), 110, 900), 900)
    return (lowp(chirp(dur, f0, f1, .5), 800) + rub * .4) * env * amp


def padstep(dur, f0=420, gain=1.0):
    """Soft wet pad contact: short squish noise + low thud."""
    n = int(round(dur * SR))
    t = np.arange(n) / SR
    squish = band(noise(dur), f0 * .6, f0 * 3.2) * np.exp(-t * 26)
    thud = np.sin(2 * np.pi * (95 - 30 * t) * np.clip(t, 0, .2)) * np.exp(-t * 30) * .5
    return (squish + thud) * gain


SRC = {
    "growl": load(PREV / "621005_samsterbirdies_deep_scary_growl_9s_CC0.mp3"),
    "gut": load(PREV / "695999_samanthacastleberry_stomach_growls_61s_CC0.mp3"),
    "squelch": load(PREV / "635042_sillygrizzlies_blood_gush_squelch_51s_CC0.mp3"),
    "wetmove": load(PREV / "834075_federicoy_wet_slimy_movement_96s_CC0.mp3"),
    "bite": load(PREV / "467701_lucasduff_monster_bite_2s_CC0.mp3"),
    "snarl": load(PREV / "466830_breviceps_dragon_snarl_roar_attack_3s_CC0.mp3"),
    "rumble": load(PREV / "431527_hgsbsn_monster_rumble_8s_CC0.mp3"),
}
manifest = {}

# --- S_M08_Idle: 3.0 s low-crouch breath loop, bore membrane shimmer -----------
dur = 3.0
gut = pitch(window(SRC["gut"], 3.6, "calm"), 0.62)
gut = fit(highp(lowp(gut[: int(round((dur + 0.6) * SR))], 380), 24), dur + 0.6)
flesh = fit(loopify(gut, 0.6), dur)
bore = fit(loopify(membrane(dur + 0.5, 9.0, .55, 48, .4), 0.5), dur)
breath = lowp(band(noise(dur + .5), 200, 900), 900)
breath_env = np.clip(np.sin(np.pi * np.arange(len(breath)) / len(breath)) * 1.4, 0, 1)
y = flesh * .8 + bore + fit(loopify(breath * breath_env * .16, .5), dur)
place(y, creak(.45, 150, 95, .5), .9, .22)
place(y, creak(.38, 190, 120, .4), 2.2, .18)
manifest["S_M08_Idle"] = save("S_M08_Idle", norm(fade(y, .01, .01), .36))

# --- S_M08_Crawl: 2.4 s loop — wet pads + low body drag on surfaces ------------
dur = 2.4
wet = pitch(window(SRC["wetmove"], 2.8, "steady", offset=14.0), 0.66)
wet = fit(band(wet, 70, 1900), 2.8)
y = fit(loopify(wet, 0.4), dur)
for i, at in enumerate((0.02, 0.32, 0.62, 0.92, 1.22, 1.52, 1.82, 2.12)):
    y = place(y, padstep(.11, f0=380 + 60 * (i % 3), gain=.5),
              at + rng.uniform(-.012, .012), .55 + .08 * (i % 2))
drag = lowp(np.cumsum(noise(dur + .4)), 260)
drag = drag / np.max(np.abs(drag))
y = y + fit(loopify(drag * .12, .4), dur)
manifest["S_M08_Crawl"] = save("S_M08_Crawl", norm(y, .5))

# --- S_M08_Bite: 0.95 s — alert hunch, lunge snarl, jaw snap ~0.48 s -----------
dur = 0.95
y = np.zeros(int(dur * SR))
hunch = creak(.3, 170, 230, .5)
place(y, hunch, 0.0, .5)
lunge = pitch(SRC["snarl"], 1.15)[: int(0.55 * SR)]
lunge = lowp(fade(lunge, 0.08, 0.12), 1700)
place(y, lunge, 0.10, .5)
snap = pitch(SRC["bite"], 1.1)
e = env_rms(snap)
onset = int(np.argmax(np.diff(e)) * 0.05 * SR)
snap = band(snap[onset:onset + int(0.5 * SR)], 140, 7500)
peak_at = int(np.argmax(np.abs(snap[: int(0.35 * SR)])))
place(y, snap, 0.48 - peak_at / SR, 1.0)
wet = window(SRC["squelch"], 0.35, "attack", offset=24.0)
place(y, lowp(wet, 2600), 0.50, .5)
manifest["S_M08_Bite"] = save("S_M08_Bite", norm(fade(y, .005, .25), .85))

# --- S_M08_Pounce: 1.3 s — crouch strain, 0.28 s launch whoosh, land ~0.95 -----
dur = 1.3
t = np.arange(int(dur * SR)) / SR
y = np.zeros(int(dur * SR))
strain = creak(.30, 120, 260, .7) * np.clip(t[: int(.30 * SR)] / .3, .15, 1)
place(y, strain, 0.0, .7)
growl = pitch(SRC["growl"], 0.9)[: int(0.35 * SR)]
place(y, lowp(growl, 1200) * np.clip(np.arange(len(growl)) / (.35 * SR), 0, 1), .02, .3)
whoosh = band(noise(.55), 250, 3400)
env = np.exp(-((np.arange(len(whoosh)) / SR - .22) / .2) ** 2)
place(y, whoosh * env, 0.28, .8)
flight = lowp(chirp(.4, 300, 520, .4), 1400)
place(y, flight * np.exp(-np.arange(len(flight)) / SR * 4), .3, .4)
tt = np.arange(int(.35 * SR)) / SR
thud = np.sin(2 * np.pi * (60 - 14 * tt) * tt) * np.exp(-tt * 10)
slam = pitch(window(SRC["wetmove"], .35, "attack", offset=48.0), 0.7)
place(y, band(slam, 70, 2400), 0.95, .85)
place(y, thud, 0.96, .8)
place(y, creak(.3, 200, 110, .5), 1.0, .35)
manifest["S_M08_Pounce"] = save("S_M08_Pounce", norm(fade(y, .01, .3), .85))

# --- S_M08_Hit: 0.65 s — wet slap + membrane flap + grunt -----------------------
dur = 0.65
y = np.zeros(int(dur * SR))
sq = pitch(window(SRC["squelch"], 0.4, "attack", offset=44.0), 0.95)
place(y, band(sq, 160, 5000)[: int(0.35 * SR)], 0.01, 1.0)
tt = np.arange(int(.2 * SR)) / SR
thump = np.sin(2 * np.pi * (72 - 16 * tt) * tt) * np.exp(-tt * 13)
place(y, thump, 0.012, .7)
flap = membrane(.18, 34.0, .9, 90, .6)
place(y, band(flap, 80, 2200), .02, .5)
grunt = pitch(SRC["growl"], 1.25)[: int(0.3 * SR)]
place(y, lowp(grunt, 1500) * np.exp(-np.arange(len(grunt)) / SR * 8), .05, .3)
manifest["S_M08_Hit"] = save("S_M08_Hit", norm(y, .8))

# --- S_M08_Death: 1.9 s — sinking groan, membrane sag, side-fall ~0.85 s -------
dur = 1.9
t = np.arange(int(dur * SR)) / SR
y = np.zeros(int(dur * SR))
moan = pitch(SRC["growl"], 0.55)[: int(0.9 * SR)]
moan = lowp(moan, 480) * np.clip(1.0 - np.arange(len(moan)) / (1.0 * SR), 0, 1)
place(y, moan, 0.0, .85)
sag = membrane(.6, 5.0, .9, 42, .5)
place(y, fit(sag, .6) * np.exp(-np.arange(int(.6 * SR)) / SR * 3), .3, .5)
slump = pitch(window(SRC["wetmove"], .7, "steady", offset=64.0), 0.6)
place(y, band(slump, 60, 2000), .55, .8)
tt = np.arange(int(.5 * SR)) / SR
thud = np.sin(2 * np.pi * (50 - 11 * tt) * tt) * np.exp(-tt * 8)
splat = pitch(window(SRC["squelch"], .45, "attack", offset=38.0), 0.7)
place(y, band(splat, 80, 2400), .85, .9)
place(y, thud, .86, .85)
place(y, creak(.5, 140, 70, .6), 1.05, .4)
settle = lowp(band(noise(.5), 90, 700), 700) * np.exp(-np.arange(int(.5 * SR)) / SR * 5)
place(y, settle, 1.15, .3)
manifest["S_M08_Death"] = save("S_M08_Death", norm(fade(y, .02, .8), .85))

# --- validation ---------------------------------------------------------------
for name in ("S_M08_Idle", "S_M08_Crawl"):
    path = OUT / (name + ".wav")
    with wave.open(str(path), "rb") as w:
        n = w.getnframes()
        y = np.frombuffer(w.readframes(n), dtype="<i2").astype(np.float64) / 32767
    step = np.max(np.abs(np.diff(y)))
    print(f"{name} wrap={abs(y[0]-y[-1]):.5f} maxstep={step:.5f}")

# Bite peak position relative to the contact window.
with wave.open(str(OUT / "S_M08_Bite.wav"), "rb") as w:
    y = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32767
e = env_rms(y)
print(f"bite rms peak at {np.argmax(e)*.05:.2f}s (want ~0.48)")

provenance = {
    "pipeline": "CC0 previews staged in M10 AudioScout -> deterministic slice/pitch/layer + fully synthesized bore-membrane/cartilage layers in prepare_audio.py -> 48000 Hz mono PCM",
    "note": "Flesh layers reuse the same freesound CC0 previews as M-10/M-14/M-25 V1; swap for original WAVs when a freesound account download is available. Membrane flutter, cartilage creaks, pad steps and whooshes are pure synthesis. Air-cannon charge/release stay on the existing V06/V11 assets.",
    "sources": {
        "621005": {"author": "SamsterBirdies", "license": "CC0", "url": "https://freesound.org/s/621005/", "used_in": ["S_M08_Pounce", "S_M08_Hit", "S_M08_Death"]},
        "695999": {"author": "SamanthaCastleberry", "license": "CC0", "url": "https://freesound.org/s/695999/", "used_in": ["S_M08_Idle"]},
        "635042": {"author": "sillygrizzlies", "license": "CC0", "url": "https://freesound.org/s/635042/", "used_in": ["S_M08_Bite", "S_M08_Hit", "S_M08_Death"]},
        "834075": {"author": "Federicoy", "license": "CC0", "url": "https://freesound.org/s/834075/", "used_in": ["S_M08_Crawl", "S_M08_Pounce", "S_M08_Death"]},
        "467701": {"author": "LucasDuff", "license": "CC0", "url": "https://freesound.org/s/467701/", "used_in": ["S_M08_Bite"]},
        "466830": {"author": "Breviceps", "license": "CC0", "url": "https://freesound.org/s/466830/", "used_in": ["S_M08_Bite"]},
        "431527": {"author": "hgsbsn", "license": "CC0", "url": "https://freesound.org/s/431527/", "used_in": []},
    },
    "outputs": manifest,
    "tested": False,
}
(ROOT / "Records" / "audio_source.json").write_text(
    json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
print("M08_AUDIO_V01_PREPARED")
