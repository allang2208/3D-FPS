"""Original procedural bench foley. Writes source WAVs; never plays or auditions audio."""
from pathlib import Path
import math,random,wave,array
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored/Audio';OUT.mkdir(exist_ok=True)
RATE=32000
def clip(name,seconds,kind):
    rng=random.Random(name);n=int(seconds*RATE);data=[0.0]*n;lp=0
    for i in range(n):
        t=i/RATE;noise=rng.uniform(-1,1);lp=.83*lp+.17*noise
        fade=min(1,t/.04,(seconds-t)/.08)
        if kind=='grind':
            scrape=max(0,math.sin(t*math.tau*3))**1.7
            data[i]=(.13*(noise-lp)+.07*lp)*(.12+.88*scrape)*fade
        elif kind=='page':data[i]=(noise-lp)*.14*(math.sin(math.pi*t/seconds)**2)*(.55+.45*math.sin(t*math.tau*13)**2)
        elif kind=='pour':data[i]=lp*.055*fade
        elif kind=='boil':data[i]=lp*.016*fade
        elif kind=='click':data[i]=.17*math.exp(-t*48)*(math.sin(t*math.tau*970)+.5*math.sin(t*math.tau*1670))
        elif kind=='bottle':data[i]=lp*.025*max(0,math.sin((t-.7)*math.pi/2))**2*fade
    if kind in ('pour','boil','bottle'):
        events=85 if kind=='pour' else 25 if kind=='boil' else 42
        for _ in range(events):
            at=rng.uniform(.03,seconds-.12) if kind!='bottle' else rng.uniform(1.6,2.7)
            start=int(at*RATE);freq=rng.uniform(430,2100);dur=rng.uniform(.025,.09);gain=rng.uniform(.018,.07)*(0.6 if kind=='boil' else 1)
            for j in range(int(dur*RATE)):
                k=start+j
                if k>=n:break
                t=j/RATE;data[k]+=gain*math.exp(-t/dur*6)*math.sin(math.tau*(freq*t+freq*1.5*t*t))
        if kind=='bottle':
            for start,gain in ((int(.2*RATE),.15),(int(3.4*RATE),.1)):
                for j in range(int(.2*RATE)):
                    t=j/RATE;data[start+j]+=gain*math.exp(-t*32)*(math.sin(t*math.tau*1470)+.3*math.sin(t*math.tau*2410))
    pcm=array.array('h',(int(max(-.9,min(.9,s))*32767) for s in data))
    with wave.open(str(OUT/(name+'.wav')),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(RATE);f.writeframes(pcm.tobytes())
for spec in [('Pour',1.8,'pour'),('Grind',1.5,'grind'),('Boil',2.5,'boil'),('Page',.55,'page'),('Click',.2,'click'),('Bottle',4,'bottle')]:clip(*spec)
print('ALCHEMY_FOLEY_AUTHORED_6')
