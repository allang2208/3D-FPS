"""Scoped offline diagnosis of the currently saved lamb grip on the actual V8 surface."""
import sys,json,math,hashlib
from pathlib import Path
import bpy,numpy as np
from mathutils import Matrix,Vector
O=Path(__file__).parent;R=O.parents[1];sys.path.insert(0,str(O));import pose_model as P
m=P.data['roasted_large_lamb']
(O/'before_motion.json').write_text(json.dumps(m,indent=2))
asset=R/'Content/Characters/ModularOutfit20260924/BarePalmV7/Traversal/SK_Traversal_BareArmsV7.uasset'
v8=json.loads((R/'SourceAssets/BareHandAudit20261016/Installed/0fc712f32c7e.json').read_text())
report={'actual_mesh':v8['path'],'saved_sha256':hashlib.sha256(asset.read_bytes()).hexdigest(),'v8_saved_sha256':v8['sha256'],'thumbs':{}}
verts,obj,goal,info=P.solve(m,2.75)
for side,sign in [('l',1),('r',-1)]:
    h='hand_'+side;pr=P.frame(P.rest['middle_01_'+side].translation-P.rest[h].translation,(P.rest['index_01_'+side].translation-P.rest[h].translation).cross(P.rest['pinky_01_'+side].translation-P.rest[h].translation)*sign)
    rows=[]
    for j in range(1,4):
        n=f'thumb_{j:02}_{side}';par=P.parent[n];delta=(goal[par]@P.local[n]).to_quaternion().inverted()@goal[n].to_quaternion()
        if delta.w<0:delta.negate()
        rows.append(dict(bone=n,local_angle_deg=math.degrees(delta.angle),local_axis=list(delta.axis),native_position_in_palm=list(pr.inverted()@(P.rest[n].translation-P.rest[h].translation))))
    report['thumbs'][side]=rows
(O/'diagnosis_before.json').write_text(json.dumps(report,indent=2))
P.render(m,2.75,'current_present')
P.render(m,4.65,'current_bite')
print('V8_CURRENT_MESH_MATCH',report['saved_sha256']==report['v8_saved_sha256'])
print(json.dumps(report['thumbs'],indent=2))
