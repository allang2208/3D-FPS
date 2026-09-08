"""Reproducible source cuts; see assets/sfx/rifle-actions-SOURCE.md."""
from pathlib import Path
import json
import argparse
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly

ROOT = Path(__file__).resolve().parents[1]
SFX = ROOT / 'assets/sfx'
REGIONS = {
    'akm_classic': ('akm_classic/source/674742_7157894-hq.mp3', {
        'mag_out': (.193, .37), 'mag_insert': (.85, .987), 'mag_seat': (.995, 1.23)}),
    'infima_ar': ('reload_sharp.mp3', {
        'mag_out': (.016, .095), 'mag_insert': (.149, .32), 'mag_seat': (.824, 1.065)}),
    'hk416': ('hk416/reload.mp3', {
        'mag_out': (.076, .197), 'mag_insert': (.20, .36), 'mag_seat': (.592, .717),
        'bolt_release': (.792, 1.066)}),
    'qbz191': ('qbz191/source/assaultriflereload1.wav', {
        'mag_out': (.23, .37), 'mag_insert': (1.027, 1.176), 'mag_seat': (1.19, 1.39)}),
}

def write_cut(source, target, start, end, peak=.48, low=80, fade_in=.002):
    samples, rate = sf.read(SFX/source, always_2d=True)
    mono = samples.mean(axis=1)
    mono = sosfilt(butter(2, [low, 12000], fs=rate, btype='bandpass', output='sos'), mono)
    cue = mono[round(start*rate):round(end*rate)].copy()
    cue[:round(fade_in*rate)] *= np.linspace(0, 1, round(fade_in*rate))
    cue[-round(.018*rate):] *= np.linspace(1, 0, round(.018*rate))
    cue *= peak / max(np.max(np.abs(cue)), 1e-9)
    if rate != 44100:
        from math import gcd
        g=gcd(rate,44100); cue=resample_poly(cue,44100//g,rate//g); rate=44100
    target=SFX/target; target.parent.mkdir(parents=True, exist_ok=True)
    sf.write(target,cue,rate,subtype='PCM_16')
    return {'source':source,'seconds':[start,end], 'duration':len(cue)/rate,
            'peak_dbfs':float(20*np.log10(np.max(abs(cue))))}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--weapons', nargs='+', choices=REGIONS, default=list(REGIONS))
    args=parser.parse_args()
    missing=[REGIONS[w][0] for w in args.weapons if not (SFX/REGIONS[w][0]).is_file()]
    if missing: parser.error('Source files missing: '+', '.join(missing))
    report={}
    for weapon in args.weapons:
        source,cues=REGIONS[weapon]
        for cue,(a,b) in cues.items():
            path=f'{weapon}/mechanics/{cue}.wav'
            report[path]=write_cut(source,path,a,b)
    (SFX/'rifle-actions-edit-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print('Prepared',len(report),'PCM clips')

if __name__=='__main__': main()
