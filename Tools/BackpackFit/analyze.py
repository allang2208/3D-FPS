"""Measure actual rear-surface separation in the saved reference pose, in cm."""
import json,os
from pathlib import Path
import numpy as np
from mathutils import Vector,Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
P=Path('D:/FPS3D/FPSGAME');R=Path(os.environ.get('BACKPACK_FIT_RUN_DIR',P/'SourceAssets/BackpackFit20261024/ContactAuditR1'))
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
plan=read(R/'plan.json');captured=read(R/'captured.json')
native=read(R/'native_contacts.json')['cases'] if (R/'native_contacts.json').exists() else []
for row in plan['rows']:
    contact=next((n for n in native if n['rig'].lower()==row['rig'].lower() and n['item']==row['item'] and n['shirt']==row['shirt']),None)
    if contact:
        row['settled_field']=contact['current_and_previous_wpo']
        if row.get('rigid_mesh'):
            row['rigid_location']=contact['rigid_location'];row['rigid_rotation_quat']=contact['rigid_rotation_quat']
def rotation(q):return np.asarray(Quaternion((q[3],q[0],q[1],q[2])).to_matrix())
def load(path,render=False):
    rec=captured[path];folder=Path(rec['folder']);prefix='render_' if render and 'render_vertices' in rec else ''
    v=np.fromfile(folder/(prefix+'positions.bin'),dtype='<f4').reshape(-1,3).astype(float)
    f=np.fromfile(folder/(prefix+'triangles.bin'),dtype='<i4').reshape(-1,3)
    f=f[np.all((f>=0)&(f<len(v)),axis=1)]
    return v,f
male={b['name']:b for b in captured[plan['rigs']['Jason']['body']]['bones']}
frames={};trees={};normal_meshes={}
for rig,data in plan['rigs'].items():
    bones={b['name']:b for b in captured[data['body']]['bones']}
    source,target=male['spine_04'],bones['spine_04']
    matrix=rotation(source['rotation'])@rotation(target['rotation']).T
    translation=np.asarray(target['position'])-np.asarray(source['position'])@matrix
    shoulder=(np.asarray(bones['clavicle_l']['position'])-translation)@matrix.T
    frames[rig]=(matrix,translation,float(shoulder[2]-male['clavicle_l']['position'][2]))
def normalized(rig,v):
    matrix,translation,_=frames[rig];return (v-translation)@matrix.T
def tree(rig,path):
    key=(rig,path)
    if key not in trees:
        v,f=load(path);v=normalized(rig,v);normal_meshes[key]=(v,f)
        trees[key]=BVHTree.FromPolygons(v.tolist(),f.tolist(),all_triangles=True)
    return trees[key]
def ray_y(bvh,x,z,inner=False):
    hit=bvh.ray_cast(Vector((x,100. if inner else -100.,z)),Vector((0.,-1. if inner else 1.,0.)),200.)
    return hit[0].y if hit[0] is not None else None
def stats(values):
    v=np.asarray(values,float)
    if not len(v):return {'samples':0}
    return {'samples':len(v),'mean_cm':float(v.mean()),'median_cm':float(np.median(v)),'p90_cm':float(np.quantile(v,.9)),
            'max_cm':float(v.max()),'over_3cm_percent':float(np.mean(v>3)*100),'over_5cm_percent':float(np.mean(v>5)*100),
            'negative_under_minus_0_2cm_percent':float(np.mean(v<-.2)*100)}
