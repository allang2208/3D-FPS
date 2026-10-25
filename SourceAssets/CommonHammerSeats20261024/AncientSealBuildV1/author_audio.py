"""Original restrained metal-and-stone seal accent; production synthesis only."""
import wave,math,random,struct
from pathlib import Path
P=Path(__file__).resolve().parent;rng=random.Random(2424);rate=44100;samples=[]
for i in range(int(rate*.23)):
    t=i/rate;attack=min(1.,t/.0025)
    sound=sum(a*math.sin(math.tau*f*t)*math.exp(-t/d) for f,a,d in [(142,.32,.075),(283,.20,.062),(607,.15,.038),(1297,.055,.021)])
    sound+=rng.uniform(-1,1)*.018*math.exp(-t/.010)
    sound*=attack*min(1.,(.23-t)/.018)
    samples.append(struct.pack('<h',int(max(-1,min(1,sound))*.72*32767)))
with wave.open(str(P/'S_AncientSeal_Impact.wav'),'wb') as w:w.setparams((1,2,rate,0,'NONE','not compressed'));w.writeframes(b''.join(samples))
print('ANCIENT_SEAL_AUDIO_AUTHORED_NO_AUDITION')
