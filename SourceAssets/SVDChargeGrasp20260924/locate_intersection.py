import bpy,json,ast
from pathlib import Path
from collections import Counter
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;info=json.loads((O/'authoring.json').read_text())['base/reload_empty'];bpy.ops.wm.open_mainfile(filepath=info['blend'],use_scripts=False)
r=bpy.data.objects['SK_M4_Infima'];a=bpy.data.actions[info['action']];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(330);bpy.context.view_layer.update()
arms=bpy.data.objects['SK_Manny_Arms_Export'];dg=bpy.context.evaluated_depsgraph_get();ev=arms.evaluated_get(dg)
print('MODIFIERS',[(m.type,m.name) for m in arms.modifiers],'VERTICES',len(arms.data.vertices),len(ev.data.vertices),'POLYS',len(arms.data.polygons),len(ev.data.polygons),flush=True)
inv=(r.matrix_world@r.pose.bones['WPN_root'].matrix).inverted()
print('BONES_ROOT',{n:list((r.pose.bones['WPN_root'].matrix.inverted()@r.pose.bones[n].matrix).translation) for n in ['upperarm_r','lowerarm_r','hand_r']},flush=True)
names={g.index for g in arms.vertex_groups if g.name.endswith('_r') and g.name.startswith(('clavicle','upperarm','lowerarm'))}
ids={v.index for v in arms.data.vertices if sum(g.weight for g in v.groups if g.group in names)/max(1e-8,sum(g.weight for g in v.groups))>.9}
faces=[list(f.vertices) for f in arms.data.polygons if all(i in ids for i in f.vertices)];verts=[ev.matrix_world@v.co for v in ev.data.vertices];tree=BVHTree.FromPolygons(verts,faces)
ob=bpy.data.objects['SM_SVD_ScopeBody'];b=ob.evaluated_get(dg);hits=tree.overlap(BVHTree.FromPolygons([b.matrix_world@v.co for v in b.data.vertices],[list(f.vertices) for f in b.data.polygons]))
indices={i for x,y in hits for i in faces[x]};weights=Counter()
for i in indices:
 for g in arms.data.vertices[i].groups:weights[arms.vertex_groups[g.group].name]+=g.weight/len(indices)
points=[inv@verts[i] for i in indices]
print('CROSSING',len(indices),'weights',dict(weights),'root_bounds',[[min(v[j] for v in points),max(v[j] for v in points)] for j in range(3)],flush=True)
print('SCOPE_ROOT_BOUNDS',[[min((inv@b.matrix_world@v.co)[j] for v in b.data.vertices),max((inv@b.matrix_world@v.co)[j] for v in b.data.vertices)] for j in range(3)],flush=True)
