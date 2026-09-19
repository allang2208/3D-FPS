"""Locate M4 normal reload contacts in the real mixer before/after speed scaling."""
from pathlib import Path
from datetime import datetime
import json
import re
import subprocess
import sys
import wave
import numpy as np

root = Path(__file__).resolve().parents[2]
run = root / 'Saved/ReloadTiming' / ('ColdSteel_' + sys.argv[1])
ff = root / 'SourceAssets/M4Infima/PreviewTools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
log = (run / 'runtime.log').read_text(encoding='utf-8-sig', errors='replace')
stamp = r'\[(\d{4}\.\d\d\.\d\d-\d\d\.\d\d\.\d\d:\d{3})\]'
def seconds(text):
    return datetime.strptime(text, '%Y.%m.%d-%H.%M.%S:%f').timestamp()
origin = seconds(re.search(stamp + r'.*RELOAD_TIMING_AUDIO_START', log)[1])
with wave.open(str(run / 'mix.wav')) as wav:
    rate, channels = wav.getframerate(), wav.getnchannels()
    pcm = np.frombuffer(wav.readframes(wav.getnframes()), dtype='<i2').reshape(-1, channels).astype(float) / 32768
mono = pcm.mean(axis=1)
events = []
for case, multiplier in ((0, 1.), (1, .8)):
    points = [(float(m[3]), seconds(m[1]) - origin) for m in re.finditer(stamp + rf'.*RELOAD_TIMING_FRAME name=case{case:02d}_\S+ world=([\d.]+) elapsed=([\d.]+)', log) if 'complete' not in m[0]]
    points.sort()
    for name, source in (('mag_out', 29/60), ('mag_insert', 76/60), ('mag_seat', 95/60)):
        expected = float(np.interp(source * multiplier, [p[0] for p in points], [p[1] for p in points]))
        template = np.frombuffer(subprocess.check_output([str(ff), '-v', 'error', '-i', str(root / 'SourceAssets/M4HK416Replica20260910/Audio' / (name + '.wav')), '-ac', '1', '-ar', str(rate), '-f', 'f32le', '-']), dtype='<f4').astype(float)
        lo, hi = max(0, round((expected-.3)*rate)), min(len(mono), round((expected+.3)*rate)+len(template))
        segment = mono[lo:hi]
        nfft = 1 << (len(segment)+len(template)-1).bit_length()
        cross = np.fft.irfft(np.fft.rfft(segment,nfft)*np.conj(np.fft.rfft(template,nfft)),nfft)[:len(segment)-len(template)+1]
        energy = np.concatenate(([0.], np.cumsum(segment**2)))
        corr = cross / np.sqrt(np.maximum(1e-20, (energy[len(template):]-energy[:-len(template)])*np.sum(template**2)))
        peak = int(np.argmax(corr))
        events.append({'case':case,'sound':name,'expected':expected,'wave_start':(lo+peak)/rate,'offset':(lo+peak)/rate-expected,'correlation':float(corr[peak])})
common_offset = float(np.median([e['offset'] for e in events]))
residual = max(abs(e['offset'] - common_offset) for e in events)
report = {'events':events,'common_recording_offset':common_offset,'max_residual':residual,'peak':float(np.abs(pcm).max()),'rms':float(np.sqrt(np.mean(pcm**2))), 'note':'Source WAV correlation against unedited mixer. This checks contact-spacing preservation across speeds, not absolute device latency. Offsets include capture sampling, recording start and mixer latency; neither WAV nor individual events have been shifted.'}
(run / 'audio-check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
assert min(e['correlation'] for e in events) > .8
# A common recording/output offset is not an animation-speed error. Test the
# spacing against the 50 ms capture resolution, and report absolute offset too.
assert residual < .05
