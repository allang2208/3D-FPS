"""Register the copied M4 palm surface to the native HK416 release paddle."""
import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;S=O.parent
bpy.ops.wm.open_mainfile(filepath=str(S/'HK416Reworked20260930/HK416_Gameplay_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima']
with bpy.data.libraries.load(str(S/'M4SlapImpact20260910/M4_Hand_MAT_Editable.blend'),link=False) as (src,dst):dst.actions=['M4_MAT_reload_empty']
r.animation_data.action=dst.actions[0];r.animation_data.action_slot=dst.actions[0].slots[0]
bpy.context.scene.frame_set(130);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();ri=r.pose.bones['WPN_root'].matrix.inverted()
hand=next(o for o in bpy.context.scene.objects if o.get('inspect_skin_source'))
button=next(o for o in bpy.context.scene.objects if o.get('HK416_SourceObject')=='Buttons_low')
def surface(o,bone,threshold):
 names=[bone] if bone!='hand_l' else [g.name for g in o.vertex_groups if g.name.endswith('_l') and g.name.startswith(('hand','thumb','index','middle','ring','pinky'))]
 indices={o.vertex_groups[n].index for n in names};ids={v.index for v in o.data.vertices if sum(g.weight for g in v.groups if g.group in indices)>threshold}
 ev=o.evaluated_get(dg);me=ev.to_mesh();points=[ri@ev.matrix_world@v.co for v in me.vertices];faces=[list(f.vertices) for f in me.polygons if all(v in ids for v in f.vertices)]
 tree=BVHTree.FromPolygons(points,faces);selected=[points[i] for i in ids];ev.to_mesh_clear();return tree,selected
palm,_=surface(hand,'hand_l',.65);paddle,points=surface(button,'WPN_BoltCatch',.7)
lo=Vector([min(p[k] for p in points) for k in range(3)]);hi=Vector([max(p[k] for p in points) for k in range(3)])
ray=Vector((hi.x+.1,(lo.y+hi.y)*.5,lo.z+(hi.z-lo.z)*.75))
goal,normal,_,_=paddle.ray_cast(ray,Vector((-1,0,0)),.2)
if goal is None:raise RuntimeError('No upper bolt-release paddle surface')
# This M4 reference identifies the accepted contacting hand surface. Keep
# the original fingers and their contact choice instead of flattening the hand.
contact,_,_,distance=palm.find_nearest(Vector((.0185,-.0934,.055)))
offset=goal+Vector((.0008,0,0))-contact
report={'donor':'M4SlapImpact20260910/M4_Hand_MAT_Editable.blend','action':'M4_MAT_reload_empty','donor_frame':130,'drum_frame':116,'palm_source_point_m':list(contact),'paddle_target_point_m':list(goal),'surface_clearance_m':.0008,'arm_translation_weapon_m':list(offset),'source_palm_marker_distance_m':distance,'method':'rigid translation of complete clavicle/arm/hand chain; no joint rotation solver'}
(O/'slap_contact.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
