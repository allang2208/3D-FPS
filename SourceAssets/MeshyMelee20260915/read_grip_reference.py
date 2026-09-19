import bpy,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'RuneSword20260913/WristOutsideInspectV34/AzureRunesword_Manny_Editable.blend'))
r=bpy.data.objects['SK_RuneSword_Rig']
print('REFERENCE_OBJECTS',[(o.name,o.type) for o in bpy.context.scene.objects if o.type in {'MESH','ARMATURE'}],flush=True)
print('REFERENCE_ACTIONS',[(a.name,list(a.frame_range)) for a in bpy.data.actions if a.name.startswith('A_RuneSword')],flush=True)
print('REFERENCE_FPS',bpy.context.scene.render.fps,flush=True)
for o in bpy.context.scene.objects:
    if o.type!='MESH' or 'Blade' not in o.name:continue
    M=r.data.bones['WPN_root'].matrix_local.inverted()@r.matrix_world.inverted()@o.matrix_world
    points=[M@v.co for v in o.data.vertices]
    print('REFERENCE_BLADE_BOUNDS',[[min(v[a] for v in points),max(v[a] for v in points)] for a in range(3)],flush=True)
    for z0,z1 in [(-.32,-.24),(-.24,-.16),(-.16,-.08),(-.08,-.03),(-.03,.03)]:
        part=[p for p in points if z0<=p.z<=z1]
        if part:print('REFERENCE_GRIP_SLICE',z0,z1,[[min(v[a] for v in part),max(v[a] for v in part)] for a in range(3)],flush=True)
    for name in ['hand_r','hand_l','Blade_Base','Blade_Tip']:
        print('REFERENCE_POSE',name,list((r.pose.bones['WPN_root'].matrix.inverted()@r.pose.bones[name].matrix).translation),flush=True)
