"""Edit the CC0 Freesound recording into dry, unpitched M16 action cues.

Requires numpy, scipy, soundfile. Original public HQ preview is retained in assets.
"""
from pathlib import Path
import json
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'assets/sfx/m16/mechanics'
SOURCE = ROOT / 'assets/sfx/m16/source/263513_4675419-hq.mp3'
# Seconds in wadaltmon's recording; independently placed at animation contacts.
REGIONS = {
    'mag_out': (.205, .500, .36),
    'mag_insert': (1.020, 1.200, .30),
    'mag_seat': (1.525, 1.785, .50),
    'charge_pull': (3.430, 3.615, .42),
    'charge_release': (3.620, 3.910, .50),
    'bolt_release': (4.225, 4.485, .46),
}

def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    samples, rate = sf.read(SOURCE, always_2d=True)
    mono = samples.mean(axis=1)
    filtered = sosfilt(butter(2, [80, 12000], fs=rate, btype='bandpass', output='sos'), mono)
    report = {'source': str(SOURCE.relative_to(ROOT)), 'rate': rate, 'cues': {}}
    for name, (start, end, peak) in REGIONS.items():
        cue = filtered[round(start * rate):round(end * rate)].copy()
        cue[:round(.002 * rate)] *= np.linspace(0, 1, round(.002 * rate))
        cue[-round(.015 * rate):] *= np.linspace(1, 0, round(.015 * rate))
        cue *= peak / np.max(np.abs(cue))
        sf.write(OUTPUT / f'{name}.wav', cue, rate, subtype='PCM_16')
        report['cues'][name] = {'source_seconds': [start, end], 'duration': len(cue)/rate,
                               'peak_dbfs': float(20*np.log10(np.max(np.abs(cue))))}
    (OUTPUT / 'edit-report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf8')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
