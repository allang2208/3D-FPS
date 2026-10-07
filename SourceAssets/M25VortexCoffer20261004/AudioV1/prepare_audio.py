"""Author the nine S_M25_* creature sounds for the VortexCoffer (thunder coffer).

Organic layers reuse the CC0 freesound previews staged for M-10 in
../../M10ChenXia20261003/AudioScout. All electric layers (electrode crackle,
mains hum, discharge sweeps, lance thunder crack) are synthesized locally with
numpy, so every output stays license-clean. Output: 44100 Hz mono 16-bit PCM.
"""
import json, subprocess, wave
from pathlib import Path
import numpy as np
import imageio_ffmpeg
from scipy.signal import butter, sosfilt, resample_poly

ROOT = Path(__file__).resolve().parent
SCOUT = ROOT.parents[1] / "M10ChenXia20261003" / "AudioScout"
PREV = SCOUT / "Previews"
OGA = SCOUT / "OGA_Packs"
OUT = ROOT / "Wav"; OUT.mkdir(parents=True, exist_ok=True)
(ROOT / "Records").mkdir(exist_ok=True)
SR = 44100
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
rng = np.random.default_rng(2510)


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
    n = int(round(seconds * SR))
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


def tanh_drive(y, k=1.6):
    return np.tanh(y * k) / np.tanh(k)


def fit(y, seconds):
    n = int(round(seconds * SR))
    if len(y) < n:
        y = np.concatenate([y, np.zeros(n - len(y))])
    return y[:n]


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


# --- electric helpers (fully synthesized, no external source) -----------------
def pops(dur, rate0, rate1, lo=2400, hi=9000, amp=1.0):
    """Random electrode pops; density ramps rate0->rate1 per second."""
    n = int(round(dur * SR))
    y = np.zeros(n)
    t = 0.02
    while t < dur - 0.02:
        rate = rate0 + (rate1 - rate0) * (t / dur)
        t += rng.exponential(1.0 / max(1.0, rate))
        w = int(rng.uniform(.004, .022) * SR)
        burst = rng.normal(0, 1, w) * np.exp(-np.arange(w) / (w * .22))
        i = int(t * SR)
        if i + w < n:
            y[i:i + w] += burst * rng.uniform(.5, 1.0)
    return band(y, lo, hi) * amp


def chirp(dur, f0, f1, amp=1.0, shape="exp"):
    t = np.arange(int(round(dur * SR))) / SR
    if shape == "exp":
        phase = 2 * np.pi * f0 * (np.power(f1 / f0, t / dur) - 1) / np.log(f1 / f0)
    else:
        phase = 2 * np.pi * (f0 * t + (f1 - f0) * t * t / (2 * dur))
    return np.sin(phase) * amp


def mains(dur, f0=110.0, wob=0.04, partials=(1.0, .5, .22, .1)):
    """Wobbling harmonic hum; the electrode bed under every idle/charge."""
    t = np.arange(int(round(dur * SR))) / SR
    y = np.zeros(len(t))
    for h, a in enumerate(partials):
        f = f0 * (h + 1)
        drift = np.cumsum(1 + wob * np.sin(2 * np.pi * (.31 + h * .13) * t)) / SR
        y += a * np.sin(2 * np.pi * f * drift)
    return y


def thunder_crack(dur):
    """Railgun release: broadband snap, sub thump, short brown rumble decay."""
    n = int(round(dur * SR))
    t = np.arange(n) / SR
    crack = rng.normal(0, 1, n) * np.exp(-t * 26)
    crack = highp(crack, 1400)
    body = np.cumsum(rng.normal(0, 1, n))
    body = lowp(body / np.max(np.abs(body)), 320) * np.exp(-t * 3.2)
    sub = chirp(min(dur, .5), 68, 34, 1.0) * np.exp(-np.arange(int(min(dur, .5) * SR)) / SR / .16)
    y = crack * .9 + body * .8
    y[:len(sub)] += sub * .7
    return fade(y, 0.001, .35)


