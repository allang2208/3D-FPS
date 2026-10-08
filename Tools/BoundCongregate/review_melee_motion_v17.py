"""User-requested source motion review: sampled joints and selected real-skin poses."""
from pathlib import Path
import bpy, json, math, sys
import numpy as np
from mathutils import Vector

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006')
revision=sys.argv[sys.argv.index('--revision')+1] if '--revision' in sys.argv else 'V16'
OUT=ROOT/'MeleeV17'/'Review'/revision
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/('Melee'+revision)/('BoundCongregate_Melee'+revision+'.blend')))
scene=bpy.context.scene
rig=next(o for o in scene.objects if o.type=='ARMATURE')
contract=json.loads((ROOT/('Melee'+revision)/'motion_contract.json').read_text())
names=['body','body_front','maw','jaw_L','jaw_R']+['leg_'+side+str(i)+'_'+part for side in 'LR' for i in range(1,6) for part in ('upper','lower','foot')]
report={}
HZ=240 # Include the half frames between the new 120 Hz baked keys.
for role in ('Bite','Flurry'):
    rig.animation_data.action=bpy.data.actions['A_BoundCongregate_'+role+revision]
    count=round(contract[role.lower()]['duration']*HZ)
    positions=[];rotations=[]
    for i in range(count+1):
        f=1+i/HZ*scene.render.fps
        scene.frame_set(int(f),subframe=f-int(f))
        bpy.context.view_layer.update()
        positions.append([list(rig.pose.bones[n].matrix.translation) for n in names])
        rotations.append([list(rig.pose.bones[n].matrix.to_quaternion()) for n in names])
    positions=np.array(positions);rotations=np.array(rotations)
    rotations/=np.linalg.norm(rotations,axis=2,keepdims=True)
    steps=np.linalg.norm(np.diff(positions,axis=0),axis=2)*100
    angles=np.degrees(2*np.arccos(np.clip(np.abs((rotations[1:]*rotations[:-1]).sum(axis=2)),0,1)))
    supports=[n for n in names if n.endswith('_foot') and not (role=='Flurry' and n in ('leg_L1_foot','leg_R1_foot'))]
    result={'duration':count/HZ,'sample_hz':HZ,'finite':bool(np.isfinite(positions).all() and np.isfinite(rotations).all()),
        'closure_max_cm':float(np.linalg.norm(positions[-1]-positions[0],axis=1).max()*100),
        'closure_max_deg':float(np.degrees(2*np.arccos(np.clip(np.abs((rotations[-1]*rotations[0]).sum(axis=1)),0,1))).max()),
        'support_drift_cm':{n:float(np.linalg.norm(positions[:,names.index(n)]-positions[0,names.index(n)],axis=1).max()*100) for n in supports},
        'maximum_steps':{n:{'cm_per_sample':float(steps[:,k].max()),'deg_per_sample':float(angles[:,k].max()),'peak_angle_time':float((angles[:,k].argmax()+1)/HZ)} for k,n in enumerate(names)}}
    report[role]=result
    np.savez_compressed(OUT/(role+'_joints.npz'),positions=positions,rotations=rotations,names=names,hz=HZ)
(OUT/'source_motion_review.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({k:{'finite':v['finite'],'closure_cm':v['closure_max_cm'],'support_max_cm':max(v['support_drift_cm'].values()),'worst_angles':sorted(v['maximum_steps'].items(),key=lambda x:x[1]['deg_per_sample'],reverse=True)[:3]} for k,v in report.items()}),flush=True)
if '--render' not in sys.argv and '--motion' not in sys.argv:sys.exit(0)
for obj in list(scene.objects):
    if obj.type in ('CAMERA','LIGHT'):bpy.data.objects.remove(obj,do_unlink=True)
    elif obj.type=='MESH' and ('Proxy' in obj.name or 'proxy' in obj.name):obj.hide_render=True
scene.render.engine='CYCLES';scene.cycles.samples=10;scene.cycles.use_denoising=True
scene.render.resolution_x=760;scene.render.resolution_y=640;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.threads_mode='FIXED';scene.render.threads=8
if '--motion' in sys.argv:
    scene.render.resolution_x=480;scene.render.resolution_y=400;scene.cycles.samples=4
scene.view_settings.view_transform='AgX'
scene.world=bpy.data.worlds.new('MeleeReview');scene.world.use_nodes=True
background=scene.world.node_tree.nodes.new('ShaderNodeBackground')
background.inputs[0].default_value=(.19,.21,.23,1)
background.inputs[1].default_value=.4
world_output=scene.world.node_tree.nodes.new('ShaderNodeOutputWorld')
scene.world.node_tree.links.new(background.outputs[0],world_output.inputs[0])
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.025))
floor=bpy.context.object;mat=bpy.data.materials.new('MeleeReviewFloor');mat.diffuse_color=(.12,.13,.15,1);floor.data.materials.append(mat)
target=Vector((0,-.2,1.15))
for name,location,power,size in [('Key',(-3,-4,6),1100,4),('Fill',(4,-2,3),700,3),('Rim',(1,4,5),900,3)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob);ob.location=location;ob.rotation_euler=(target-ob.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('MeleeReviewCamera');cam=bpy.data.objects.new('MeleeReviewCamera',data);scene.collection.objects.link(cam);scene.camera=cam
data.type='ORTHO';data.ortho_scale=5.4;cam.location=(6,-6,3.6);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
for role in ('Bite','Flurry'):
    rig.animation_data.action=bpy.data.actions['A_BoundCongregate_'+role+revision]
    entry=contract[role.lower()]
    if role=='Bite':times=[0,entry.get('windup_end',entry['contact']-.12),entry['contact'],entry['contact']+.15,entry['duration']]
    else:times=[0,entry.get('strike_starts',[entry['contacts'][0]-.12])[0],entry['contacts'][0],entry['contacts'][1],entry['contacts'][-1],entry['duration']]
    if '--motion' in sys.argv:
        times=[i/30 for i in range(math.ceil(entry['duration']*30)+1)]
        (OUT/role).mkdir(exist_ok=True)
    for i,t in enumerate(times):
        f=1+t*scene.render.fps;scene.frame_set(int(f),subframe=f-int(f))
        scene.render.filepath=str(OUT/role/f'{i:03}.png' if '--motion' in sys.argv else OUT/(role+f'_{i:02}_{t:.3f}.png'))
        bpy.ops.render.render(write_still=True)
print('SOURCE_POSES_RENDERED',flush=True)
