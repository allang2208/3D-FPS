import bpy,json
from pathlib import Path
P=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(next((P/'Original').rglob('*.fbx'))))
m=next(o for o in bpy.context.scene.objects if o.type=='MESH')
print('SWORD_SECTIONS',[(round(z,2),round(max(abs(v.co.x) for v in m.data.vertices if z<=v.co.z<z+.1),3)) for z in [-.95+i*.1 for i in range(19)]],flush=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(P/'Reference/Arms.fbx'))
r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');out={}
for a in bpy.data.actions:
    if not any(x in a.name for x in ['Sword_Idle','Sword_Walk','Sword_Slash']):continue
    r.animation_data_create();r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
    out[a.name.split('|')[-1]]=[]
    for f in range(int(a.frame_range[0]),int(a.frame_range[1])+1):
        bpy.context.scene.frame_set(f)
        out[a.name.split('|')[-1]].append({'frame':f,'right':[list(row) for row in r.matrix_world@r.pose.bones['Wrist.R'].matrix],'left':[list(row) for row in r.matrix_world@r.pose.bones['Wrist.L'].matrix]})
    print(a.name,[(s['frame'],[round(s['right'][i][3],3) for i in range(3)]) for s in out[a.name.split('|')[-1]][::5]],flush=True)
(P/'Reference/motion.json').write_text(json.dumps(out))