SCOUT2 = ROOT / "Scout"
SRC = {
    "tesla_bed": load(SCOUT2 / "362975_follytowers_big_tesla_coil_38s_CC0.mp3"),
    "tesla_arc": load(SCOUT2 / "415960_follytowers_high_voltage_discharge_1_CC0.mp3"),
    "thunder": load(SCOUT2 / "347853_cognitoperceptu_thunder_crack_CC0.mp3"),
    "thunder_close": load(SCOUT2 / "616992_TRP_thunder_close_toronto_CC0.mp3"),
    "roars": load(PREV / "479380_breviceps_dragon_roars_60s_CC0.mp3"),
    "snarl_attack": load(PREV / "466830_breviceps_dragon_snarl_roar_attack_3s_CC0.mp3"),
    "growl": load(PREV / "621005_samsterbirdies_deep_scary_growl_9s_CC0.mp3"),
    "rumble": load(PREV / "431527_hgsbsn_monster_rumble_8s_CC0.mp3"),
    "gut": load(PREV / "695999_samanthacastleberry_stomach_growls_61s_CC0.mp3"),
    "squelch": load(PREV / "635042_sillygrizzlies_blood_gush_squelch_51s_CC0.mp3"),
    "wetmove": load(PREV / "834075_federicoy_wet_slimy_movement_96s_CC0.mp3"),
    "bite": load(PREV / "467701_lucasduff_monster_bite_2s_CC0.mp3"),
    "oga_roar": load(OGA / "monster_roar.wav"),
}
manifest = {}

# --- S_M25_Idle: 3.6 s resonant maw body + faint electrode hum ----------------
dur = 3.6
gut = pitch(window(SRC["gut"], 4.1, "calm"), 0.8)
gut = fit(highp(lowp(gut[: int(round((dur + 0.5) * SR))], 520), 24), dur + 0.5)
gut = fit(loopify(gut, 0.5), dur)
# V2 realism: muted substation-style buzz from the tesla recording's low band,
# sparse real discharge ticks instead of synthesized pops.
buzz = pitch(window(SRC["tesla_bed"], dur + .5, "calm", offset=4.0), 1.0)
buzz = fit(lowp(band(buzz, 90, 700), 500), dur + .5)
buzz = fit(loopify(buzz, .5), dur) * .30
spark = pitch(window(SRC["tesla_arc"], dur + .5, "calm", offset=20.0), 1.0)
spark = fit(loopify(highp(band(spark, 1500, 9000), 1200), .5), dur) * .35
y = norm(gut * .9 + buzz + spark, .45)
manifest["S_M25_Idle"] = save("S_M25_Idle", y)

# --- S_M25_Crawl: 2.6 s slow tendril drag loop --------------------------------
dur = 2.6
wet = pitch(window(SRC["wetmove"], 3.0, "steady", offset=30.0), 0.8)
wet = fit(band(wet, 70, 2600), 3.0)
wet = fit(loopify(wet, 0.4), dur)
y = wet.copy()
for i, at in enumerate((0.1, 0.75, 1.4, 2.05)):
    tt = np.arange(int(0.22 * SR)) / SR
    pad = np.sin(2 * np.pi * (58 - 12 * tt) * tt) * np.exp(-tt * 16)
    place(y, pad, at + rng.uniform(-.02, .02), .30 + .06 * (i % 2))
fizz = window(SRC["tesla_arc"], dur + .4, "calm", offset=44.0)
fizz = fit(loopify(band(fizz, 2000, 9000), .4), dur) * .22
y = norm(y * .9 + fizz, .5)
manifest["S_M25_Crawl"] = save("S_M25_Crawl", y)

# --- S_M25_Crackle: 4.0 s electrode discharge bed -----------------------------
dur = 4.0
# V2 realism: the bed IS a real tesla-coil discharge stretch (steady sizzle),
# no synthesized zaps. Two sliced accents ride on top for irregularity.
bed = window(SRC["tesla_bed"], dur + .7, "loud", offset=8.0)
bed = fit(loopify(band(bed, 300, 8500), .7), dur)
hum = fit(loopify(mains(dur + .6, 100, wob=.12, partials=(1.0, .45, .18)), .6), dur) * .16
y = bed * .8 + hum
acc1 = window(SRC["tesla_arc"], 0.5, "attack", offset=34.0)
place(y, highp(band(acc1, 900, 11000), 600), 1.15, .5)
acc2 = window(SRC["tesla_arc"], 0.4, "attack", offset=47.0)
place(y, highp(band(acc2, 900, 11000), 600), 2.85, .4)
y = norm(y, .5)
manifest["S_M25_Crackle"] = save("S_M25_Crackle", y)

