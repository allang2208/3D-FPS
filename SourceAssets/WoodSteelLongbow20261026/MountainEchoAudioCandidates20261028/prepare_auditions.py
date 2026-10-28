"""Download public sound previews and prepare three unlayered auditions."""
import concurrent.futures
import hashlib
import json
import math
import urllib.request
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parent
SOURCES = ROOT / 'Sources'
OUT = ROOT / 'Auditions'
OUT.mkdir(exist_ok=True)
CANDIDATES = [
    {'id': 'A', 'name': 'MagicSmite', 'title': 'Magic Smite', 'author': 'spookymodem',
     'page': 'https://opengameart.org/content/magic-smite', 'license': 'CC-BY-3.0',
     'license_url': 'https://creativecommons.org/licenses/by/3.0/',
     'audio_url': 'https://opengameart.org/sites/default/files/Magic%20Smite.wav', 'ext': '.wav'},
    {'id': 'B', 'name': 'LaserMagicImpacts', 'title': 'Laser/Magic Spell Impacts', 'author': 'TannerSound',
     'page': 'https://freesound.org/people/TannerSound/sounds/842627/', 'license': 'CC-BY-4.0',
     'license_url': 'https://creativecommons.org/licenses/by/4.0/',
     'audio_url': 'https://cdn.freesound.org/previews/842/842627_4369435-hq.mp3', 'ext': '.mp3'},
    {'id': 'C', 'name': 'MagicalHit', 'title': 'Magical Hit', 'author': 'SailorErick',
     'page': 'https://freesound.org/people/SailorErick/sounds/430769/', 'license': 'CC0-1.0',
     'license_url': 'https://creativecommons.org/publicdomain/zero/1.0/',
     'audio_url': 'https://cdn.freesound.org/previews/430/430769_8617758-hq.mp3', 'ext': '.mp3'},
]

def prepare(source):
    entry = dict(source)
    raw = SOURCES / (source['name'] + source['ext'])
    if not raw.exists():
        req = urllib.request.Request(source['audio_url'], headers={'User-Agent': 'Mozilla/5.0'})
        raw.write_bytes(urllib.request.urlopen(req, timeout=40).read())
    audio, rate = sf.read(raw, dtype='float64', always_2d=True)
    source_seconds = len(audio) / rate
    divisor = math.gcd(rate, 48000)
    audio = resample_poly(audio, 48000 // divisor, rate // divisor)
    peak = float(np.abs(audio).max())
    if peak <= 0:
        raise RuntimeError('Empty sound: ' + source['name'])
    gain = 10 ** (-3 / 20) / peak
    audio *= gain
    # Preserve the full source event and its pitch, timing and stereo image.
    output = OUT / (source['id'] + '_' + source['name'] + '.wav')
    sf.write(output, audio, 48000, subtype='PCM_16')
    entry.update(source_file=str(raw), source_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),
                 audition_file=str(output), seconds=round(source_seconds, 3), sample_rate=48000,
                 gain_db=round(20 * math.log10(gain), 3), selected=False, imported_to_ue=False,
                 processing='Full event, unchanged pitch/speed; 48 kHz PCM16, -3 dBFS peak. Peak matching is not perceptual loudness matching.')
    return entry

results = []
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    jobs = {pool.submit(prepare, item): item for item in CANDIDATES}
    for job in concurrent.futures.as_completed(jobs):
        try:
            entry = job.result()
            results.append(entry)
            print(json.dumps({'id': entry['id'], 'seconds': entry['seconds'], 'file': entry['audition_file']}))
        except Exception as exc:
            print(json.dumps({'id': jobs[job]['id'], 'error': str(exc)}))
results.sort(key=lambda x: x['id'])
(ROOT / 'manifest.json').write_text(json.dumps({'date': '2026-10-28', 'runtime_modified': False,
    'purpose': 'Three candidate light-arrow impact sounds for user audition', 'candidates': results}, indent=2), encoding='utf-8')
credits = ['Light-arrow impact audition candidates, 2026-10-28', 'No game integration. Full source events, resampled and peak-matched only.', '']
for entry in results:
    credits.extend([entry['id'] + ': ' + entry['title'] + ' by ' + entry['author'], entry['page'],
                    entry['license'] + ' ' + entry['license_url'], entry['processing'], ''])
(ROOT / 'CREDITS.txt').write_text('\n'.join(credits), encoding='utf-8')
if len(results) != 3:
    raise SystemExit('Some candidates unavailable; see output and manifest.')
