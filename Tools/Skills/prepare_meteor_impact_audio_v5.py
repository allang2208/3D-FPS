"""Derive one bounded impact mix from the user's meteor recording; no audition."""
import hashlib
import json
import wave
from pathlib import Path
import numpy as np
from scipy.signal import butter, sosfilt, resample_poly

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "SourceAssets/FireMagic20260921/S_MeteorLand.wav"
OUT = ROOT / "SourceAssets/MeteorImpactWeightV5_20261022"
OUT.mkdir(parents=True, exist_ok=True)
with wave.open(str(SOURCE), "rb") as f:
    sr, channels = f.getframerate(), f.getnchannels()
    if f.getsampwidth() != 2:
        raise RuntimeError("Expected original PCM16 meteor source")
    source = np.frombuffer(f.readframes(f.getnframes()), dtype="<i2").astype(np.float64)/32768
source = source.reshape(-1, channels).mean(axis=1)
if sr != 48000:
    source = resample_poly(source, 48000, sr)
sr = 48000
onset = np.flatnonzero(np.abs(source) > max(1e-5, np.max(np.abs(source))*.045))
trim = min(int(onset[0]) if len(onset) else 0, int(.25*sr))
source = source[trim:]
source /= max(.01, np.max(np.abs(source)))
t = np.arange(round(1.65*sr))/sr
rng = np.random.default_rng(20261022)

def fit(x):
    y = np.zeros_like(t)
    y[:min(len(y),len(x))] = x[:len(y)]
    return y

def band(x, lo, hi):
    return sosfilt(butter(3, [lo,hi], btype="bandpass", fs=sr, output="sos"), x)

dry = band(fit(source), 100, 6500)
body = band(fit(resample_poly(source, 5, 4)), 45, 230)
noise = rng.normal(size=len(t))
air = band(noise, 110, 1300)
crunch = band(noise, 700, 4200)
# The dry contact leads; the low body arrives beneath the fracture at 30 ms.
mix = .72*dry*np.exp(-t*.65)
mix += .32*body*(1-np.exp(-t*100))*np.exp(-t*5)
age = np.maximum(t-.025, 0)
phase = 2*np.pi*(51*age+1.5*(1-np.exp(-age*22)))
mix += (t>=.025)*(.20*np.sin(phase)*np.exp(-age*13)+.24*air*np.exp(-age*18))
# Restrained, dry debris ticks belong to the same single spatial sound voice.
for start,gain in ((.12,.065),(.24,.045),(.39,.025),(.58,.014)):
    age = np.maximum(t-start,0)
    mix += (t>=start)*gain*crunch*(1-np.exp(-age*700))*np.exp(-age*65)
mix = sosfilt(butter(2, 32, btype="highpass", fs=sr, output="sos"), mix)
mix *= np.minimum(t/.0015,1)*np.clip((1.65-t)/.12,0,1)
mix = np.tanh(mix*1.15)
mix *= .76/max(1e-8,np.max(np.abs(mix)))
path = OUT / "S_MeteorImpact.wav"
with wave.open(str(path),"wb") as f:
    f.setparams((1,2,sr,len(mix),"NONE","not compressed"))
    f.writeframes((mix*32767).astype("<i2").tobytes())
record = dict(source=str(SOURCE), source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
              output=str(path), sample_rate=sr, channels=1, duration=1.65, peak_limit=.76,
              trimmed_leading_seconds=trim/sr, provenance="User project meteor recording plus original synthesized low impact and dry debris",
              auditioned=False, runtime_tested=False)
(OUT/"audio-source.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
print("METEOR_IMPACT_AUDIO_PREPARED "+str(path))
