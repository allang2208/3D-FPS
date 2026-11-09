"""Record the six M249 pace maps and the two magazine attribute timings."""
from pathlib import Path
import json,re,hashlib
import numpy as np
r=Path(__file__).resolve().parent;project=r.parents[2]
header=project/'Source/FPSGAME/Weapons/M249ReloadTiming.h'
code=header.read_text(encoding='utf-8')
constants={k:float(v.rstrip('f')) for k,v in re.findall(r'(NormalSeconds|EmptySeconds|ChargeStart|ChargePull|ChargeRear|ChargePush|ChargeClosed)=([0-9.f]+)',code)}
def number(v):return constants[v] if v in constants else float(v.rstrip('f'))
curves={}
for name,body in re.findall(r'inline constexpr FKey (\w+)\[\]=\{(.*?)\};',code,re.S):
    curves[name]=np.array([[number(v.strip()) for v in pair.split(',')] for pair in re.findall(r'\{([^{}]+)\}',body)])
def sample(keys,t):
    x,y=keys.T;slopes=np.diff(y)/np.diff(x);tangent=np.r_[slopes[0],2*slopes[:-1]*slopes[1:]/(slopes[:-1]+slopes[1:]),slopes[-1]]
    i=np.clip(np.searchsorted(x,t,side='left')-1,0,len(x)-2);span=x[i+1]-x[i];a=np.clip((t-x[i])/span,0,1)
    return (2*a**3-3*a**2+1)*y[i]+(a**3-2*a**2+a)*span*tangent[i]+(-2*a**3+3*a**2)*y[i+1]+(a**3-a**2)*span*tangent[i+1]
def runtime(keys,source):
    lo,hi=0.,keys[-1,0]
    for _ in range(20):
        mid=(lo+hi)/2
        if sample(keys,mid)<source:lo=mid
        else:hi=mid
    return float((lo+hi)/2)
events={'out':.72,'insert':2.55,'seat':2.70,'cycle_begin':2.85,'pull':3.18,'rear':3.41,'push':3.53,'closed':3.87}
report={'header_sha256':hashlib.sha256(header.read_bytes()).hexdigest(),'curves':{},'catalog':{},'gameplay_tested':False}
for name,keys in curves.items():
    t=np.linspace(0,keys[-1,0],10001);s=sample(keys,t)
    assert np.all(np.diff(keys,axis=0)>0) and np.all(np.diff(s)>0),name
    assert abs(s[0])<1.e-9 and abs(s[-1]-keys[-1,1])<1.e-9,name
    row={'duration':float(keys[-1,0]),'source_end':float(keys[-1,1]),'monotone':True,'keys':keys.tolist()}
    if name.startswith('Side'):
        contacts=events if name.endswith('Empty') else {k:events[k] for k in ['out','insert','seat']}
        row['contacts']={k:runtime(keys,v) for k,v in contacts.items()}
    report['curves'][name]=row
catalog=project/'Content/ColdSteelData/gunsmith.json'
weapon=next(w for w in json.loads(catalog.read_text(encoding='utf-8'))['weapons'] if w['id']=='ue_m249')
for mag in ['30','45']:
    opt=next(o for o in weapon['options']['magazine'] if o['id']=='m249_side_mag_'+mag)
    normal=weapon['base']['reload_time']*opt['stats']['reload_mult'];empty=weapon['base']['empty_reload_time']*opt['stats']['empty_reload_mult']
    assert abs(normal-curves['Side'+mag+'Normal'][-1,0])<1.e-6
    assert abs(empty-curves['Side'+mag+'Empty'][-1,0])<1.e-6
    report['catalog'][mag]={'normal_seconds':normal,'empty_seconds':empty,'capacity':weapon['base']['mag_size']+opt['stats']['mag_delta']}
report['catalog_sha256']=hashlib.sha256(catalog.read_bytes()).hexdigest()
report['charged_tail_seconds']={mag:report['curves']['Side'+mag+'Empty']['contacts']['closed']-report['curves']['Side'+mag+'Empty']['contacts']['pull'] for mag in ['30','45']}
(r/'timing_receipt.json').write_text(json.dumps(report,indent=2))
for mag,row in report['catalog'].items():print(mag,'rounds',round(row['normal_seconds'],3),round(row['empty_seconds'],3))
print('Six pace maps monotone; catalog durations match; charge tails',report['charged_tail_seconds'])
