import wave,audioop,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/M1911Integration20260913/Audio')
with wave.open(str(O/'Source/1911_A_34P.wav'),'rb') as w:
 n=w.getnchannels();sr=w.getframerate();sw=w.getsampwidth();data=w.readframes(w.getnframes())
if n==2:data=audioop.tomono(data,sw,.5,.5)
data=audioop.lin2lin(data,sw,2);block=sr//100
levels=[audioop.max(data[i:i+block*2],2) for i in range(0,len(data),block*2)]
peak=max(levels);first=next(i for i,v in enumerate(levels) if v>peak*.35)
start=max(0,first-1)*block*2;tail=min(len(data),start+int(sr*1.5)*2)
clip=data[start:tail];clip=audioop.mul(clip,2,.86*32767/max(1,audioop.max(clip,2)))
with wave.open(str(O/'S_M1911_Fire.wav'),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes(clip)
(O/'source.json').write_text(json.dumps({'source':'The Free Firearm Sound Library, 1911 A_34P','license':'CC0-1.0','original':'https://opengameart.org/content/the-free-firearm-sound-library','mirror':'https://github.com/petroulacl/fps-asset-kit','edit':{'offset_seconds':start/(sr*2),'duration_seconds':len(clip)/(sr*2),'mix':'mono, peak -1.3dB'},'listened_or_tested':False},indent=2))
print('Created M1911 gunshot',sr,'Hz',len(clip)/(sr*2),'s')
