"""Compare right-hand surface proximity to the actual source rear grip."""
import bpy,json,statistics
from pathlib import Path
from mathutils.bvhtree import BVHTree
P=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(P/'Base/M4_QuickCombat_Base_Editable.blend'))
rig=bpy.data.objects['SK_M4_Infima'];scene=bpy.context.scene
grip=bpy.data.objects['M4_Grip Default Unreal_Export'];arms=bpy.data.objects['SK_Manny_Arms_Export']
groups={g.index:g.name for g in arms.vertex_groups}
right={'hand_r'}|{b.name for b in rig.data.bones['hand_r'].children_recursive}
ids=[v.index for v in arms.data.vertices if v.groups and groups[max(v.groups,key=lambda g:g.weight).group] in right]
rows=[]
for rev in ('K','N'):
    a=bpy.data.actions[f'M4_QuickCombatRefine{rev}_Base'];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
    for f in (0,4,8,12,20,32,72,96,108):
        scene.frame_set(f);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
        ge=grip.evaluated_get(dg);gm=ge.to_mesh();ae=arms.evaluated_get(dg);am=ae.to_mesh()
        verts=[ge.matrix_world @ v.co for v in gm.vertices]
        tree=BVHTree.FromPolygons(verts,[tuple(p.vertices) for p in gm.polygons])
        distances=[];negative=[]
        for i in ids:
            point=ae.matrix_world @ am.vertices[i].co
            near,normal,index,distance=tree.find_nearest(point)
            distances.append(distance*1000)
            if (point-near).dot(normal)<0:negative.append(distance*1000)
        rows.append({'revision':rev,'frame':f,'vertices':len(ids),'vertices_within_2mm':sum(d<2 for d in distances),
                     'minimum_distance_mm':min(distances),'normal_signed_inward_max_mm':max(negative,default=0),
                     'normal_signed_inward_over_2mm':sum(d>2 for d in negative)})
        ge.to_mesh_clear();ae.to_mesh_clear()
(P/'contact_checks.json').write_text(json.dumps({'note':'Source rear grip only; nearest-surface normals are not a proof of solid intersection. Finger curl unchanged. No whole-weapon collision claim.','samples':rows},indent=2))
print('CONTACT_CHECK',json.dumps(rows),flush=True)