results=[]
for row in plan['rows']:
    rig=row['rig'];body_tree=tree(rig,row['body'])
    cloth_trees=[tree(rig,path) for path in row.get('garment_surfaces',[row['garment']] if row['garment'] else [])]
    source_v,source_f=load(row['mesh']);rec=captured[row['mesh']]
    if not rec['mask_valid']:raise RuntimeError('Missing saved deformation mask '+row['mesh'])
    mask=np.fromfile(Path(rec['folder'])/'mask.bin',dtype='<f4')
    render_v,render_f=load(row['mesh'],True)
    kd=KDTree(len(source_v))
    for i,point in enumerate(source_v):kd.insert(point,i)
    kd.balance();mapping=[kd.find(point) for point in render_v]
    render_mask=np.asarray([mask[index] for _,index,_ in mapping]);mapping_error=max(distance for _,_,distance in mapping)
    if 'settled_field' in row:
        field=np.asarray(row['settled_field']);render_v=render_v+((render_v-field[:3])@field[3:12].reshape(3,3).T+field[12:15])*render_mask[:,None]
    if row.get('rigid_mesh'):
        shell,shell_f=load(row['rigid_mesh']);shell=shell@rotation(row['rigid_rotation_quat']).T+row['rigid_location']
    else:
        shell=render_v
        if rec.get('cargo_vertices'):
            cargo=np.fromfile(rec['cargo_vertices'],dtype='u1');render_cargo=np.asarray([cargo[index] for _,index,_ in mapping]);shell_f=render_f[np.all(render_cargo[render_f]>0,axis=1)]
        else:shell_f=render_f[np.all(render_mask[render_f]>.98,axis=1)]
    shell=normalized(rig,shell)
    shell_tree=BVHTree.FromPolygons(shell.tolist(),shell_f.tolist(),all_triangles=True)
    shift=frames[rig][2];samples=[]
    for x in np.arange(-10.,10.01,.5):
        for z in np.arange(106.+shift,141.+shift,.5):
            b=ray_y(body_tree,x,z)
            hits=[v for v in [b,*[ray_y(t,x,z) for t in cloth_trees]] if v is not None]
            body_y=min(hits) if hits else None
            pack_y=ray_y(shell_tree,x,z,True)
            if body_y is not None and pack_y is not None:samples.append([float(x),float(z),float(body_y-pack_y)])
    fixed=normalized(rig,render_v[render_mask<.01]);fixed=fixed[(fixed[:,2]>98+shift)&(fixed[:,2]<150+shift)]
    distances=[]
    for point in fixed:
        candidates=[body_tree.find_nearest(Vector(point))]
        candidates.extend(t.find_nearest(Vector(point)) for t in cloth_trees)
        distances.append(min(hit[3] for hit in candidates if hit[0] is not None))
    gap=stats([s[2] for s in samples]);strap=stats(distances)
    result={'rig':rig,'item':row['item'],'shirt':row['shirt'],'shirt_surface_variants':len(cloth_trees),'shell_gap':gap,'fixed_strap_distance':strap,
            'render_to_source_max_distance_cm':float(mapping_error),'samples':samples,
            'motion_mode':('gravity_contact_settled' if native else 'gravity_contact_reference_only') if 'hanging_pack' in row else 'bounded_inertia',
            'large_gap_candidate':gap.get('over_5cm_percent',0)>20,'fixed_strap_gap_candidate':strap.get('over_3cm_percent',0)>10}
    if 'hanging_pack' in row and 'settled_field' in row:
        field=np.asarray(row['settled_field']);p=np.asarray(row['hanging_pack']['probes'])
        p=normalized(rig,p+(p-field[:3])@field[3:12].reshape(3,3).T+field[12:15])
        distances=[min(t.find_nearest(Vector(q))[3] for t in [body_tree,*cloth_trees]) for q in p]
        result['settled_contact_probes']={'minimum_cm':float(min(distances)),'within_1cm':int(sum(d<=1 for d in distances)),'count':len(distances),'distances_cm':distances}
    results.append(result)
    (R/'contact_progress.json').write_text(json.dumps(results,separators=(',',':')))
    print('BACKPACK_CONTACT',rig,row['item'],row['shirt'] or 'bare','gap_p90',round(gap.get('p90_cm',0),2),'over5',round(gap.get('over_5cm_percent',0),1),'strap_p90',round(strap.get('p90_cm',0),2),flush=True)
report={'scope':plan['scope'],'geometry_stage':plan.get('geometry_stage','saved_source_and_render'),
        'method':'opposing triangle rays over the central back, equal-area 0.5 cm stations; available built skeletal LOD0, otherwise explicitly labelled authored source; full Nanite source',
        'gap_candidate_rule':'more than 20% of overlapping central back samples exceed 5 cm; requires anatomical/visual classification',
        'rows':results,'missing_mappings':plan['missing_mappings'],'runtime_animation_tested':False,'network_tested':False,
        'capture_status':read(R/'capture_status.json') if (R/'capture_status.json').exists() else {'state':'authored_preview'}}
(R/'contact_report.json').write_text(json.dumps(report,indent=2)+'\n')
print('BACKPACK_CONTACT_COMPLETE',len(results),flush=True)
