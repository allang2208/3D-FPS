"""Author the seven S_M07_* creature sounds for the Blind Supplicant.

The supplicant is a 3.1 m kneeling sensory experiment: whispered litany,
robe shuffle, gill-membrane cloth. Flesh layers reuse the CC0 freesound
previews staged for M-10 in ../M10ChenXia20261003/AudioScout; chant,
cloth, magic shimmer and gill flutter are synthesized locally with numpy,
so all outputs stay license-clean. Spell impact sounds stay on the
existing player-skill assets; the wall-listen mimic voice stays as is.
Output: 48000 Hz mono 16-bit PCM.
"""
import json, subprocess, wave
from pathlib import Path
import numpy as np
import imageio_ffmpeg
from scipy.signal import butter, sosfilt, resample_poly

ROOT = Path(__file__).resolve().parent
SCOUT = ROOT.parents[1] / "M10ChenXia20261003" / "AudioScout"
PREV = SCOUT / "Previews"
OUT = ROOT / "Audio"; OUT.mkdir(parents=True, exist_ok=True)
(ROOT / "Records").mkdir(exist_ok=True)
SR = 48000
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
rng = np.random.default_rng(1407)


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


def loopfit(y, dur, xf=0.5):
    """Compose an overlong buffer, then fold the overhang into a seamless loop."""
    return loopify(fit(y, dur + xf), xf)


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


# --- supplicant helpers (fully synthesized, no external source) ---------------
def chant(dur, syllables, f0=210, spread=.09, amp=1.0):
    """Whispered litany: two detuned formant bands gated by syllable bursts."""
    n = int(round(dur * SR))
    t = np.arange(n) / SR
    vox = band(noise(dur), 420, 1400) + band(noise(dur), 1600, 3600) * .4
    env = np.zeros(n)
    cursor = 0.0
    for _ in range(syllables):
        cursor += rng.exponential(dur / syllables) * .8
        if cursor >= dur:
            break
        sl = int(rng.uniform(.10, .24) * SR)
        i = int(cursor * SR)
        if i + sl < n:
            shape = np.sin(np.pi * np.arange(sl) / sl) ** 1.6
            drift = 1 + rng.uniform(-spread, spread)
            env[i:i + sl] += shape * drift
    env = np.clip(env, 0, 1.3)
    hum = np.sin(2 * np.pi * f0 * t + .3 * np.sin(2 * np.pi * 2.1 * t)) * env * .12
    return (vox * env * .55 + hum) * amp


def robe(dur, rate=3.2, amp=1.0):
    """Cloth drag/rustle bed: mid-band noise with stride-rate AM."""
    n = int(round(dur * SR))
    t = np.arange(n) / SR
    cloth = band(noise(dur), 500, 5200)
    am = .35 + .65 * np.abs(np.sin(np.pi * rate * t)) ** 1.3
    return cloth * am * amp


def shimmer(dur, f0, f1, amp=1.0):
    """Magic charge sheen: slow rising sine cluster plus air hiss."""
    n = int(round(dur * SR))
    t = np.arange(n) / SR
    s = chirp(dur, f0, f1, .5) + chirp(dur, f0 * 1.5, f1 * 1.52, .25)
    s += chirp(dur, f0 * 2.02, f1 * 2.0, .12)
    hiss = band(noise(dur), 2600, 8200) * .2
    env = np.clip(t / (dur * .8), 0, 1) ** .7
    return (s + hiss) * env * amp


def gill(dur, rate=11.0, f0=64, amp=1.0):
    """Gill-membrane flutter on the robe fringes."""
    t = np.arange(int(round(dur * SR))) / SR
    am = (1 - .7) + .7 * np.abs(np.sin(np.pi * rate * t)) ** 1.5
    return np.sin(2 * np.pi * f0 * t) * am * amp


def thud(dur, f0=52, decay=8.0):
    t = np.arange(int(round(dur * SR))) / SR
    return np.sin(2 * np.pi * (f0 - f0 * .22 * t) * t) * np.exp(-t * decay)


def swipe(dur, f0=350, f1=900, amp=1.0):
    """Claw-limb whoosh: band noise pushed through a rising band envelope."""
    n = int(round(dur * SR))
    t = np.arange(n) / SR
    w = band(noise(dur), f0, f1 * 4)
    env = np.exp(-((t - dur * .55) / (dur * .3)) ** 2)
    return w * env * amp


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

