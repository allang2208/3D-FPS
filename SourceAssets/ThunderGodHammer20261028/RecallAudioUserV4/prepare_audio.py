"""Import the two user-selected MP3s under English names; no sound redesign."""
from pathlib import Path
import hashlib
import json
import subprocess
import imageio_ffmpeg
import numpy as np
import soundfile as sf

P=Path(__file__).resolve().parent
SOURCE=Path('D:/FPS3D/资产/音效')
for name in ('Source','Audio'):
    (P/name).mkdir(exist_ok=True)
rows=[]
for original,english,asset,loop in (
    ('划空声.mp3','GuanLei_Recall_Whoosh','S_GuanLei_RecallAirLoop',True),
    ('接住钝器.mp3','GuanLei_Catch_Blunt','S_GuanLei_RecallCatch',False)):
    source=SOURCE/original
    stored=P/'Source'/(english+'.mp3')
    stored.write_bytes(source.read_bytes())
    decoded=P/'Source'/(english+'_Float.wav')
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-y','-i',str(stored),
                    '-vn','-map_metadata','-1','-ar','48000','-c:a','pcm_f32le',str(decoded)],check=True)
    raw,rate=sf.read(decoded,always_2d=True,dtype='float64')
    # Only strip near-silence around the useful sound. Keep 2 ms before onset
    # for the contact transient, and the complete audible decay after it.
    active=np.flatnonzero(np.max(np.abs(raw),axis=1)>10**(-60/20))
    if not len(active):
        raise RuntimeError('Selected source contains no audible signal: '+str(source))
    begin=max(0,int(active[0])-round(rate*.002))
    end=min(len(raw),int(active[-1])+1+round(rate*.004))
    audio=raw[begin:end].copy()
    edge=round(rate*.001)
    audio[:edge]*=np.linspace(0,1,edge)[:,None]
    audio[-edge:]*=np.linspace(1,0,edge)[:,None]
    gain=min(1.,.999/max(1e-10,float(np.max(np.abs(audio)))))
    output=P/'Audio'/(asset+'.wav')
    sf.write(output,audio*gain,rate,subtype='PCM_16')
    rows.append({'file':str(output.relative_to(P)),'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
                 'source_original':str(source),'source_english':str(stored.relative_to(P)),
                 'source_sha256':hashlib.sha256(stored.read_bytes()).hexdigest(),
                 'sample_rate':rate,'channels':audio.shape[1],'seconds':len(audio)/rate,
                 'leading_near_silence_removed_seconds':begin/rate,
                 'trailing_near_silence_removed_seconds':(len(raw)-end)/rate,
                 'edge_fade_seconds':.001,'clip_prevention_gain':gain,
                 'eq_applied':False,'pitch':1.,'time_stretch':1.,'looping':loop})
recipe={'revision':'UserSelectedV4','assets':rows,
        'runtime_destination':'/Game/Weapons/ThunderGodHammer20261028/RecallAudioV1',
        'rights':'Both audio clips explicitly supplied and selected by the user. Original rights retained; no redistribution authorization inferred.',
        'runtime':'Whoosh loops at original pitch until actual catch; catch plays once independently.',
        'gameplay_tested':False}
(P/'audio_manifest.json').write_text(json.dumps(recipe,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(recipe,ensure_ascii=False))
