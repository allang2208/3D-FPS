"""Read author meshes and saved clothing curves; do not save or render scenes."""
import bpy,json,math
import numpy as np
from pathlib import Path
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessStaffReview20261009')
assets=json.loads((OUT/'assets.json').read_text(encoding='utf-8'))
roots={'Security':Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008/V11'),
       'Receptionist':Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessReceptionist20261007/V04')}
report={'source_saved':False,'rendered':False,'characters':{}}
for who,root in roots.items():
    version='V11' if who=='Security' else 'V04'
    source=root/'Authoring'/('Faceless'+who+'_'+version+'.blend')
    bpy.ops.wm.open_mainfile(filepath=str(source))
    rigs=[o for o in bpy.context.scene.objects if o.type=='ARMATURE']
    bonenames={b.name for r in rigs for b in r.data.bones}
    data={'source':str(source),'meshes':{},'curve_shape_endpoints':{}}
    for o in bpy.context.scene.objects:
        if o.type!='MESH':continue
        p=np.empty(len(o.data.vertices)*3,np.float64);o.data.vertices.foreach_get('co',p);p=p.reshape((-1,3))
        groups={g.index:g.name for g in o.vertex_groups};weighted=any(m.type=='ARMATURE' for m in o.modifiers)
        totals=np.array([sum(g.weight for g in v.groups if groups[g.group] in bonenames) for v in o.data.vertices])
        row={'vertices':len(p),'armature_modifier':weighted,'finite_coordinates':bool(np.isfinite(p).all()),
            'unweighted_vertices':int((totals<1e-6).sum()) if weighted else None,
            'weight_sum_range':[float(totals.min()),float(totals.max())] if weighted and len(totals) else None,
            'shape_count':len(o.data.shape_keys.key_blocks)-1 if o.data.shape_keys else 0}
        data['meshes'][o.name]=row
        if not o.data.shape_keys:continue
        keys=o.data.shape_keys.key_blocks;basis=np.empty(p.size,np.float64);keys[0].data.foreach_get('co',basis);basis=basis.reshape(p.shape)
        delta={}
        for key in list(keys)[1:]:
            co=np.empty(p.size,np.float64);key.data.foreach_get('co',co);co=co.reshape(p.shape)
            row['finite_coordinates']&=bool(np.isfinite(co).all());delta[key.name]=co-basis
        endpoints={}
        for role,tracks in assets['characters'][who]['morph_curve_keys'].items():
            ends=[]
            for idx in [0,-1]:
                d=np.zeros_like(p)
                for name,(_,values) in tracks.items():
                    if name in delta and values:d+=delta[name]*values[idx]
                ends.append(d)
            endpoints[role]=ends
        metrics={}
        for old,new in [('attack','idle'),('attack','walk'),('idle','hit'),('walk','hit'),('walk','walk'),('idle','idle')]:
            if old not in endpoints or new not in endpoints:continue
            d=np.linalg.norm(endpoints[old][-1]-endpoints[new][0],axis=1)
            metrics[old+'_to_'+new]={'max_bind_shape_displacement_cm':float(d.max()*100),
                'vertices_over_1cm':int((d>.01).sum())}
        data['curve_shape_endpoints'][o.name]=metrics
    report['characters'][who]=data
(OUT/'author_data.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M03_M04_AUTHOR_REVIEW '+json.dumps({k:{'mesh_count':len(v['meshes']),
    'weight_problems':[n for n,r in v['meshes'].items() if r['unweighted_vertices']],
    'nonfinite':[n for n,r in v['meshes'].items() if not r['finite_coordinates']]} for k,v in report['characters'].items()}),flush=True)