# --- S_M07_Idle: 3.4 s loop — kneeling body rumble + murmured litany -----------
dur = 3.4
gut = pitch(window(SRC["gut"], 4.0, "calm"), 0.55)
flesh = highp(lowp(gut, 340), 22)
litany = chant(dur + 0.5, 8, f0=180, amp=.5)
frill = gill(dur + 0.5, 8.0, 58, .3)
y = loopfit(fit(flesh, dur + .5) * .8 + fit(litany, dur + .5) * .6 + fit(frill, dur + .5), dur)
manifest["S_M07_Idle"] = save("S_M07_Idle", norm(fade(y, .01, .01), .34))

# --- S_M07_Chase: 2.3 s loop — robe drag + bare-foot shuffle + low bulk --------
dur = 2.3
y = fit(robe(dur + .5, rate=2.6, amp=.5), dur + .5)
for i, at in enumerate((0.05, 0.42, 0.79, 1.16, 1.53, 1.9, 2.24)):
    step = lowp(band(noise(.13), 300 + 50 * (i % 3), 1600), 1600)
    step = step * np.exp(-np.arange(len(step)) / SR * 20)
    place(y, step, at + rng.uniform(-.015, .015), .5 + .07 * (i % 2))
    th = thud(.10, f0=70 + 6 * (i % 3), decay=22)
    place(y, th, at + .02, .4)
bulk = pitch(window(SRC["wetmove"], 2.6, "steady", offset=30.0), 0.55)
bulk = fit(lowp(band(bulk, 60, 900), 900), 2.8)
y = loopfit(y + fit(bulk * .5, dur + .5), dur)
manifest["S_M07_Chase"] = save("S_M07_Chase", norm(y, .48))

# --- S_M07_Melee: 0.9 s — claw sweep whoosh -> flesh hit ~0.48 s ----------------
dur = 0.9
t = np.arange(int(dur * SR)) / SR
y = np.zeros(int(dur * SR))
place(y, swipe(.5, 400, 1100, .7), 0.02, .7)
grunt = pitch(SRC["growl"], 1.35)[: int(0.4 * SR)]
place(y, lowp(grunt, 1600) * np.clip(np.arange(len(grunt)) / (.4 * SR), 0, 1), .03, .3)
sq = pitch(window(SRC["squelch"], .35, "attack", offset=30.0), 0.95)
sq = band(sq, 160, 5600)
peak_at = int(np.argmax(np.abs(sq[: int(0.3 * SR)])))
place(y, sq, 0.38 - peak_at / SR, 1.0)
place(y, thud(.25, f0=64, decay=11), 0.385, .75)
manifest["S_M07_Melee"] = save("S_M07_Melee", norm(fade(y, .005, .25), .85))

# --- S_M07_MagicGather: 2.2 s — chant builds with the charge sheen -------------
dur = 2.2
t = np.arange(int(dur * SR)) / SR
y = np.zeros(int(dur * SR))
litany = chant(2.0, 9, f0=200, amp=.7)
litany = litany * np.clip(np.arange(len(litany)) / (1.9 * SR), .2, 1)
place(y, litany, .05, .7)
place(y, shimmer(2.0, 300, 900, .55), .15, .55)
frill = gill(1.8, 13.0, 70, .35) * np.clip(t[: int(1.8 * SR)] / 1.8, .1, 1)
place(y, frill, .2, .35)
manifest["S_M07_MagicGather"] = save("S_M07_MagicGather", norm(fade(y, .02, .35), .7))

# --- S_M07_MagicRelease: 1.0 s — exhale burst at the 0.30 s release ------------
dur = 1.0
t = np.arange(int(dur * SR)) / SR
y = np.zeros(int(dur * SR))
drawn = chant(.30, 3, f0=230, amp=.5)
place(y, drawn, 0.0, .5)
blast = band(noise(.3), 240, 5200) * np.exp(-np.arange(int(.3 * SR)) / SR * 9)
place(y, blast, 0.30, .9)
exhale = band(noise(.5), 500, 3200) * np.exp(-np.arange(int(.5 * SR)) / SR * 6)
place(y, exhale, 0.31, .5)
place(y, chirp(.4, 900, 260, .4) * np.exp(-np.arange(int(.4 * SR)) / SR * 6), .3, .4)
roar = pitch(SRC["snarl"], 0.9)[: int(0.45 * SR)]
place(y, lowp(roar, 1800) * np.exp(-np.arange(len(roar)) / SR * 7), .32, .35)
manifest["S_M07_MagicRelease"] = save("S_M07_MagicRelease", norm(fade(y, .005, .3), .85))

