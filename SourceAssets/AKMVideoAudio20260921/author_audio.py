"""Extract the user-selected video cues; no audition or gameplay test."""
from pathlib import Path
import hashlib
import json
import subprocess
import imageio_ffmpeg
import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
SOURCE = Path(r'C:\Users\allan\.codex\tmp\bilibili-BV17VtT6REZr\reference.mp4')
# Exact source-video seconds. Roles are editorial adaptations to AKM's existing
# contact events, inferred from the reference animation and waveform transients.
CUES = {
    'Fire': (373.040, 373.435),
    'MagOut': (377.000, 377.190),
    'MagInsert': (377.280, 377.445),
    'MagSeat': (377.450, 377.660),
    'ChargePull': (377.935, 378.185),
    'ChargeRelease': (378.195, 378.460),
}
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-v', 'error', '-y',
                '-i', str(SOURCE), '-ss', '370', '-t', '9', '-vn',
                '-ar', '48000', '-ac', '2', str(HERE / 'reference_610_619.wav')], check=True)
x, sr = sf.read(HERE / 'reference_610_619.wav', always_2d=True)
records = []
for cue, (start, end) in CUES.items():
    y = x[round((start-370)*sr):round((end-370)*sr)].copy()
    # Tiny edge fades prevent edit clicks; retain original pitch and level.
    fade_in = min(round(.0005*sr), len(y))
    fade_out = min(round(.015*sr), len(y))
    y[:fade_in] *= np.linspace(0, 1, fade_in)[:, None]
    y[-fade_out:] *= np.linspace(1, 0, fade_out)[:, None]
    name = 'S_AKM_' + cue
    sf.write(HERE / (name + '.wav'), y, sr, subtype='PCM_16')
    records.append(dict(name=name, source_start=start, source_end=end,
                        duration=len(y)/sr, peak=float(np.max(np.abs(y)))))
(HERE / 'provenance.json').write_text(json.dumps(dict(
    source_url='https://www.bilibili.com/video/BV17VtT6REZr/',
    source_creator='LAZERH', source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    request='User requested fire near 6:12 and reload/charging at 6:17-6:19.',
    rights='User-directed local extraction; third-party rights retained. No redistribution license established.',
    notes='Mixed video soundtrack, not isolated stems. Roles adapted to AKM. Not auditioned.',
    cues=records), ensure_ascii=False, indent=2), encoding='utf-8')
print('Authored six AKM cues:', ', '.join(CUES))
