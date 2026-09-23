import bpy, json
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;R=O.parent
bpy.ops.wm.open_mainfile(filepath=str(R/'Motion21/PKM_HingedOutlet_Editable.blend'),use_scripts=False)
r=bpy.data.objects['PKM_Manny_Rig'];r.data.pose_position='REST'
fit=Matrix(json.loads((R/'Animation03/animation_manifest.json').read_text())['fit_matrix'])
B=r.data.bones['WPN_root'].matrix_local@fit;Bi=B.inverted()
parts=[]
for ob in bpy.context.scene.objects:
 if ob.type!='MESH' or not ob.name.startswith('PKM_Part_'):continue
 p=[Bi@ob.matrix_world@v.co for v in ob.data.vertices]
 lo=[min(v[k] for v in p) for k in range(3)];hi=[max(v[k] for v in p) for k in range(3)]
 if hi[2]<.07 or lo[2]>.16 or hi[1]<-.065 or lo[1]>.26:continue
 parts.append({'name':ob.name,'bone':ob.get('mechanical_bone'),'min':lo,'max':hi,
  'materials':[m.name for m in ob.data.materials],'vertices':[list(v) for v in p],
  'triangles':[list(t.vertices) for t in ob.data.loop_triangles]})
 # Triangulate only for the saved measurement representation.
 ob.data.calc_loop_triangles();parts[-1]['triangles']=[list(t.vertices) for t in ob.data.loop_triangles]
cover=Bi@r.data.bones['PKM_Cover'].matrix_local
report={'parts':parts,'cover_frame':list(map(list,cover)),'optics':{}}
for key in ['optic_rail','holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x']:
 bpy.ops.wm.open_mainfile(filepath=str(R/'Accessories14'/('SM_PKM_'+key+'.blend')),use_scripts=False)
 rows=[]
 for ob in bpy.context.scene.objects:
  if ob.type!='MESH':continue
  points=[ob.matrix_world@v.co for v in ob.data.vertices]
  rows.append({'name':ob.name,'min':[min(v[k] for v in points) for k in range(3)],
   'max':[max(v[k] for v in points) for k in range(3)],'vertices':[list(v) for v in points],
   'uv_names':[uv.name for uv in ob.data.uv_layers]})
 report['optics'][key]=rows
(O/'source_geometry.json').write_text(json.dumps(report,indent=2))
print('PKM23_PARTS',json.dumps([{k:v for k,v in p.items() if k not in ['vertices','triangles']} for p in parts]),flush=True)
print('PKM23_COVER_FRAME',list(map(list,cover)),flush=True)
