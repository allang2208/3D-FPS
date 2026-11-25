"""Measure this riding coat and fingerless Meshy hand bones in the skeleton's UE component space."""
from pathlib import Path
import bpy
import numpy as np
root=Path(__file__).resolve().parents[5]
home=root/'SourceAssets/HillsVillageStable'
out=home/'StablemasterBackIdleR7'
bpy.ops.wm.open_mainfile(filepath=str(home/'StablemasterHeadR5/StablemasterNative.blend'))
body=bpy.data.objects['SK_Stablemaster_Body_R5'];rig=body.parent
sign=np.array([1.,-1.,1.])
points={name:[] for name in ['LeftHand','RightHand','coat']}
for v in body.data.vertices:
    group=max(v.groups,key=lambda g:g.weight)
    name=body.vertex_groups[group.group].name
    p=np.array(v.co)*sign
    if name in ('LeftHand','RightHand') and group.weight>.72:
        points[name].append(p-np.array(rig.data.bones[name].head_local)*sign)
    if (name.startswith('Spine') or name=='Hips') and 80<p[2]<118 and p[1]<0:
        points['coat'].append(p)
np.savez_compressed(out/'tailoring.npz',**{k:np.asarray(a,'f') for k,a in points.items()})