# --- S_M25_Bite: 0.8 s arcane maw snap, contact ~0.33 s ------------------------
dur = 0.8
y = np.zeros(int(dur * SR))
grow = pitch(SRC["snarl_attack"], 1.0)[: int(0.28 * SR)]
grow = lowp(fade(grow, 0.05, 0.12), 1600)
place(y, grow, 0.0, .3)
snap = pitch(SRC["bite"], 1.05)
e = env_rms(snap)
onset = int(np.argmax(np.diff(e)) * 0.05 * SR)
snap = band(snap[onset:onset + int(0.6 * SR)], 140, 7000)
peak_at = int(np.argmax(np.abs(snap[: int(0.4 * SR)])))
place(y, snap, 0.33 - peak_at / SR, 1.0)
arc = window(SRC["tesla_arc"], 0.16, "attack", offset=36.0)
arc = highp(band(arc, 1200, 12000), 900)
place(y, arc, 0.33, .55)
fizzb = window(SRC["tesla_bed"], 0.3, "loud", offset=28.0)
place(y, band(fizzb, 1800, 9500), 0.36, .35)
wet = window(SRC["squelch"], 0.35, "attack", offset=12.0)
place(y, lowp(wet, 2600), 0.37, .4)
y = fade(y, 0.015, 0.25)
manifest["S_M25_Bite"] = save("S_M25_Bite", norm(y, .85))

# --- S_M25_Charge: 0.6 s sharp current windup ---------------------------------
dur = 0.6
t = np.arange(int(dur * SR)) / SR
ramp = np.clip(t / dur, 0, 1) ** 1.4
# V3: piercing high-voltage current, not a swoop — a thin rising whine over
# swelling corona hiss, tight and needle-like.
whine = chirp(dur, 1500, 5400, .15, "exp") * (.30 + ramp)
whine += chirp(dur, 3050, 7900, .05, "exp") * ramp
corona = window(SRC["tesla_arc"], dur + .1, "attack", offset=36.0)[: int(dur * SR)]
corona = fit(band(corona, 3200, 12000), dur) * (.12 + ramp)
tension = np.sin(2 * np.pi * 62 * t) * ramp * .10
y = fade(whine + corona + tension, .008, .05)
manifest["S_M25_Charge"] = save("S_M25_Charge", norm(y, .75))

# --- S_M25_LanceCharge: 1.7 s railgun charge-up --------------------------------
dur = 1.7
t = np.arange(int(dur * SR)) / SR
ramp = np.clip(t / dur, 0, 1) ** 1.5
hum = mains(dur, 55, wob=.06, partials=(1.0, .55, .3, .15)) * ramp * .45
fizz = window(SRC["tesla_bed"], dur + .3, "loud", offset=24.0)[: int(dur * SR)]
fizz = fit(band(fizz, 900, 9000), dur) * (.20 + ramp) * .8
sub = np.sin(2 * np.pi * 42 * t) * ramp * .3
whine = chirp(dur, 200, 950, .10, "exp") * ramp
y = fade(hum + fizz + sub + whine, .05, .10)
manifest["S_M25_LanceCharge"] = save("S_M25_LanceCharge", norm(y, .8))

# --- S_M25_LanceRelease: 1.8 s railgun thunder crack ---------------------------
# V2 realism: a genuine thunder crack (peak ~1.35 s into the source) preceded by
# a short tesla snap so the transient reads "electric", not weather.
dur = 1.8
boom = window(SRC["thunder"], 2.2, "attack", offset=0.9)
boom = fit(boom, dur + .4)[: int(dur * SR)]
snap = window(SRC["tesla_arc"], 0.35, "attack", offset=35.0)
snap = highp(band(snap, 1500, 12000), 1000)
y = np.zeros(int(dur * SR))
place(y, snap, 0.0, .7)
place(y, boom, 0.06, 1.0)
sub = chirp(min(dur, .45), 72, 36, 1.0) * np.exp(-np.arange(int(min(dur, .45) * SR)) / SR / .14)
place(y, sub, 0.02, .6)
manifest["S_M25_LanceRelease"] = save("S_M25_LanceRelease", norm(y, .9))

# --- S_M25_Hit: 0.75 s wet impact + spark --------------------------------------
dur = 0.75
y = np.zeros(int(dur * SR))
sq = pitch(window(SRC["squelch"], 0.5, "attack", offset=30.0), 0.95)
sq = band(sq, 160, 4200)[: int(0.45 * SR)]
place(y, sq, 0.02, 1.0)
tt = np.arange(int(0.28 * SR)) / SR
thump = np.sin(2 * np.pi * (56 - 12 * tt) * tt) * np.exp(-tt * 12)
place(y, thump, 0.015, .7)
fizz = window(SRC["tesla_arc"], 0.22, "attack", offset=36.4)
place(y, highp(band(fizz, 1800, 11000), 1200), 0.03, .5)
manifest["S_M25_Hit"] = save("S_M25_Hit", norm(y, .8))

