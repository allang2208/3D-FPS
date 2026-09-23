import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;R=O.parent
bpy.ops.wm.open_mainfile(filepath=str(R/'OutgoingBelt19/PKM_OutgoingBelt_Editable.blend'),use_scripts=False)
r=bpy.data.objects['PKM_Manny_Rig'];r.data.pose_position='REST'
fit=Matrix(json.loads((R/'Animation03/animation_manifest.json').read_text())['fit_matrix'])
B=r.data.bones['WPN_root'].matrix_local@fit;Bi=B.inverted()
rows=[]
for ob in bpy.context.scene.objects:
 if ob.type!='MESH' or not ob.name.startswith('PKM_Part_'):continue
 pts=[Bi@ob.matrix_world@v.co for v in ob.data.vertices]
 low=[min(p[k] for p in pts) for k in range(3)];high=[max(p[k] for p in pts) for k in range(3)]
 if high[0]>.022 and low[0]<.12 and high[2]>.057 and low[2]<.10 and low[1]<.095 and high[1]>-.025:
  rows.append({'name':ob.name,'bone':ob.get('mechanical_bone'),'min':low,'max':high,
   'points':[list(p) for p in pts],'materials':[m.name for m in ob.data.materials]})
(O/'source_hinges.json').write_text(json.dumps({'parts':rows,'bones':[b.name for b in r.data.bones]},indent=2))
print('HINGE_PARTS',json.dumps([{k:v for k,v in row.items() if k!='points'} for row in rows]),flush=True)
