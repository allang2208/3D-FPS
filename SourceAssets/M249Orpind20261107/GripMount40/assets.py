"""Production paths of the M249 parts and currently approved pose sources."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]
COMMON='/Game/Weapons/M249/CommonParts20261108'
ASSEMBLY='/Game/Weapons/M249/Assembly/SM_M249_'
RIG='/Game/Weapons/M249/SK_M249_V7'
FRONT={key:COMMON+'/Meshes/SM_M249_'+key for key in ('vertical','tactical_vertical','angled','canted','prism')}
FRONT['base']='/Game/Weapons/LMGStabilityGrip20261111/SM_M249_StabilityGrip'
BACK={key:COMMON+'/Meshes/SM_M249_'+key for key in ('phantom_reargrip','balanced_reargrip','stable_antislip_reargrip')}
TABLE={key:ASSEMBLY+key for key in ('body','reargrip')}
POSES={f:COMMON+'/Profiles/DA_M249_'+f for f in ('vertical','angled','canted','prism')}
POSES['base']='/Game/Weapons/M249/Bipod/DA_M249_SupportGrip'

def disk(path):return PROJECT/'Content'/(path.removeprefix('/Game/')+'.uasset')
def digest(path):return hashlib.sha256(disk(path).read_bytes()).hexdigest()

if __name__=='__main__':
    inputs={path:digest(path) for path in [RIG,*FRONT.values(),*BACK.values(),*TABLE.values(),*POSES.values()]}
    approved=json.loads((HERE.parent/'Wrist39/saved.json').read_text())
    donor=json.loads((HERE.parent/'Wrist33/inputs.json').read_text())['hashes']
    for path in POSES.values():
        if inputs[path]!=approved[path]:raise RuntimeError('Refresh grip layer '+path)
    for path,h in donor.items():
        if path==RIG or '/Animations/' in path:
            if digest(path)!=h:raise RuntimeError('Refresh pose or topology input '+path)
    stamp=HERE/'inputs.json'
    if stamp.exists() and json.loads(stamp.read_text())!=inputs:raise RuntimeError('Input snapshot already exists')
    stamp.write_text(json.dumps(inputs,indent=2))