# --- S_M07_Hit: 0.65 s — robe-wrapped impact + gurgle -----------------------------
dur = 0.65
y = np.zeros(int(dur * SR))
sq = pitch(window(SRC["squelch"], 0.4, "attack", offset=10.0), 0.9)
place(y, band(sq, 150, 4500)[: int(0.35 * SR)], 0.01, 1.0)
place(y, thud(.22, f0=58, decay=12), 0.012, .75)
place(y, robe(.2, rate=14.0, amp=.4), .02, .4)
gurgle = pitch(SRC["gut"], 1.2)[: int(0.3 * SR)]
gurgle = lowp(gurgle, 1400) * np.exp(-np.arange(len(gurgle)) / SR * 9)
place(y, gurgle, .06, .3)
manifest["S_M07_Hit"] = save("S_M07_Hit", norm(y, .8))

# --- S_M07_Death: 2.2 s — chant chokes off, bulk sinks, robes fall ~0.9 s ------
dur = 2.2
t = np.arange(int(dur * SR)) / SR
y = np.zeros(int(dur * SR))
choke = chant(0.8, 4, f0=170, amp=.6)
choke = choke * np.clip(1.0 - np.arange(len(choke)) / (0.85 * SR), 0, 1)
place(y, choke, 0.0, .6)
moan = pitch(SRC["growl"], 0.5)[: int(1.1 * SR)]
moan = lowp(moan, 420) * np.clip(1.0 - np.arange(len(moan)) / (1.15 * SR), 0, 1)
place(y, moan, .15, .7)
slump = pitch(window(SRC["wetmove"], .8, "steady", offset=70.0), 0.6)
place(y, band(slump, 60, 1800), .55, .8)
place(y, robe(.5, rate=8.0, amp=.5), .7, .5)
splat = pitch(window(SRC["squelch"], .5, "attack", offset=42.0), 0.7)
place(y, band(splat, 80, 2200), 0.9, .9)
place(y, thud(.5, f0=46, decay=8), 0.91, .85)
frill = gill(.7, 6.0, 50, .4) * np.exp(-np.arange(int(.7 * SR)) / SR * 4)
place(y, frill, 1.1, .4)
manifest["S_M07_Death"] = save("S_M07_Death", norm(fade(y, .02, .9), .85))

# --- validation ---------------------------------------------------------------
for name in ("S_M07_Idle", "S_M07_Chase"):
    with wave.open(str(OUT / (name + ".wav")), "rb") as w:
        y = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32767
    print(f"{name} wrap={abs(y[0]-y[-1]):.5f} maxstep={np.max(np.abs(np.diff(y))):.5f}")

with wave.open(str(OUT / "S_M07_Melee.wav"), "rb") as w:
    y = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32767
e = env_rms(y)
print(f"melee rms peak at {np.argmax(e)*.05:.2f}s (want ~0.38)")

provenance = {
    "pipeline": "CC0 previews staged in M10 AudioScout -> deterministic slice/pitch/layer + fully synthesized chant/robe/shimmer/gill layers in prepare_audio.py -> 48000 Hz mono PCM",
    "note": "Flesh layers reuse the same freesound CC0 previews as the M-08/09/10/14/25 batches. Litany chant, robe rustle, magic shimmer and gill flutter are pure synthesis. Spell impact audio stays on the existing player-skill assets; SW_M07_WallMimic stays on its own timer.",
    "sources": {
        "621005": {"author": "SamsterBirdies", "license": "CC0", "url": "https://freesound.org/s/621005/", "used_in": ["S_M07_Melee", "S_M07_Death"]},
        "695999": {"author": "SamanthaCastleberry", "license": "CC0", "url": "https://freesound.org/s/695999/", "used_in": ["S_M07_Idle", "S_M07_Hit"]},
        "635042": {"author": "sillygrizzlies", "license": "CC0", "url": "https://freesound.org/s/635042/", "used_in": ["S_M07_Melee", "S_M07_Hit", "S_M07_Death"]},
        "834075": {"author": "Federicoy", "license": "CC0", "url": "https://freesound.org/s/834075/", "used_in": ["S_M07_Chase", "S_M07_Death"]},
        "466830": {"author": "Breviceps", "license": "CC0", "url": "https://freesound.org/s/466830/", "used_in": ["S_M07_MagicRelease"]},
    },
    "outputs": manifest,
    "tested": False,
}
(ROOT / "Records" / "audio_source.json").write_text(
    json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
print("M07_AUDIO_V01_PREPARED")
