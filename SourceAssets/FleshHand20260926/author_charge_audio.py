"""Original mono PCM charge sounds; no external samples or audio preview."""
from pathlib import Path
import math, random, wave, struct, json
root=Path(__file__).resolve().parent/'ChargeVisual';root.mkdir(exist_ok=True)
rate=24000;rng=random.Random(27092026)
for name,duration in [('S_HandChargeWindup',1.2),('S_HandChargeRush',.36)]:
    values=[];low=0.;phase=0.
    for i in range(round(rate*duration)):
        t=i/rate;p=t/duration;white=rng.uniform(-1,1);low+=.12*(white-low)
        envelope=min(1,t/.018)*min(1,(duration-t)/.04)
        if 'Windup' in name:
            phase+=2*math.pi*(58+35*p)/rate
            pulse=.85+.15*math.sin(2*math.pi*(2*p+2*p*p))
            sample=(math.sin(phase)*.28+math.sin(phase*2.01)*.07+low*.45)*(.28+.65*p)*pulse
        else:
            phase+=2*math.pi*(100-50*p)/rate
            sample=(low*.75+white*.08+math.sin(phase)*.12)*math.sin(math.pi*p)**.65
        values.append(int(max(-.85,min(.85,sample*envelope))*32767))
    with wave.open(str(root/(name+'.wav')),'wb') as out:
        out.setnchannels(1);out.setsampwidth(2);out.setframerate(rate)
        out.writeframes(struct.pack('<'+'h'*len(values),*values))
(root/'audio_source.json').write_text(json.dumps({'source':'Original deterministic synthesis; no third-party samples',
    'sample_rate':rate,'channels':1,'seed':27092026,'previewed':False},indent=2),encoding='utf-8')
print('FLESHHAND_CHARGE_AUDIO_AUTHORED')
