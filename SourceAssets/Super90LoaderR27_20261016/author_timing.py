"""Write the R27 push clock header and its timing record (no pose change)."""
import json
from pathlib import Path
import r27_timing as T

O = Path(__file__).parent
P = O.parents[1]
H = P / 'Source/FPSGAME/Weapons/Super90LoaderPushTiming.h'
before = O / 'Before/Source/Super90LoaderPushTiming.h'
if not before.exists():
    before.parent.mkdir(parents=True, exist_ok=True)
    before.write_bytes(H.read_bytes())
H.write_text(T.header(), encoding='utf-8')
audio = json.loads((O.parent / 'Super90LoaderR16_20261009/audio_provenance.json').read_text())
record = dict(revision='Super90LoaderR27-20261016', fps=60, base_rate=1.3, split_source_frame=T.SPLIT,
    alignment='R25 span 86-104 unchanged', drive_control=T.DRIVE, drive_scale=T.scale,
    knots=[dict(pace=p, source=s, slope=m) for p, s, m in T.KNOTS],
    cues=[dict(asset=c['asset'], source_frame=c['animation_frame'], pace_frame=T.pace_frame(c['animation_frame']))
          for c in audio['audio']], runtime_tested=False)
(O / 'timing.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
print('R27_TIMING', len(T.KNOTS), 'knots; drive scale', round(T.scale, 4))
