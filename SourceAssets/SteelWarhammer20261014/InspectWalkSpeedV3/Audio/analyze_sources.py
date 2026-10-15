"""Numeric profile of candidate cue sources (no listening): length, level, envelope, brightness."""
import json,wave
from pathlib import Path
import numpy as np

P=Path(__file__).resolve().parent;ROOT=P.parents[3]
SOURCES={
 'steel_block_01':ROOT/'SourceAssets/MeleeBlockAudio20260927/S_MeleeBlock_01.wav',
 'steel_block_02':ROOT/'SourceAssets/MeleeBlockAudio20260927/S_MeleeBlock_02.wav',
 'forge_anvil':ROOT/'SourceAssets/ForgeInteraction20260927/ForgeHammerImpact.wav',
 'hammer_swing_air':ROOT/'SourceAssets/SteelWarhammer20261014/NormalSwingAudioV1/S_Warhammer_NormalSwing.wav'}
report={}
for key,path in SOURCES.items():
    if not path.exists():report[key]={'missing':str(path)};continue
    with wave.open(str(path),'rb') as w:
        rate=w.getframerate();channels=w.getnchannels();width=w.getsampwidth();data=w.readframes(w.getnframes())
    x=np.frombuffer(data,dtype={2:np.int16,4:np.int32}[width]).astype(np.float64)/(2**(8*width-1))
    x=x.reshape(-1,channels).mean(axis=1)
    win=int(rate*.01);frames=len(x)//win
    rms=np.sqrt((x[:frames*win].reshape(frames,win)**2).mean(axis=1)+1e-12)
    db=20*np.log10(rms);peak_i=int(np.argmax(rms))
    tail=next((i for i in range(len(db)-1,peak_i,-1) if db[i]>db[peak_i]-30),peak_i)
    onset=next(i for i in range(len(db)) if db[i]>db[peak_i]-12)
    spectrum=np.abs(np.fft.rfft(x*np.hanning(len(x))));freq=np.fft.rfftfreq(len(x),1/rate)
    centroid=float((spectrum*freq).sum()/spectrum.sum())
    bands={f'{a}-{b}Hz':round(float(spectrum[(freq>=a)&(freq<b)].sum()/spectrum.sum()),3) for a,b in [(0,300),(300,1500),(1500,5000),(5000,24000)]}
    report[key]={'path':str(path),'rate':rate,'channels':channels,'seconds':round(len(x)/rate,4),
        'peak_dbfs':round(float(20*np.log10(np.abs(x).max()+1e-12)),2),'loudest_10ms_at_s':round(peak_i*.01,3),
        'onset_minus12db_at_s':round(onset*.01,3),
        'loudest_10ms_dbfs':round(float(db[peak_i]),2),'decay_to_minus30db_s':round((tail-peak_i)*.01,3),
        'spectral_centroid_hz':round(centroid,1),'energy_bands':bands}
(P/'source_profile.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('INSPECT_AUDIO_PROFILE '+json.dumps(report))
