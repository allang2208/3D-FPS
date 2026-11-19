"""Numerical comparison of the actual saved UE donor and candidate."""
import json,sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from leg_proportions import LegProportions
from muscle_shape import MuscleShape
OUT=Path(globals().get('variant_output','D:/FPS3D/FPSGAME/SourceAssets/JasonStrong20261117/R2_LongLegs'))
ShapeClass=globals().get('variant_shape_class',MuscleShape)
REVIEW=OUT/'AnatomyReview'
a=json.loads((REVIEW/'original_saved_mesh.json').read_text())
b=json.loads((REVIEW/'derived_saved_mesh.json').read_text())
prop=LegProportions(a['bones'])
P,Q=np.array(a['positions']),np.array(b['positions'])
T,S=np.array(a['triangles']),np.array(b['triangles'])
report={'source':a['source'],'candidate':b['source']}
report['bone_count']=len(b['bones'])
report['hierarchy_identical']=[(x['name'],x['parent']) for x in a['bones']]==[(x['name'],x['parent']) for x in b['bones']]
report['skeleton_asset_identical']=a['skeleton']==b['skeleton']
report['materials_identical']=a['materials']==b['materials']
report['topology_identical']=a['triangles']==b['triangles']
report['uv_identical']=a['triangle_uvs']==b['triangle_uvs']
report['vertex_count']=len(Q)
report['triangle_count']=len(S)
report['raw_weight_entry_order_identical']=a['weights']==b['weights']
report['weight_influences_and_values_identical']=all(dict(x)==dict(y) for x,y in zip(a['weights'],b['weights']))
report['max_weight_sum_error']=max(abs(sum(w for i,w in ws)-1) for ws in b['weights'])
report['invalid_weight_vertices']=[i for i,ws in enumerate(b['weights']) if not ws or any(j<0 or j>=len(b['bones']) or w<=0 or not np.isfinite(w) for j,w in ws)]
report['max_world_axis_change']=float(max(np.max(np.abs(np.array(x['axes'])-np.array(y['axes']))) for x,y in zip(a['bones'],b['bones'])))
report['max_local_axis_change']=float(max(np.max(np.abs(np.array(x['local']['axes'])-np.array(y['local']['axes']))) for x,y in zip(a['bones'],b['bones'])))
report['max_expected_bind_position_error_cm']=float(max(np.linalg.norm(np.array(prop.point(x['position']))-y['position']) for x,y in zip(a['bones'],b['bones'])))
report['max_geometry_vs_mesh_bind_position_error_cm']=float(max(np.linalg.norm(np.array(y['geometry_bone']['position'])-y['position']) for y in b['bones']))
axes=np.array([x['axes'] for x in b['bones']])
report['bind_basis_determinant_range']=[float(v) for v in (np.min(np.linalg.det(axes)),np.max(np.linalg.det(axes)))]
report['max_basis_orthogonality_error']=float(np.max(np.abs(axes@np.transpose(axes,(0,2,1))-np.eye(3))))
report['nonfinite_positions']=int(np.count_nonzero(~np.isfinite(Q)))
morph=ShapeClass(a['bones'],seam_segments=json.loads((OUT/'neck_seam.json').read_text()))
expected=np.array([prop.deform(p,morph.deform(p,w)) for p,w in zip(a['positions'],a['weights'])])
report['max_saved_mesh_vs_authored_position_error_cm']=float(np.max(np.linalg.norm(Q-expected,axis=1))) if len(Q)==len(expected) else None
if report['topology_identical']:
    edges=np.unique(np.sort(np.concatenate([T[:,[0,1]],T[:,[1,2]],T[:,[2,0]]]),axis=1),axis=0)
    E=np.linalg.norm(P[edges[:,0]]-P[edges[:,1]],axis=1)
    F=np.linalg.norm(Q[edges[:,0]]-Q[edges[:,1]],axis=1)
    report['rest_edge_length_ratio_percentiles']=np.percentile(F[E>1e-4]/E[E>1e-4],[0,1,50,99,100]).tolist()
    c0=np.cross(P[T[:,1]]-P[T[:,0]],P[T[:,2]]-P[T[:,0]])
    c1=np.cross(Q[S[:,1]]-Q[S[:,0]],Q[S[:,2]]-Q[S[:,0]])
    area0=np.linalg.norm(c0,axis=1);area1=np.linalg.norm(c1,axis=1)
    report['new_collapsed_triangles']=int(np.count_nonzero((area0>1e-6)&(area1<1e-6)))
    report['rest_normal_dot_negative_count']=int(np.count_nonzero(np.einsum('ij,ij->i',c0,c1)<-1e-8))
    report['rest_area_ratio_percentiles']=np.percentile(area1[area0>1e-6]/area0[area0>1e-6],[0,1,50,99,100]).tolist()
    prior=REVIEW/'derived_before_refinement.json'
    if prior.exists():
        old=np.array(json.loads(prior.read_text())['positions'])
        co=np.cross(old[S[:,1]]-old[S[:,0]],old[S[:,2]]-old[S[:,0]])
        report['local_refinement']={'areas':['inner upper arm / armpit transition','medial upper thigh / crotch transition'],
            'before_rest_normal_dot_negative_count':int(np.count_nonzero(np.einsum('ij,ij->i',c0,co)<-1e-8)),
            'after_rest_normal_dot_negative_count':report['rest_normal_dot_negative_count'],
            'max_local_vertex_refinement_cm':float(np.max(np.linalg.norm(Q-old,axis=1)))}

report['measurements']={}
for label,data in [('original',a),('derived',b)]:
    joints={x['name']:np.array(x['position']) for x in data['bones']}
    m={}
    for side in ['l','r']:
        for part,end in [('upperarm','lowerarm'),('lowerarm','hand'),('thigh','calf'),('calf','foot')]:
            m[part+'_'+side+'_length_cm']=float(np.linalg.norm(joints[part+'_'+side]-joints[end+'_'+side]))
    m['knee_height_cm']=float(joints['calf_l'][2])
    m['hip_joint_height_cm']=float(joints['thigh_l'][2])
    m['ankle_height_cm']=float(joints['foot_l'][2])
    head=json.loads((OUT/'head_source.json').read_text())
    height=max(p[2] for p in head['positions'])+(prop.total_gain if label=='derived' else 0)-min(p[2] for p in data['positions'])
    m['total_height_cm']=height
    m['hip_height_to_stature']=m['hip_joint_height_cm']/height
    m['bilateral_limb_length_max_difference_cm']=max(abs(m[p+'_l_length_cm']-m[p+'_r_length_cm']) for p in ['upperarm','lowerarm','thigh','calf'])
    report['measurements'][label]=m

(REVIEW/'numerical_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
