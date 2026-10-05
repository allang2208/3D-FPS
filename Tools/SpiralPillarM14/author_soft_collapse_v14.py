"""Bake a staggered tissue collapse; retain V13 seams and the settled footprint."""
from pathlib import Path
import bpy, json, struct
import numpy as np

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/SpiralPillarM14Meshy20261004')
OUT=ROOT/'ProductionV14'
for folder in ('Authoring','Exports','Records'):(OUT/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'ProductionV13/Authoring/M14_HardwareSeams_Spit_v13.blend'))
scene=bpy.context.scene;rig=bpy.data.objects['M14_Rig'];obj=bpy.data.objects['M14_SoftDeathMesh'];mesh=obj.data
rig.animation_data.action=None;scene.frame_set(0)
for pb in rig.pose.bones:pb.location=(0,0,0);pb.rotation_quaternion=(1,0,0,0);pb.scale=(1,1,1)
obj.data.shape_keys.animation_data_clear()
source=np.load(ROOT/'ProductionV11/Records/hardware_source.npz')
p=source['p'].astype(np.float64);vertex_count=len(p)
flat=np.empty(vertex_count*3,np.float32)
mesh.shape_keys.key_blocks['M14_DeathSpread'].data.foreach_get('co',flat)
final=flat.reshape(-1,3).astype(np.float64)
binding=np.load(ROOT/'ProductionV13/Records/hardware_binding.npz')
owner,blend=binding['owner'],binding['blend']
weld=np.load(ROOT/'ProductionV11/Records/hardware_components.npz')['weld']
_,representative,inverse=np.unique(weld,return_index=True,return_inverse=True)
final=final[representative][inverse]

def smooth(v):v=np.clip(v,0,1);return v*v*(3-2*v)
def rigid_fit(source,destination):
    center=source.mean(0);dest=destination.mean(0)
    a,_,bt=np.linalg.svd((source-center).T@(destination-dest));rotation=a@bt
    if np.linalg.det(rotation)<0:a[:,-1]*=-1;rotation=a@bt
    return rotation,dest-center@rotation

# Region boundaries share source positions and the same feathered attachment.
# Corrections replace only the nonrigid part of each hardware trajectory.
hardware=[]
for cid in binding['major']:
    solid=np.flatnonzero((owner==cid)&(blend>=.999999))
    affected=np.flatnonzero((owner==cid)&(blend>0))
    rotation,translation=rigid_fit(p[solid],final[solid])
    end=p[affected]@rotation+translation
    hardware.append((solid,affected,end))

x,y,z=p.T;height=np.clip(z,0,3)
sac_weights=[]
for side in ('L','R'):
    center=np.array(rig.data.bones['sac_'+side].head_local);center[2]-=.18
    d=(p-center)/[.34,.32,.43]
    sac_weights.append(np.exp(-2*np.sum(d*d,axis=1)))
left,right=sac_weights
# Support gives way from the bottom upward; sacs lag independently of the trunk.
delay=.015+.105*height+.055*smooth(x+.5)+.13*left+.23*right
fall_duration=.60+.16*height+.10*left+.13*right
contact=delay+fall_duration
times=[.18,.42,.68,.94,1.20,1.50,1.85,2.35,3.10]
names=[f'M14_DeathSoft_{i+1:02d}' for i in range(len(times))]

for key in list(mesh.shape_keys.key_blocks)[1:]:
    if key.name.startswith('M14_Death'):obj.shape_key_remove(key)

rows=np.zeros((len(representative),3+len(names)*3),dtype='<f4')
rows[:,:3]=p[representative]
for index,(time,name) in enumerate(zip(times,names)):
    if index==len(times)-1:
        target=final.copy()
    else:
        phase=smooth((time-delay)/fall_duration)
        target=p+(final-p)*phase[:,None]
        folding=np.sin(np.pi*phase)
        # The lower and upper coils buckle in opposite directions instead of
        # translating as one straight column. Volume opens sideways under load.
        target[:,0]+=folding*(.24*np.sin(height*2.4)+.10*x)
        target[:,1]+=folding*(.19*np.sin(height*2.1-.4)+.08*y)
        target[:,2]-=folding*.10*np.sin(height*1.6)**2
        elapsed=np.maximum(0,time-contact)
        settle=1-smooth((time-1.8)/1.3)
        recoil=np.sin(elapsed*8.0)*np.exp(-elapsed*3.0)*settle
        target[:,2]+=.055*recoil*smooth(height/.5)
        target[:,0]+=.035*recoil*np.sin(height*3.1)
        # Soft sacs retain some volume, land at different times, then settle.
        for weight,offset in ((left,.04),(right,.14)):
            after=max(0,time-1.12-offset)
            bounce=np.sin(after*7.5)*np.exp(-after*3.4)*settle
            target[:,2]+=.12*weight*bounce
            target[:,0]+=.07*weight*bounce*np.sign(x)
        target[:,2]=np.maximum(.012,target[:,2])
        secondary=target-(p+(final-p)*phase[:,None])
        for solid,affected,end in hardware:
            rotation,translation=rigid_fit(p[solid],target[solid])
            landed=p[solid]@rotation+translation
            translation[2]+=max(0.,.012-float(landed[:,2].min()))
            rigid=p[affected]@rotation+translation
            linear=p[affected]+(end-p[affected])*phase[affected,None]+secondary[affected]
            target[affected]+=(rigid-linear)*blend[affected,None]
        # All material-cut copies get one trajectory, including tiny chain patches.
        target=target[representative][inverse]
    key=obj.shape_key_add(name=name,from_mix=False)
    key.data.foreach_set('co',target.astype(np.float32).ravel());key.value=0
    rows[:,3+index*3:6+index*3]=target[representative]-p[representative]
    print('M14_V14_BAKED',name,time,flush=True)

# Store the exact same linear-between-samples timing in the editable source.
scene.render.fps=30;scene.frame_start=0;scene.frame_end=108
for index,name in enumerate(names):
    key=mesh.shape_keys.key_blocks[name]
    for sample,time in enumerate([0.]+times+[3.6]):
        key.value=1. if sample==index+1 or (sample==len(times)+1 and index==len(times)-1) else 0.
        key.keyframe_insert('value',frame=time*30)
action=mesh.shape_keys.animation_data.action;action.name='M14_SoftCollapse_v14';action.use_fake_user=True
for slot in action.slots:
    for layer in action.layers:
        for strip in layer.strips:
            bag=strip.channelbag(slot)
            if bag:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
scene.frame_set(0)
with (OUT/'Exports/soft_collapse.bin').open('wb') as stream:
    stream.write(struct.pack('<ii',len(rows),len(names)));stream.write(rows.tobytes())
settings={'names':names,'times':times,'settled_seconds':3.10,'clip_seconds':3.6,
          'spit_max_range':3000.,'spit_travel_range':3300.,'aggro_radius':3300.,'leash_radius':4000.}
(OUT/'Exports/soft_collapse.json').write_text(json.dumps(settings,indent=2)+'\n',encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Authoring/M14_SoftCollapse_v14.blend'),compress=True)
report={'complete':True,'source':'ProductionV13','source_vertices':vertex_count,'export_rows':len(rows),
        'source_triangles':len(source['f']),'geometry_removed':0,'death_targets':len(names),
        'sample_seconds':times,'active_targets_max':2,'final_pose':'V13 unchanged; compatible with V06 compound corpse',
        'hardware_regions':len(hardware),'coincident_seams_unified':True,'bone_scale':'unit',
        'tested':False,'rendered':False}
(OUT/'Records/authoring.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print('M14_V14_SOURCE_SAVED',flush=True)
