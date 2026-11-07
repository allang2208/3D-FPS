"""Original synthesized steel chimes; no third-party audio dependencies."""
from pathlib import Path
import math, random, struct, wave
P=Path(__file__).resolve().parent/'Audio';P.mkdir(exist_ok=True)
rate=48000
for name,duration,partials in [
    ('S_OathReady',.24,[(1180,1.,18.),(1779,.38,24.),(2951,.19,32.),(4138,.06,40.)]),
    ('S_OathImpact',.34,[(264,1.,15.),(533,.50,18.),(1198,.22,26.),(2537,.10,33.)])]:
    rng=random.Random(61106)
    values=[]
    for i in range(int(rate*duration)):
        t=i/rate
        value=sum(a*math.sin(2*math.pi*f*t)*math.exp(-decay*t) for f,a,decay in partials)
        value+=rng.uniform(-1,1)*(.035 if name.endswith('Ready') else .10)*math.exp(-65*t)
        value*=min(1.,t/.002)*(1.-max(0.,(t-duration+.02)/.02))
        values.append(value)
    peak=max(abs(v) for v in values)
    with wave.open(str(P/(name+'.wav')),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate)
        w.writeframes(b''.join(struct.pack('<h',int(v/peak*.65*32767)) for v in values))
print('Authored two original oath metal cues.')
