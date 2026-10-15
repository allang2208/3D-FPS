import bpy,json,numpy as np
from pathlib import Path

BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66');ROOT=BASE/'SmallHandSeparationV09'
(ROOT/'Records').mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'HandContinuityV08/Authoring/M66_hand_continuity_v08.blend'))
rig=bpy.data.objects['M66_Rig'];mesh=bpy.data.objects['M66_Body'];scene=bpy.context.scene
positions=np.array([v.co[:] for v in mesh.data.vertices]);edges=np.array([e.vertices[:] for e in mesh.data.edges],dtype=int)
names=[g.name for g in mesh.vertex_groups];weights=np.zeros((len(positions),len(names)))
for v in mesh.data.vertices:
    for g in v.groups:weights[v.index,g.group]=g.weight
_,unique_ids,weld=np.unique(np.rint(positions/1e-6).astype(np.int64),axis=0,return_index=True,return_inverse=True)
parent=list(range(len(unique_ids)))
def find(i):
    while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
    return i
for a,b in weld[edges]:
    a,b=find(a),find(b)
    if a!=b:parent[b]=a
components={}
for i,k in enumerate(weld):components.setdefault(find(int(k)),[]).append(i)
roi=(positions[:,0]>-.52)&(positions[:,0]<1.0)&(positions[:,1]<-.22)&(positions[:,2]>1.15)&(positions[:,2]<3.35)
rows=[];component_id=np.empty(len(positions),int)
for index,ids in enumerate(components.values()):
    component_id[ids]=index;p=positions[ids];s=weights[ids].sum(0)
    if np.count_nonzero(roi[ids])>10:
        rows.append({'id':index,'vertices':len(ids),'front_vertices':int(np.count_nonzero(roi[ids])),
            'bounds':[p.min(0).tolist(),p.max(0).tolist()],
            'weights':[(names[i],float(s[i])) for i in np.argsort(s)[-8:][::-1]]})
rows.sort(key=lambda r:-r['front_vertices'])
original=np.linalg.norm(positions[edges[:,0]]-positions[edges[:,1]],axis=1)
edge_roi=roi[edges].any(axis=1);stretched=[]
for frame in (0,24,48,60,72,80,96,120,156):
    scene.frame_set(frame);bpy.context.view_layer.update();evaluated=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    p=np.empty(len(positions)*3);evaluated.data.vertices.foreach_get('co',p);p=p.reshape(-1,3)
    lengths=np.linalg.norm(p[edges[:,0]]-p[edges[:,1]],axis=1);delta=np.where(edge_roi,lengths-original,-1)
    for i in np.argsort(delta)[-8:]:
        a,b=map(int,edges[i]);stretched.append({'frame':frame,'vertices':[a,b],'component_ids':[int(component_id[a]),int(component_id[b])],
            'rest_length':float(original[i]),'extra_length':float(delta[i]),'positions':[positions[a].tolist(),positions[b].tolist()],
            'weights':[{names[j]:float(weights[k,j]) for j in np.flatnonzero(weights[k]>.001)} for k in (a,b)]})
report={'components':rows,'worst_edges':sorted(stretched,key=lambda r:-r['extra_length'])[:20],
    'bones':{b.name:{'parent':b.parent.name if b.parent else None,'head':list(b.head_local),'tail':list(b.tail_local)} for b in rig.data.bones}}
(ROOT/'Records/anatomy_inputs.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
np.savez_compressed(ROOT/'Records/anatomy_arrays.npz',positions=positions,edges=edges,weights=weights,
    names=np.array(names),weld=weld,unique_ids=unique_ids,component_ids=component_id)
print('M66_SMALL_HAND_INPUTS '+json.dumps({'welded_components':len(components),'front_components':len(rows),'worst':report['worst_edges'][:2]}),flush=True)
