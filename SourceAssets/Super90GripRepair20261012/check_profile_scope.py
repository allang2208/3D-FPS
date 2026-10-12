"""Targeted contact-layer audit requested by the user; no game execution."""
import json,gzip,sys,numpy as np
from pathlib import Path
O=Path(__file__).parent;sys.path.insert(0,str(O))
from grip_math import load,sample
before=load('profiles_before');after=load('profiles_after')
report={}
for family,b in before.items():
    a=after[family];assert [c['base'] for c in b['clips']]==[c['base'] for c in a['clips']]
    max_translation=0.;max_scale=0.
    for old,new in zip(b['clips'],a['clips']):
        assert abs(old['duration']-new['duration'])<1e-5
        assert [t for t in old['tracks'] if not t['bone'].endswith('_l')]==[t for t in new['tracks'] if not t['bone'].endswith('_l')]
        original={t['bone']:t for t in old['tracks']}
        for tr in new['tracks']:
            if not tr['bone'].endswith('_l'):continue
            for i,time in enumerate(tr['times']):
                prev=sample(original[tr['bone']],time) if tr['bone'] in original else [0,0,0,0,0,0,1,0,0,0]
                current=tr['values'][i*10:i*10+10]
                if tr['bone']!='clavicle_l':max_translation=max(max_translation,max(abs(x-y) for x,y in zip(prev[:3],current[:3])))
                max_scale=max(max_scale,max(abs(x-y) for x,y in zip(prev[7:],current[7:])))
    assert max_translation<.0001 and max_scale<.0001
    report[family]={'clips_preserved':len(a['clips']),'non_left_tracks_unchanged':True,'max_non_clavicle_local_translation_error':max_translation,'max_local_scale_error':max_scale}
(O/'scope_check.json').write_text(json.dumps(report,indent=2))
print('CONTACT_LAYER_SCOPE_OK '+json.dumps(report),flush=True)
