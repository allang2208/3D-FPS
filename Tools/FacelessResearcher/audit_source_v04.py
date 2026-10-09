"""Read-only numeric review of accepted author data; no render or re-export."""
import bpy,json
import numpy as np
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessResearcher20261009/V04');OUT=ROOT/'Review20261009';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/FacelessResearcher_V04.blend'))
coat=bpy.data.objects['Researcher_LabCoat_Continuous'];half=int(coat['outer_vertex_count'])
cp=np.array([v.co[:] for v in coat.data.vertices]);a,b=np.array([tuple(e.vertices) for e in coat.data.edges if all(i<half for i in e.vertices)]).T
length=np.linalg.norm(cp[a]-cp[b],axis=1)
report={'objects':{},'shape_edges':[],'loops':{},'finite':True,'source_saved':False,'rendered':False}
for o in bpy.context.scene.objects:
    if o.type!='MESH':continue
    totals=np.array([sum(g.weight for g in v.groups) for v in o.data.vertices])
    report['objects'][o.name]={'vertices':len(totals),'unweighted_vertices':int((totals<1.e-6).sum()),
        'weight_sum_range':[float(totals.min()),float(totals.max())]}
delta={}
for key in coat.data.shape_keys.key_blocks:
    if key.name=='Basis':continue
    p=np.empty(cp.size,np.float32);key.data.foreach_get('co',p);p=p.reshape(cp.shape)
    d=p-cp;delta[key.name]=d[:half]
    jump=np.linalg.norm(d[a]-d[b],axis=1);i=int(np.argmax(jump))
    report['finite']&=bool(np.isfinite(p).all())
    report['shape_edges'].append({'name':key.name,'max_delta_m':float(np.linalg.norm(d[:half],axis=1).max()),
        'max_neighbor_delta_m':float(jump[i]),'that_edge_length_m':float(length[i]),
        'paired_wall_delta_error_m':float(np.linalg.norm(d[:half]-d[half:],axis=1).max())})
manifest=json.loads((ROOT/'stable_manifest.json').read_text(encoding='utf-8'))
curves=json.loads((ROOT/'stable_curves.json').read_text(encoding='utf-8'))
for role in ['idle','walk']:
    frames=manifest[role]['samples'];first=delta['FRS4_%s_%03d'%(role,frames[0])];last=delta['FRS4_%s_%03d'%(role,frames[-1])]
    report['loops'][role]={'shape_endpoint_error_m':float(np.linalg.norm(first-last,axis=1).max())}
report['curve_weight_sums']={role:[float(v) for v in (np.min(np.array(list(tracks.values())).sum(0)),np.max(np.array(list(tracks.values())).sum(0)))] for role,tracks in curves.items()}
report['shape_edges'].sort(key=lambda x:-x['max_neighbor_delta_m'])
(OUT/'source.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M05_READ_ONLY_SOURCE_REVIEW '+json.dumps({'finite':report['finite'],'worst_edges':report['shape_edges'][:3],'loops':report['loops']}),flush=True)
