"""Read the existing shipped SourceMatched AKM idle grip, without editing it."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent/'AKMSoviet20260911/AKM_Soviet_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(S),use_scripts=False);r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
a=bpy.data.actions['AKM_Native_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0)
rest={b.name:r.matrix_world@b.matrix_local for b in r.data.bones};pose={b.name:r.matrix_world@b.matrix for b in r.pose.bones}
# Soviet AKM author coordinates: barrel -Y, up +Z; M870 canonical +Y, up +Z.
G=Matrix.Rotation(math.pi,4,'Z')@pose['WPN_root'].inverted()
out={'source':str(S),'runtime_animation':'/Game/Weapons/AKMIntegration/SourceMatched/A_AKM_idle','action':a.name,'rest':{n:[list(x) for x in m] for n,m in rest.items()},'pose':{n:[list(x) for x in G@m] for n,m in pose.items()},'world_pose':{n:[list(x) for x in m] for n,m in pose.items()},'parents':{b.name:b.parent.name if b.parent else None for b in r.data.bones}}
ob=bpy.data.objects['AKM_Soviet_Native'];ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();out['gun_vertices']=[list(G@ev.matrix_world@v.co) for v in me.vertices];out['gun_faces']=[list(p.vertices) for p in me.polygons];ev.to_mesh_clear()
(O/'akm_grip.json').write_text(json.dumps(out,separators=(',',':')))
print('AKM_GRIP_SOURCE',out['runtime_animation'])
for n in ['hand_l','thumb_01_l','thumb_03_l','index_01_l','index_03_l','middle_01_l','pinky_01_l']:print(n,list((G@pose[n]).translation))
