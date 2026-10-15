import bpy,json,numpy as np
from pathlib import Path
BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66');ROOT=BASE/'ThumbDrapeV10'
(ROOT/'Records').mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'SmallHandSeparationV09/Authoring/M66_small_hand_separation_v09.blend'))
rig=bpy.data.objects['M66_Rig'];mesh=bpy.data.objects['M66_Body'];scene=bpy.context.scene
p=np.array([v.co[:] for v in mesh.data.vertices]);edges=np.array([e.vertices[:] for e in mesh.data.edges],int)
names=[g.name for g in mesh.vertex_groups];w=np.zeros((len(p),len(names)))
for v in mesh.data.vertices:
    for g in v.groups:w[v.index,g.group]=g.weight
hand=(p[:,0]<-.46)&(p[:,2]<1.9)
base_length=np.linalg.norm(p[edges[:,0]]-p[edges[:,1]],axis=1)
edge_hand=hand[edges].all(axis=1);worst=[];channels=[]
for frame in (0,18,30,42,50,58):
    scene.frame_set(frame);bpy.context.view_layer.update();evaluated=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    posed=np.empty(len(p)*3);evaluated.data.vertices.foreach_get('co',posed);posed=posed.reshape(-1,3)
    length=np.linalg.norm(posed[edges[:,0]]-posed[edges[:,1]],axis=1)
    delta=np.where(edge_hand,length-base_length,-1)
    for i in np.argsort(delta)[-5:]:
        ids=edges[i];worst.append({'frame':frame,'vertices':ids.tolist(),'rest_cm':float(base_length[i]*100),'posed_cm':float(length[i]*100),
            'positions':p[ids].tolist(),'weights':[{names[j]:float(w[k,j]) for j in np.flatnonzero(w[k]>.001)} for k in ids]})
    channels.append({'frame':frame,'bones':{b.name:{'location':list(b.location),'scale':list(b.scale),'angle':float(b.rotation_quaternion.angle)}
        for b in rig.pose.bones if b.name in ['Bone_%03d'%i for i in list(range(24,29))+list(range(34,38))+list(range(54,74))]}})
bones={b.name:{'parent':b.parent.name if b.parent else None,'head':list(b.head_local),'tail':list(b.tail_local)} for b in rig.data.bones}
report={'worst_thumb_edges':sorted(worst,key=lambda e:e['posed_cm']-e['rest_cm'],reverse=True),'channels':channels,'bones':bones}
(ROOT/'Records/source_anatomy.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
np.savez_compressed(ROOT/'Records/source_arrays.npz',positions=p,edges=edges,weights=w,names=np.array(names))
print('M66_V10_SOURCE '+json.dumps({'worst_edges':report['worst_thumb_edges'][:3]}),flush=True)
