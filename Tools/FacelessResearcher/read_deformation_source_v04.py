"""Read authoring geometry to locate the reported spikes, no playback or renders."""
import bpy,json,numpy as np
from pathlib import Path
BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessResearcher20261009');ROOT=BASE/'V04'
for f in ['Authoring','Delivery','Motion','Logs']:(ROOT/f).mkdir(parents=True,exist_ok=True)
report={}
for version in ['V01','V03']:
    bpy.ops.wm.open_mainfile(filepath=str(BASE/version/('Authoring/FacelessResearcher_'+version+'.blend')))
    coat=bpy.data.objects['Researcher_LabCoat_Continuous'];rig=bpy.data.objects['root']
    p=np.array([v.co[:] for v in coat.data.vertices]);half=int(coat['outer_vertex_count'])
    edges=np.array([e.vertices[:] for e in coat.data.edges if all(i<half for i in e.vertices)])
    lengths=np.linalg.norm(p[edges[:,0]]-p[edges[:,1]],axis=1)
    families={};gn={g.index:g.name for g in coat.vertex_groups}
    for label,mask in [('waist',(p[:,2]>.97)&(p[:,2]<1.22)&(abs(p[:,0])<.26)),('chest',(p[:,2]>1.25)&(abs(p[:,0])<.22))]:
        totals={}
        for i in np.flatnonzero(mask):
            for g in coat.data.vertices[i].groups:totals[gn[g.group]]=totals.get(gn[g.group],0)+g.weight
        families[label]=sorted(totals.items(),key=lambda v:-v[1])[:18]
    shapes=[]
    for key in coat.data.shape_keys.key_blocks:
        if key.name=='Basis':continue
        co=np.empty(p.size,np.float32);key.data.foreach_get('co',co);co=co.reshape(p.shape)
        delta=np.linalg.norm(co-p,axis=1);idx=int(delta.argmax())
        gradient=np.linalg.norm((co-p)[edges[:,0]]-(co-p)[edges[:,1]],axis=1)
        edge=int(gradient.argmax())
        shapes.append({'name':key.name,'max_m':float(delta[idx]),'position':p[idx].tolist(),
            'largest_edge_jump_m':float(gradient[edge]),'jump_position':p[edges[edge,0]].tolist(),
            'jump_edge_m':float(lengths[edge])})
    report[version]={'half':half,'vertices':len(p),'pair_separation_percentiles_m':np.percentile(np.linalg.norm(p[:half]-p[half:],axis=1),[0,50,95,100]).tolist(),
        'weights':families,'worst_shapes':sorted(shapes,key=lambda v:-v['largest_edge_jump_m'])[:12],
        'bones':{b.name:(rig.matrix_world@b.head_local)[:] for b in rig.data.bones if b.name in ['pelvis','spine_01','spine_02','spine_03','neck_01','clavicle_l','upperarm_l','lowerarm_l','hand_l','thigh_l','calf_l']}}
(ROOT/'deformation_source.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)
