"""Make render inputs from authoring poses, without touching installed assets."""
from pathlib import Path
import json, shutil, sys
import numpy as np

P=Path(__file__).resolve().parent
ROOT=P.parents[1]
native=ROOT/'Saved/HighlandThirdPersonReview20261106/native-v3'
out=ROOT/'Saved/HighlandThirdPerson20261106/AuthorPreview'
out.mkdir(parents=True,exist_ok=True)
if not (out/'parts').exists():shutil.copytree(native/'parts',out/'parts')
shutil.copyfile(native/'parts.json',out/'parts.json')
kind,grip,role=sys.argv[1:4]
folder=out/kind/(grip+'_'+('sweep' if role in ['Sweep','SweepReady'] else 'charged_thrust'))
folder.mkdir(parents=True,exist_ok=True)
for f in ['skin.bind','skin.bones','skin.weights','skin.indices','mesh.json']:
    shutil.copyfile(native/kind/f,out/kind/f)
data=json.loads((P/'Inputs'/f'{kind}-{grip}.json').read_text())
src=P/'Authoring'/f'{kind}_{grip}_{role}'
poses=np.fromfile(src/'poses.bin',np.float32).reshape(-1,len(data['names']),10)[::4]
poses.tofile(folder/'poses.bin')
motion=dict(mount=data['mount'],left_grip=data['left_grip'],role=role,grip=grip,body=kind,
            attack_seconds=1.6 if role=='RidgeThrust' else 4/3,lead_seconds=0.,
            frames=[dict(time=i/30,variant=role,roll=0,slide=0,progress=i/(len(poses)-1),selected=role,post_process_instance=False) for i in range(len(poses))])
(folder/'motion.json').write_text(json.dumps(motion))
print(folder)
