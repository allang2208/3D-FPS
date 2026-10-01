import bpy,json
from pathlib import Path
O=Path(__file__).parent
source=O.parent/'A762Meshy20260920/Accessories05/A762_AccessoryReady_Editable.blend'
with bpy.data.libraries.load(str(source),link=False) as (_,data):
    data.objects=['SK_M4_Infima'];data.actions=['A_A762_idle']
r=data.objects[0];bpy.context.collection.objects.link(r)
r.animation_data_create();r.animation_data.action=data.actions[0]
r.animation_data.action_slot=r.animation_data.action.slots[0]
r.data.pose_position='POSE';bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
root=r.pose.bones['WPN_root'].matrix
out={'source':str(source),'root_rest':[list(row) for row in r.data.bones['WPN_root'].matrix_local],
    'bind_to_root':{}}
for b in r.data.bones:
    if b.name.startswith('WPN'):
        out['bind_to_root'][b.name]=[list(row) for row in root.inverted()@r.pose.bones[b.name].matrix@b.matrix_local.inverted()]
(O/'Input/frames.json').write_text(json.dumps(out,indent=2))
print('A762_DETAIL_FRAMES',out['root_rest'],flush=True)
