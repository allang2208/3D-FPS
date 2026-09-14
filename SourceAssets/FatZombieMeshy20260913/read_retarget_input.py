import bpy,json
from pathlib import Path
ROOT=Path(__file__).parent
out={}
for role in ['Idle','Walk','Attack','Death']:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(ROOT/f'native_retarget/A_FatZombie_Raw_{role}.fbx'))
    rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
    action=rig.animation_data.action
    record={'object':rig.name,'matrix':[list(r) for r in rig.matrix_world],
            'fps':bpy.context.scene.render.fps,'range':list(action.frame_range),
            'bones':{b.name:{'parent':b.parent.name if b.parent else None,'matrix':[list(r) for r in rig.matrix_world@b.matrix_local]} for b in rig.data.bones},'poses':{}}
    for part in [0,.25,.5,.75,1]:
        f=action.frame_range[0]+part*(action.frame_range[1]-action.frame_range[0])
        bpy.context.scene.frame_set(int(f),subframe=f-int(f))
        record['poses'][str(part)]={b.name:{'head':list((rig.matrix_world@b.matrix).translation),'scale':list(b.scale),'loc':list(b.location),'matrix_scale':list(b.matrix.to_scale())} for b in rig.pose.bones if b.name in ['Hips','Head','LeftHand','RightHand','LeftFoot','RightFoot','Spine02']}
    out[role]=record
(ROOT/'retarget_authoring_input.json').write_text(json.dumps(out,indent=2))
print('RETARGET_INPUT '+json.dumps({k:{p:v[p] for p in ['object','matrix','fps','range','poses']} for k,v in out.items()}))
