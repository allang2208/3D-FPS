"""Locate the reported hand spikes in the existing authored sweep, without rendering."""
import bpy,json,numpy as np
from pathlib import Path

BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66');ROOT=BASE/'HandContinuityV08'
(ROOT/'Records').mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'ClawSweepV06/Authoring/M66_claw_sweep_v06.blend'))
rig=bpy.data.objects['M66_Rig'];mesh=bpy.data.objects['M66_Body'];scene=bpy.context.scene
names=[g.name for g in mesh.vertex_groups]
weights=[{names[g.group]:float(g.weight) for g in v.groups if g.weight>.001} for v in mesh.data.vertices]
positions=np.array([v.co[:] for v in mesh.data.vertices])
edges=np.array([e.vertices[:] for e in mesh.data.edges],dtype=int)
original_lengths=np.linalg.norm(positions[edges[:,0]]-positions[edges[:,1]],axis=1)
def below(name,parent):
    bone=rig.data.bones[name]
    while bone.parent:
        bone=bone.parent
        if bone.name==parent:return True
    return False
arm=[b.name for b in rig.data.bones if b.name=='Bone_027' or below(b.name,'Bone_027')]
report={'arm':{},'worst_edges':[],'poses':[]}
for n in arm:
    selected=np.array([w.get(n,0)>.5 for w in weights]);b=rig.data.bones[n]
    report['arm'][n]={'parent':b.parent.name if b.parent else None,'head':list(b.head_local),'tail':list(b.tail_local),
        'dominant_vertices':int(selected.sum()),'bounds':[positions[selected].min(0).tolist(),positions[selected].max(0).tolist()] if selected.any() else None}
rows=[]
for frame in range(0,157,4):
    scene.frame_set(frame);bpy.context.view_layer.update();evaluated=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    points=np.empty(len(mesh.data.vertices)*3);evaluated.data.vertices.foreach_get('co',points);points=points.reshape(-1,3)
    lengths=np.linalg.norm(points[edges[:,0]]-points[edges[:,1]],axis=1)
    stretch=lengths-original_lengths
    for i in np.argsort(stretch)[-3:]:
        a,b=map(int,edges[i]);rows.append({'frame':frame,'time':frame/60.,'vertices':[a,b],
            'rest_length':float(original_lengths[i]),'posed_length':float(lengths[i]),'extra_length':float(stretch[i]),
            'rest_positions':[positions[a].tolist(),positions[b].tolist()],
            'posed_positions':[points[a].tolist(),points[b].tolist()],'weights':[weights[a],weights[b]]})
    if frame in (0,72,80,96,156):
        report['poses'].append({'frame':frame,'bones':{n:{'position':list(rig.pose.bones[n].matrix.translation),
            'local_translation':list(rig.pose.bones[n].location)} for n in arm}})
report['worst_edges']=sorted(rows,key=lambda r:r['extra_length'],reverse=True)[:12]
(ROOT/'Records/deformation_inputs.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M66_HAND_DEFORMATION '+json.dumps({'arm_bones':len(arm),'worst':report['worst_edges'][:2]}),flush=True)
