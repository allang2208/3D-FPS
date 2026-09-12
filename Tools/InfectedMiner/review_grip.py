import bpy,json,sys
from pathlib import Path
from mathutils import Vector
R=Path('D:/FPS3D/FPSGAME/SourceAssets/InfectedMiner20260912');O=R/'Previews/GripV03';O.mkdir(exist_ok=True)
source=R/('Candidates/CMU02_07' if '--cmu' in sys.argv else 'Delivery')
if '--cmu' in sys.argv:O=R/'Previews/CMU02_07';O.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(source/'InfectedMiner_Editable.blend'))
s=bpy.context.scene;r=bpy.data.objects['MinerRig']
for o in list(s.objects):
    if o.type in ['CAMERA','LIGHT']:bpy.data.objects.remove(o,do_unlink=True)
s.render.engine='CYCLES';s.cycles.samples=12;s.render.resolution_x=760;s.render.resolution_y=760;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('MinerGloveReview');s.world.use_nodes=True;next(n for n in s.world.node_tree.nodes if n.type=='BACKGROUND').inputs['Strength'].default_value=.55
for p,e in [((3,-4,4),800),((-3,-2,3),600),((0,3,4),800)]:
    d=bpy.data.lights.new('Review','AREA');d.energy=e;d.size=3;o=bpy.data.objects.new('Review',d);s.collection.objects.link(o);o.location=p;o.rotation_euler=(Vector((0,0,1.2))-o.location).to_track_quat('-Z','Y').to_euler()
d=bpy.data.cameras.new('Review');c=bpy.data.objects.new('Review',d);s.collection.objects.link(c);s.camera=c;d.type='ORTHO'
poses=[('idle','A_Miner_Idle',1)]
if '--attack' in sys.argv:
    contract=json.loads((source/'attack-authoring.json').read_text());contact=contract['contact_time']
    poses += [('windup','A_Miner_Attack',round(contact*.70*30)+1),('contact','A_Miner_Attack',round(contact*30)+1),('follow','A_Miner_Attack',min(contract['frames']+1,round((contact+.2)*30)+1))]
for label,act,frame in poses:
    a=bpy.data.actions[act];r.animation_data.action=a
    if a.slots:r.animation_data.action_slot=a.slots[0]
    s.frame_set(frame);bpy.context.view_layer.update();w=(r.matrix_world@r.pose.bones['hand_l'].matrix).translation
    for view,offset,scale,target in [('palm',Vector((1,-1,.3)),.44,w),('back',Vector((1,1,.3)),.50,w),('whole',Vector((3,-6,2)),3.3,Vector((0,0,1.3)))]:
        if '--whole-only' in sys.argv and view!='whole':continue
        c.location=target+offset;c.rotation_euler=(target-c.location).to_track_quat('-Z','Y').to_euler();d.ortho_scale=scale;s.render.filepath=str(O/f'{label}_{view}.png');bpy.ops.render.render(write_still=True)
print('MINER_GRIP_REVIEW_RENDERED',flush=True)
