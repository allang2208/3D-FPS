"""Confirm the scoped correction, including all untouched profile clips."""
from pathlib import Path
import json,gzip,hashlib
import numpy as np
here=Path(__file__).resolve().parent;project=here.parents[2]
before=here.parent/'Wrist37';changed=[];unchanged=0
owned={'clavicle_r','upperarm_r','upperarm_twist_01_r','upperarm_twist_02_r',
       'lowerarm_r','lowerarm_twist_01_r','lowerarm_twist_02_r','hand_r'}
for family in ['base','vertical','angled','canted','prism']:
    a=json.load(gzip.open(before/(family+'.json.gz'),'rt'))
    b=json.load(gzip.open(here/(family+'.json.gz'),'rt'))
    assert len(a['clips'])==len(b['clips'])
    for x,y in zip(a['clips'],b['clips']):
        assert x['base']==y['base'] and len(x['tracks'])==len(y['tracks'])
        if x==y:unchanged+=1;continue
        assert x['base'].endswith(('_reload','_reload_empty'))
        bones=[]
        for tx,ty in zip(x['tracks'],y['tracks']):
            assert tx['bone']==ty['bone']
            if tx==ty:continue
            assert tx['bone'] in owned
            # Existing W37 tracks already include the full sample lattice.
            assert tx['times']==ty['times']
            vx=np.asarray(tx['values']).reshape(-1,10);vy=np.asarray(ty['values']).reshape(-1,10)
            assert np.array_equal(vx[:,[0,1,2,7,8,9]],vy[:,[0,1,2,7,8,9]])
            bones.append(tx['bone'])
        changed.append(dict(family=family,clip=x['base'],bones=bones))
guard={}
for package,row in json.loads((here/'assets-after.json').read_text()).items():
    path=project/'Content'/(package.removeprefix('/Game/')+'.uasset')
    guard[package]=hashlib.sha256(path.read_bytes()).hexdigest()==row['after']
assert all(guard.values())
result=dict(changed_clips=changed,unchanged_clips=unchanged,joint_rotation_only=True,
            left_arm_unchanged=True,fingers_unchanged=True,asset_guard=guard)
(here/'scope_receipt.json').write_text(json.dumps(result,indent=2))
print('Changed clips',len(changed),'unchanged',unchanged,'guarded assets',len(guard))