# --- S_M25_Death: 3.0 s moan, collapse at ~1.35 s, electrodes die ~2.0 s -------
dur = 3.0
y = np.zeros(int(dur * SR))
moan = pitch(SRC["growl"], 0.66)[: int(1.6 * SR)]
moan = lowp(moan, 620) * np.clip(1.2 - np.arange(len(moan)) / (1.6 * SR), 0, 1)
place(y, moan, 0.0, .8)
splat = pitch(window(SRC["wetmove"], 0.6, "attack", offset=45.0), 0.8)
place(y, band(splat, 90, 3000), 1.35, 1.0)
tt = np.arange(int(0.4 * SR)) / SR
thump = np.sin(2 * np.pi * (48 - 10 * tt) * tt) * np.exp(-tt * 9)
place(y, thump, 1.37, .85)
dying = pitch(window(SRC["tesla_arc"], 1.0, "loud", offset=35.0), 0.75)
dying = dying[: int(.9 * SR)] * np.exp(-np.arange(int(.9 * SR)) / SR * 2.0)
place(y, band(dying, 400, 8000), 1.65, .6)
dying2 = pitch(window(SRC["tesla_bed"], .8, "calm", offset=30.0), 0.6)
dying2 = dying2 * np.exp(-np.arange(len(dying2)) / SR * 1.6)
place(y, lowp(dying2, 3000), 1.75, .35)
y = fade(y, 0.03, 0.7)
manifest["S_M25_Death"] = save("S_M25_Death", norm(y, .85))

provenance = {
    "pipeline": "CC0 previews staged in M10 AudioScout + AudioV1/Scout -> deterministic slice/pitch/layer in prepare_audio.py -> 44100 Hz mono PCM",
    "note": "V2 realism pass (2026-10-07): synthesized zap chirps and pops replaced by recorded CC0 tesla-coil discharges and real thunder. Organic layers reuse the same freesound CC0 previews as M-10 V1; swap for original WAVs when a freesound account download is available.",
    "sources": {
        "362975": {"author": "follytowers", "license": "CC0", "url": "https://freesound.org/s/362975/", "used_in": ["S_M25_Idle", "S_M25_Crawl", "S_M25_Crackle", "S_M25_Bite", "S_M25_LanceCharge", "S_M25_Death"]},
        "415960": {"author": "follytowers", "license": "CC0", "url": "https://freesound.org/s/415960/", "used_in": ["S_M25_Idle", "S_M25_Crawl", "S_M25_Crackle", "S_M25_Bite", "S_M25_Charge", "S_M25_Hit", "S_M25_LanceRelease", "S_M25_Death"]},
        "347853": {"author": "cognito perceptu", "license": "CC0", "url": "https://freesound.org/s/347853/", "used_in": ["S_M25_LanceRelease"]},
        "479380": {"author": "Breviceps", "license": "CC0", "url": "https://freesound.org/s/479380/", "used_in": []},
        "466830": {"author": "Breviceps", "license": "CC0", "url": "https://freesound.org/s/466830/", "used_in": ["S_M25_Bite"]},
        "621005": {"author": "SamsterBirdies", "license": "CC0", "url": "https://freesound.org/s/621005/", "used_in": ["S_M25_Death"]},
        "431527": {"author": "hgsbsn", "license": "CC0", "url": "https://freesound.org/s/431527/", "used_in": []},
        "695999": {"author": "SamanthaCastleberry", "license": "CC0", "url": "https://freesound.org/s/695999/", "used_in": ["S_M25_Idle"]},
        "635042": {"author": "sillygrizzlies", "license": "CC0", "url": "https://freesound.org/s/635042/", "used_in": ["S_M25_Bite", "S_M25_Hit"]},
        "834075": {"author": "Federicoy", "license": "CC0", "url": "https://freesound.org/s/834075/", "used_in": ["S_M25_Crawl", "S_M25_Death"]},
        "467701": {"author": "LucasDuff", "license": "CC0", "url": "https://freesound.org/s/467701/", "used_in": ["S_M25_Bite"]},
    },
    "outputs": manifest,
    "tested": False,
}
(ROOT / "Records" / "audio_source.json").write_text(
    json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
print("M25_AUDIO_V1_PREPARED")
