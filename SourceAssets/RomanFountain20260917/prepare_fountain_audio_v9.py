"""Download CC0 public HQ audition files and author seamless PCM water loops.

The Freesound original WAV downloads require login; these are explicitly the
public HQ MP3 versions, not the original 24-bit recordings. No listening test.
"""
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT/'Saved/FountainPolishV9/python'))
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from math import gcd

ROOT = Path(__file__).with_name('AudioV9')
ROOT.mkdir(exist_ok=True)
SOURCES = [
    dict(id=676173, name='FountainBed', start=0., duration=10., crossfade=1.2, rms_db=-22., highpass=70., lowpass=8500.),
    dict(id=698306, name='FountainDetail', start=10., duration=20., crossfade=2., rms_db=-24., highpass=180., lowpass=11000.),
]


def fetch(url):
    return urlopen(Request(url, headers={'User-Agent':'Mozilla/5.0'}), timeout=45).read()


def author(item):
    page = f"https://freesound.org/people/Nox_Sound/sounds/{item['id']}/"
    html = fetch(page).decode('utf-8')
    if 'creativecommons.org/publicdomain/zero' not in html:
        raise RuntimeError('Expected CC0 license missing on '+page)
    urls = sorted(set(re.findall(r'https://cdn\.freesound\.org/previews/[^\s"<>]+-hq\.mp3', html)))
    if len(urls) != 1:
        raise RuntimeError('Could not identify public HQ preview for '+page)
    source = ROOT/f"{item['id']}_NoxSound_public_HQ.mp3"
    if not source.exists():
        source.write_bytes(fetch(urls[0]))
    (ROOT/f"{item['id']}_source-page.html").write_text(html, encoding='utf-8')
    audio, source_rate = sf.read(source, dtype='float64', always_2d=True)
    # Mono preserves a stable point/extended source under UE spatialization.
    audio = audio.mean(axis=1)
    divisor = gcd(source_rate, 48000)
    audio = resample_poly(audio, 48000//divisor, source_rate//divisor)
    start = round(item['start']*48000)
    audio = audio[start:start+round(item['duration']*48000)]
    audio -= audio.mean()
    overlap = round(item['crossfade']*48000)
    # File begins at input[overlap]; its tail ends at input[overlap-1]. Thus
    # wrapping is a continuation of the original waveform, with no silence gap.
    theta = np.linspace(0., np.pi/2, overlap)
    transition = audio[-overlap:]*np.cos(theta)+audio[:overlap]*np.sin(theta)
    loop = np.concatenate((audio[overlap:-overlap], transition))
    # Periodic spectral filtering avoids introducing filter start/end transients.
    frequencies = np.fft.rfftfreq(len(loop), 1/48000)
    nonzero = np.maximum(frequencies, .001)
    eq = 1/np.sqrt(1+(item['highpass']/nonzero)**4)
    eq *= 1/np.sqrt(1+(frequencies/item['lowpass'])**4)
    eq[0] = 0.
    loop = np.fft.irfft(np.fft.rfft(loop)*eq, n=len(loop))
    gain = min(10**(item['rms_db']/20)/np.sqrt(np.mean(loop*loop)), .82/np.max(np.abs(loop)))
    loop *= gain
    output = ROOT/f"S_{item['name']}_LoopV9.wav"
    sf.write(output, loop, 48000, subtype='PCM_16')
    return dict(**item, source_page=page, download_url=urls[0], author='Nox_Sound',
                license='CC0-1.0', license_url='https://creativecommons.org/publicdomain/zero/1.0/',
                source_version='public HQ MP3, not original WAV', source_sample_rate=source_rate,
                source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                output=output.name, output_seconds=len(loop)/48000,
                output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                sample_rate=48000, channels=1, bits=16, listened=False)


if __name__ == '__main__':
    results = [author(item) for item in SOURCES]
    (ROOT/'sources-and-processing.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(json.dumps([{'output':r['output'], 'seconds':r['output_seconds']} for r in results]))
