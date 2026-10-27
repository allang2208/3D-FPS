"""Author the arrow mesh and three short cues; restore the selected generated icon."""
from pathlib import Path
import math,json,shutil
import numpy as np
import soundfile as sf
from scipy.signal import butter,sosfilt,resample_poly
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/MagicArrowRain20261026'
OUT.mkdir(parents=True,exist_ok=True)
vertices=[];faces=[]
def vertex(p):vertices.append(p);return len(vertices)
def face(*ids):faces.append(ids)
def ring(x,r,n=12):return [vertex((x,r*math.cos(i*math.tau/n),r*math.sin(i*math.tau/n))) for i in range(n)]
a,b=ring(-76,.32),ring(-12,.32)
for i in range(12):
    j=(i+1)%12;face(a[i],a[j],b[j]);face(a[i],b[j],b[i])
tip=vertex((0,0,0));ridge=vertex((-10,0,1.15));under=vertex((-10,0,-1.15));left=vertex((-14,-2.9,0));right=vertex((-14,2.9,0));back=vertex((-11,0,0))
for f in [(tip,left,ridge),(tip,ridge,right),(tip,under,left),(tip,right,under),(left,back,ridge),(ridge,back,right),(left,under,back),(right,back,under)]:face(*f)
for i in range(3):
    angle=i*math.tau/3
    def p(x,r):return vertex((x,r*math.cos(angle),r*math.sin(angle)))
    ids=[p(-75,.32),p(-73,2.4),p(-58,.32)]
    face(*ids);face(*reversed(ids))
with (OUT/'SM_ArrowRain.obj').open('w',encoding='ascii') as f:
    f.write('# Magic Arrow Rain, centimeters, +X forward, tip at origin\no ArrowRain\n')
    for v in vertices:f.write('v %.6f %.6f %.6f\n'%v)
    # Interchange expects explicit UV and normal indices even for the untextured metal mesh.
    for x,y,z in vertices:f.write('vt %.6f %.6f\n'%((x+76)/76,(math.atan2(z,y)+math.pi)/math.tau))
    for t in faces:
        p,q,r=[np.asarray(vertices[i-1]) for i in t]
        n=np.cross(q-p,r-p);n/=max(float(np.linalg.norm(n)),1.e-9)
        f.write('vn %.6f %.6f %.6f\n'%tuple(n))
    for normal,t in enumerate(faces,1):f.write('f '+' '.join(f'{i}/{i}/{normal}' for i in t)+'\n')
RATE=48000;rng=np.random.default_rng(1026)
def read(name):
    p=ROOT/'SourceAssets/HeartPiercingArrowAudioCandidates20261026/Sources'/name
    x,rate=sf.read(p,always_2d=True);x=x.mean(axis=1)
    if rate!=RATE:x=resample_poly(x,RATE,rate)
    return x
def filt(x,cut,kind):return sosfilt(butter(3,cut,kind,fs=RATE,output='sos'),x)
def write(name,x,peak):
    x=np.asarray(x);x-=x.mean();x[:48]*=np.linspace(0,1,48);x[-480:]*=np.linspace(1,0,480)
    x*=peak/max(1e-6,abs(x).max());sf.write(OUT/(name+'.wav'),np.column_stack((x,x)),RATE,subtype='PCM_24')
release=np.zeros(int(.60*RATE));bow=read('Bow.wav');wind=read('swish_3.wav')
for x,gain,delay in [(bow,1.,0),(wind,.22,int(.012*RATE))]:
    count=min(len(x),len(release)-delay);release[delay:delay+count]+=filt(x[:count],100,'highpass')*gain
release*=np.exp(-np.arange(len(release))/RATE*3);write('S_ArrowRainRelease',release,.58)
t=np.arange(int(.32*RATE))/RATE
burst=np.sin(math.tau*(130*t-65*t*t))*np.exp(-t*22)*.65+filt(rng.normal(size=len(t)),[90,1800],'bandpass')*np.exp(-t*24)*.3
write('S_ArrowRainBurst',burst,.30)
impact=np.zeros(int(.65*RATE))
for i in range(14):
    delay=int((i/14*.20+rng.uniform(0,.006))*RATE);t=np.arange(int(.11*RATE))/RATE
    tap=(filt(rng.normal(size=len(t)),[450,6500],'bandpass')*np.exp(-t*75)*.65+np.sin(math.tau*(150+i*3)*t)*np.exp(-t*50)*.25)
    impact[delay:delay+len(t)]+=tap*(.65+.35*rng.random())
t=np.arange(len(impact))/RATE;impact+=filt(rng.normal(size=len(impact)),[180,2000],'bandpass')*np.exp(-t*8)*.06
write('S_ArrowRainImpact',impact,.70)
shutil.copy2(OUT/'magic_arrow_rain_cold_steel.png',ROOT/'Content/ColdSteelData/Skills/magic_arrow_rain_cold_steel.png')
(OUT/'sources.json').write_text(json.dumps({'icon':'AI generated original; same cold steel reference family','mesh':'Original procedural OBJ, centimeter units, tip at origin, forward +X','sound_sources':['artisticdude / Battle Sound Effects / Bow.wav and swish_3.wav (CC0)','Original synthesized burst and clustered impacts (CC0)'],'audio_sample_rate':RATE,'gameplay_tested':False,'listening_approved':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('Arrow Rain editable mesh, single-shot sound sources and icon saved.')
