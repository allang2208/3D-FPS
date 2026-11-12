import json, sys
from pathlib import Path
p=Path(sys.argv[1]); case=int(sys.argv[2])
for role in ['client','host']:
    j=json.loads((p/(role+'.json')).read_text(encoding='utf-8-sig'))
    frames=[f for f in j['frames'] if f['case']==case]
    print(role, j['cases'][case])
    previous=None
    for i,f in enumerate(frames):
        state=(f['active'],f['grounded'],f['rms'])
        if previous is None or state != (previous['active'],previous['grounded'],previous['rms']):
            print('TRANSITION',i,f)
        if previous and abs(f['x']-previous['x'])+abs(f['z']-previous['z'])>max(80,(abs(f['vx'])+abs(f['vz']))*(f['time']-previous['time'])*1.8):
            print('CORRECTION',i,previous,f)
        previous=f
