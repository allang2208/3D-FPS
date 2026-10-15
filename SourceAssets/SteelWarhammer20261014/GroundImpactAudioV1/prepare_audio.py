"""Decode the user-selected impact without EQ, pitch or time changes."""
import hashlib,json,subprocess
from pathlib import Path
import imageio_ffmpeg
import numpy as np
import soundfile as sf

P=Path(__file__).resolve().parent
source=Path('D:/FPS3D/资产/音效/砸地.mp3')
(P/'Source').mkdir(exist_ok=True)
original=P/'Source/GroundImpact.mp3'
original.write_bytes(source.read_bytes())
decoded=P/'Source/GroundImpact_Float.wav'
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-y','-i',str(original),'-vn','-map_metadata','-1','-c:a','pcm_f32le',str(decoded)],check=True)
raw,rate=sf.read(decoded,always_2d=True,dtype='float64')
# Remove only the leading near-silence so file playback starts at impact.
# Preserve 2 ms of attack lead-in and the complete original decay.
active=np.flatnonzero(np.max(np.abs(raw),axis=1)>10**(-60/20))
start=max(0,int(active[0])-round(rate*.002)) if len(active) else 0
audio=raw[start:]
peak=float(np.max(np.abs(audio)))
gain=min(1.,.999/peak) if peak>0 else 1.
output=P/'S_Warhammer_GroundImpact.wav'
sf.write(output,audio*gain,rate,subtype='PCM_16')
recipe={'source_path':str(source),'source_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),
    'output':output.name,'sample_rate':rate,'channels':raw.shape[1],'duration_seconds':len(audio)/rate,
    'leading_silence_removed_seconds':start/rate,'clip_prevention_gain':gain,
    'pitch':1.,'time_stretch':1.,'eq_applied':False,'auditioned':False,
    'attribution':'User-provided audio; original rights retained; no redistribution authorization inferred.'}
(P/'provenance.json').write_text(json.dumps(recipe,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(recipe,ensure_ascii=False))
