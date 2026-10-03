"""Measure only the reported leg-root region in matching authored turn poses."""
from pathlib import Path
import json
import bpy,numpy as np
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent/'RigV1'
geo=np.load(BASE/'source_geometry.npz');v=geo['unique'];edges=geo['edges']
cfg=json.loads((BASE/'rig_definition.json').read_text(encoding='utf8'))
region=np.zeros(len(v),bool)
for leg in cfg['legs']:region|=np.linalg.norm(v-np.array(leg['points'][0]),axis=1)<.22
selected_edges=edges[region[edges].all(axis=1)];ids=np.unique(selected_edges)
lookup=np.full(len(v),-1);lookup[ids]=np.arange(len(ids));local=lookup[selected_edges]
base_length=np.linalg.norm(v[selected_edges[:,0]]-v[selected_edges[:,1]],axis=1)
keep=base_length>.001;local=local[keep]
report={'scope':'authored turn poses; hip-root surface edges only; excludes UE foot-plant execution','poses':{},'root_vertices':len(ids),'root_edges':len(local)}
for revision,blend,data_path in [('before',ROOT.parent/'HowlV4/Delivery/M10_HowlV4_Editable.blend',BASE/'authored_weights.npz'),('after',ROOT/'Delivery/M10_SurfaceRigV5_Editable.blend',ROOT/'surface_rig_data.npz')]:
    bpy.ops.wm.open_mainfile(filepath=str(blend));scene=bpy.context.scene;rig=next(o for o in scene.objects if o.type=='ARMATURE')
    data=np.load(data_path);indices=data['bone_indices'][ids];weights=data['weights'][ids];names=data['bone_names']
    if not np.isfinite(weights).all() or not np.allclose(weights.sum(axis=1),1,atol=2e-6):raise RuntimeError('Invalid root weights')
    positions=v[ids].copy()
    if revision=='after':positions+=data['displacement'][ids]
    rest={b.name:b.matrix_local.inverted() for b in rig.data.bones};baseline=np.linalg.norm(positions[local[:,0]]-positions[local[:,1]],axis=1)
    records=[]
    for role in ('CurveLeft','CurveRight','PivotLeft','PivotRight'):
        action=bpy.data.actions['M10_'+role+('_V2' if revision=='before' else '_V5')]
        rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
        for frame in (1,10,19,28):
            scene.frame_set(frame);matrices=np.array([rig.pose.bones[str(name)].matrix@rest[str(name)] for name in names])
            posed=np.zeros_like(positions)
            for slot in range(4):
                transforms=matrices[indices[:,slot]]
                posed+=weights[:,slot,None]*(np.einsum('nij,nj->ni',transforms[:,:3,:3],positions)+transforms[:,:3,3])
            ratio=np.linalg.norm(posed[local[:,0]]-posed[local[:,1]],axis=1)/baseline
            distortion=np.maximum(ratio,1/np.maximum(ratio,1e-6))
            records.append({'clip':role,'frame':frame,'edge_distortion_p95':float(np.percentile(distortion,95)),'edge_distortion_p99':float(np.percentile(distortion,99)),'edges_over_2x':int((distortion>2).sum())})
    report['poses'][revision]=records
(ROOT/'root_deformation_diagnosis.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({key:{'mean_p99':float(np.mean([r['edge_distortion_p99'] for r in rows])),'sum_edges_over_2x':sum(r['edges_over_2x'] for r in rows)} for key,rows in report['poses'].items()}),flush=True)
