import bpy,json
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'Candidate/base/A_M16_reload.blend'),use_scripts=False);r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;s.frame_set(95);bpy.context.view_layer.update()
W=r.pose.bones['WPN_root'].matrix;Wi=W.inverted();p={b.name:b.matrix.copy() for b in r.pose.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones};rest={b.name:b.matrix_local.copy() for b in r.data.bones};local={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in rest}
out={'bones':{n:list((Wi@m).translation) for n,m in p.items() if n.endswith('_l') and n.startswith(('hand','thumb','index','middle','ring','pinky'))}}
mag=bpy.data.objects['M16A2_Magazine'];ev=mag.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();pts=[Wi@r.matrix_world.inverted()@ev.matrix_world@v.co for v in me.vertices];ev.to_mesh_clear();out['slices']={}
for z in [-.10,-.08,-.06,-.04,-.02,0.]:
 row=[v for v in pts if abs(v.z-z)<.008];out['slices'][z]=[[min(v[k] for v in row),max(v[k] for v in row)] for k in range(3)] if row else None
(O/'contact_fit.json').write_text(json.dumps(out,indent=2))
