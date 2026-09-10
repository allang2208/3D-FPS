"""Validate the real UE mixer WAV and locate copied HK416 contact waveforms."""
from pathlib import Path
from datetime import datetime
import json, re, subprocess, wave, sys
import numpy as np

ROOT = Path(__file__).resolve().parent
LABEL = sys.argv[1] if len(sys.argv)>1 else 'm4-hk416-av60-audible'
RUN = ROOT.parents[1] / 'Saved/GunplayUpgrade' / LABEL
FFMPEG = ROOT.parent / 'M4Infima/PreviewTools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
with wave.open(str(RUN / 'GunplayAudio.wav')) as w:
    rate, channels, frames = w.getframerate(), w.getnchannels(), w.getnframes()
    pcm = np.frombuffer(w.readframes(frames), dtype='<i2').reshape(-1, channels).astype(float) / 32768
mono = pcm.mean(axis=1)
log = (ROOT / f'runtime-{LABEL}.log').read_text(encoding='utf-8-sig', errors='replace')
stamp = r'\[(\d{4}\.\d\d\.\d\d-\d\d\.\d\d\.\d\d:\d{3})\]'
first = re.search(stamp + r'.*GUNPLAY_ASSERT PASS replacement_mesh t=([\d.]+)', log)
parse = lambda s: datetime.strptime(s, '%Y.%m.%d-%H.%M.%S:%f')
origin, first_tick = parse(first[1]), float(first[2])
stop = re.search(stamp + r'.*GUNPLAY_ASSERT PASS fx_expire_after_input_regressions', log)
recording_wall_seconds = (parse(stop[1]) - origin).total_seconds()
names = {'MagOut': 'mag_out', 'MagInsert': 'mag_insert', 'MagSeat': 'mag_seat', 'BoltRelease': 'bolt_release'}
events = []
for match in re.finditer(stamp + r'.*M4_AUDIO_CUE empty=(\d) index=(\d).*late=([\d.]+) sound=S_HK416_(\w+)', log):
    expected = (parse(match[1]) - origin).total_seconds()
    name = names[match[5]]
    template = np.frombuffer(subprocess.check_output([str(FFMPEG), '-v', 'error', '-i', str((ROOT/'Audio' if name=='bolt_release' else ROOT.parent/'M4HK416Replica20260910/Audio')/f'{name}.wav'), '-ac', '1', '-ar', str(rate), '-f', 'f32le', '-']), dtype='<f4').astype(float)
    lo = max(0, round((expected - .5) * rate))
    hi = min(len(mono), round((expected + .7) * rate) + len(template))
    segment = mono[lo:hi]
    nfft = 1 << (len(segment) + len(template) - 1).bit_length()
    cross = np.fft.irfft(np.fft.rfft(segment, nfft) * np.conj(np.fft.rfft(template, nfft)), nfft)[:len(segment)-len(template)+1]
    energy = np.concatenate(([0.], np.cumsum(segment**2)))
    denominator = np.sqrt(np.maximum(1e-20, (energy[len(template):] - energy[:-len(template)]) * np.sum(template**2)))
    corr = cross / denominator
    peak = int(np.argmax(corr))
    events.append(dict(empty=bool(int(match[2])), name=name, correlation=float(corr[peak]), wave_start=(lo+peak)/rate,
                       log_seconds=expected, audio_vs_log_seconds=(lo+peak)/rate-expected, game_event_lateness=float(match[4])))
fire = np.frombuffer(subprocess.check_output([str(FFMPEG), '-v', 'error', '-i', str(ROOT.parent/'M4HK416Replica20260910/Audio/fire.wav'), '-t', '0.08', '-ac', '1', '-ar', str(rate), '-f', 'f32le', '-']), dtype='<f4').astype(float)
segment = mono[round(2.5*rate):round(5.5*rate)]
nfft = 1 << (len(segment)+len(fire)-1).bit_length()
cross = np.fft.irfft(np.fft.rfft(segment,nfft)*np.conj(np.fft.rfft(fire,nfft)),nfft)[:len(segment)-len(fire)+1]
energy = np.concatenate(([0.],np.cumsum(segment**2)))
fire_corr = float(np.max(cross/np.sqrt(np.maximum(1e-20,(energy[len(fire):]-energy[:-len(fire)])*np.sum(fire**2)))))
report = dict(recording=str(RUN/'GunplayAudio.wav'), duration=frames/rate, rate=rate, channels=channels, fire_attack_correlation=fire_corr,
              recording_wall_seconds=recording_wall_seconds,
              peak=float(np.abs(pcm).max()), rms=float(np.sqrt(np.mean(pcm**2))), clipped_samples=int(np.sum(np.abs(pcm)>=.999)),
              first_audit_elapsed=first_tick, events=events,
              note='Waveform correlation against final source clips; audio versus log includes render-buffer latency and recording-start offset. Frame export is 20 Hz.')
(ROOT/f'audio_validation_{LABEL}.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
assert abs(report['duration']-recording_wall_seconds) < .15 and report['rms'] > .001 and not report['clipped_samples']
assert len(events) == 11 and min(e['correlation'] for e in events) > .80
assert fire_corr > .80
