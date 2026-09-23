"""Read the carry handle's source geometry for hinge placement; no rendering."""
import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;R=O.parent
bpy.ops.wm.open_mainfile(filepath=str(R/'Accessories14/PKM_Modular_Editable.blend'),use_scripts=False)
r=bpy.data.objects['PKM_Manny_Rig'];r.data.pose_position='REST';bpy.context.view_layer.update()
fit=Matrix(json.loads((R/'Animation03/animation_manifest.json').read_text())['fit_matrix'])
gun=r.matrix_world@r.data.bones['WPN_root'].matrix_local@fit
dg=bpy.context.evaluated_depsgraph_get();out={}
for idx in [75,136]:
 ob=bpy.data.objects[f'PKM_Part_{idx:03}'];ev=ob.evaluated_get(dg);me=ev.to_mesh()
 points=[gun.inverted()@ev.matrix_world@v.co for v in me.vertices]
 lo=Vector([min(v[i] for v in points) for i in range(3)]);hi=Vector([max(v[i] for v in points) for i in range(3)])
 near=[v for v in points if v.x<lo.x+.012]
 out[str(idx)]={'bounds':[list(lo),list(hi)],'points':[list(v) for v in points],
  'near_mount_bounds':[[min(v[i] for v in near) for i in range(3)],[max(v[i] for v in near) for i in range(3)]],
  'materials':[m.name for m in ob.data.materials], 'mechanical_bone':ob.get('mechanical_bone')}
 print('HANDLE_SOURCE',idx, 'bounds',out[str(idx)]['bounds'],'mount',out[str(idx)]['near_mount_bounds'],flush=True)
 ev.to_mesh_clear()
(O/'source_geometry.json').write_text(json.dumps(out,indent=2))
