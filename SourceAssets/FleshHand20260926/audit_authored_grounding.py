"""Read-only grounding audit of existing authored actions; no save/export/render."""
from pathlib import Path
import json
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'CompletionAudit20260927'
source=ROOT/'Animations/FleshHand_Animated.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
mesh=max((o for o in bpy.context.scene.objects if o.type=='MESH'),key=lambda o:len(o.data.vertices))
rig.animation_data_create()
axis=(rig.matrix_world@rig.data.bones['root'].matrix_local).to_3x3()@Vector((0,0,1))
report={'source':str(source),'mesh':mesh.name,'root_local_z_in_world':list(axis),
        'clips':{},'assets_modified':False,'rendered':False}
for role in ('Idle','Hit','Dizzy','Slam','GrandSlam','Death'):
    action=bpy.data.actions.get('A_FleshHand_'+role)
    if not action:
        report['clips'][role]={'missing':True};continue
    rig.animation_data.action=action
    if action.slots:rig.animation_data.action_slot=action.slots[0]
    first,last=map(float,action.frame_range)
    frames={round(first+(last-first)*t) for t in (0.,.125,.25,.5,.75,1.)}
    if role=='Slam':frames.add(15)
    if role=='GrandSlam':frames.add(32)
    rows=[]
    for frame in sorted(frames):
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        obj=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
        low=min((obj.matrix_world@v.co).z for v in obj.data.vertices)
        rows.append({'frame':frame,'lowest_z_m':low,
                     'main_hand_plane_offset_cm':low*200,
                     'small_hand_plane_offset_cm':low*65,
                     'root_local_location':list(rig.pose.bones['root'].location)})
    report['clips'][role]={'frame_range':[first,last],'samples':rows,
                          'minimum_z_m':min(r['lowest_z_m'] for r in rows)}
OUT.mkdir(exist_ok=True)
(OUT/'authored_grounding.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('HAND_GROUNDING_AUDIT '+json.dumps({k:v.get('minimum_z_m') for k,v in report['clips'].items()}),flush=True)
