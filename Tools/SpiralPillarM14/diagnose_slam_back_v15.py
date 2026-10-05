"""Read the reported rear protrusion from the current slam skin and bone poses."""
from pathlib import Path
import bpy, json
import numpy as np
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/SpiralPillarM14Meshy20261004')
OUT=ROOT/'ProductionV15/Records';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'ProductionV14/Authoring/M14_SoftCollapse_v14.blend'))
scene=bpy.context.scene;rig=bpy.data.objects['M14_Rig'];obj=bpy.data.objects['M14_SoftDeathMesh']
obj.data.shape_keys.animation_data_clear()
for key in obj.data.shape_keys.key_blocks:key.value=0
for modifier in obj.modifiers:
    if modifier.type=='ARMATURE':modifier.show_viewport=False
source=np.load(ROOT/'ProductionV11/Records/hardware_source.npz')
p=source['p'];faces=source['f'];groups=[g.name for g in obj.vertex_groups]
bones=np.zeros((len(p),4),np.int32);weights=np.zeros((len(p),4),np.float32)
for i,v in enumerate(obj.data.vertices):
    for k,g in enumerate(sorted(v.groups,key=lambda g:-g.weight)[:4]):bones[i,k]=g.group;weights[i,k]=g.weight
rest=np.array([rig.data.bones[n].matrix_local for n in groups]);rest_inv=np.linalg.inv(rest)
rig.animation_data.action=bpy.data.actions['A_M14_TrunkSlam_v13']
report={'clip':'A_M14_TrunkSlam_v13','source':'ProductionV14','frames':[]}
for frame in (0,24,30,36,40,45,60,78,96):
    scene.frame_set(frame);bpy.context.view_layer.update()
    matrices=np.array([rig.pose.bones[n].matrix for n in groups]);skin=matrices@rest_inv
    q=np.zeros_like(p)
    for k in range(4):
        for bone in np.unique(bones[:,k]):
            ids=np.flatnonzero((bones[:,k]==bone)&(weights[:,k]>0))
            q[ids]+=(p[ids]@skin[bone,:3,:3].T+skin[bone,:3,3])*weights[ids,k,None]
    rear=(q[:,1]>.25)&(q[:,2]>.5)
    regions=[]
    for i,name in enumerate(groups):
        ids=np.flatnonzero((bones[:,0]==i)&(weights[:,0]>.3))
        if len(ids):regions.append({'bone':name,'vertices':len(ids),'head':matrices[i,:3,3].round(4).tolist(),
            'rear_high':int(rear[ids].sum()),'min':q[ids].min(0).round(4).tolist(),'max':q[ids].max(0).round(4).tolist()})
    stretched=[]
    for a,b in ((0,1),(1,2),(2,0)):
        length=np.linalg.norm(p[faces[:,a]]-p[faces[:,b]],axis=1)
        new=np.linalg.norm(q[faces[:,a]]-q[faces[:,b]],axis=1)
        ratio=new/np.maximum(length,1.e-6)
        eligible=np.flatnonzero((length>.003)&(new>.035)&(q[faces].mean(1)[:,1]>-.5))
        top=eligible[np.argsort(ratio[eligible])[-8:]]
        for fi in top:
            ids=faces[fi]
            stretched.append({'face':int(fi),'ratio':float(ratio[fi]),'old_m':float(length[fi]),'new_m':float(new[fi]),
                'material':obj.data.materials[int(source['material'][fi])].name,'position':q[ids].mean(0).round(4).tolist(),
                'source':p[ids].mean(0).round(4).tolist(),
                'skin':[{groups[int(b)]:round(float(w),3) for b,w in zip(bones[v],weights[v]) if w>.001} for v in ids]})
    report['frames'].append({'frame':frame,'bounds':[q.min(0).round(4).tolist(),q.max(0).round(4).tolist()],
        'rear_high_count':int(rear.sum()),'regions':regions,'stretched':sorted(stretched,key=lambda s:-s['ratio'])[:10]})
    if frame==36:np.savez(OUT/'contact_source.npz',p=p,q=q,bones=bones,weights=weights,skin=skin,groups=np.array(groups))
    print('M14_SLAM_READ',frame,'rear',int(rear.sum()),'bounds',q.min(0).round(3),q.max(0).round(3),flush=True)
(OUT/'diagnosis.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print('M14_SLAM_DIAGNOSIS_SAVED',flush=True)
