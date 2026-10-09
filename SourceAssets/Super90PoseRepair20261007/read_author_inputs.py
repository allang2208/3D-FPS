import bpy,json,math
from pathlib import Path
from mathutils import Matrix
P=Path(r'D:/FPS3D/FPSGAME');O=P/'SourceAssets/Super90PoseRepair20261007';S=P/'SourceAssets/BenelliM4Super9020261006'
out={}
for key,file,rig,clip,frame in [
    ('original',S/'BenelliM4_Original_Editable.blend','Rig','M4_Idle',1),
    ('authored',S/'Super90_Gameplay_Editable.blend','SK_Super90','A_Super90_idle',0)]:
    bpy.ops.wm.open_mainfile(filepath=str(file));r=bpy.data.objects[rig];s=bpy.context.scene
    a=next(a for a in bpy.data.actions if a.name==clip or a.name.endswith('|'+clip))
    r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(frame);bpy.context.view_layer.update()
    out[key]={'object':[list(x) for x in r.matrix_world],
              'rest':{b.name:[list(x) for x in r.matrix_world@b.matrix_local] for b in r.data.bones},
              'pose':{b.name:[list(x) for x in r.matrix_world@b.matrix] for b in r.pose.bones}}
(O/'author_inputs.json').write_text(json.dumps(out,indent=2))
print('SUPER90_AUTHOR_INPUTS_SAVED',flush=True)
