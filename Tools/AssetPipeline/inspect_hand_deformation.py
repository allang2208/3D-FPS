"""Read-only deformation evidence on the delivered WRAD/AKM mesh."""
import bpy, json
import numpy as np
from pathlib import Path

root = Path(r'D:/FPS3D/FPSGAME')
out = root / 'SourceAssets/ArmsRepair20260909'
out.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(root / 'SourceAssets/AKMReplacement/SK_AKM_Replacement_Source.blend'))
rig = bpy.data.objects['SK_AKM_Viewmodel']
mesh = bpy.data.objects['SK_ArmsReplacement_WRAD']
rest = np.array([tuple(v.co) for v in mesh.data.vertices])
edges = np.array([tuple(e.vertices) for e in mesh.data.edges])
lengths = np.linalg.norm(rest[edges[:, 0]] - rest[edges[:, 1]], axis=1)
weights = [{mesh.vertex_groups[g.group].name: float(g.weight) for g in v.groups if g.weight > 0.0001} for v in mesh.data.vertices]
bone_names = ['lowerarm_l','lowerarm_twist_01_l','hand_l','upperarm_twist_01_l',
              'lowerarm_r','lowerarm_twist_01_r','hand_r','upperarm_twist_01_r']
report = {'mesh': mesh.name, 'samples': [], 'armature_modifiers': [
    {'name': m.name, 'preserve_volume': m.use_deform_preserve_volume} for m in mesh.modifiers if m.type == 'ARMATURE']}
for action_name, frames in [('idle',[1]), ('aim',[1]), ('reload',[15,24,35,52,66]), ('reload_empty',[42,52,66,75,88,96])]:
    action = bpy.data.actions['AKM_' + action_name]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    for frame in frames:
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        obj = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
        evaluated = obj.to_mesh()
        posed = np.array([tuple(v.co) for v in evaluated.vertices])
        obj.to_mesh_clear()
        ratios = np.linalg.norm(posed[edges[:,0]]-posed[edges[:,1]],axis=1) / np.maximum(lengths, 1e-8)
        valid = lengths > 1e-5
        top = np.argsort(np.where(valid, ratios, 0))[-6:][::-1]
        sample = {'action': action_name, 'frame': frame,
            'edge_ratio_p01_p50_p99_max': np.quantile(ratios[valid], [0.01,0.5,0.99,1]).tolist(),
            'worst_edges': [{'edge': edges[i].tolist(), 'ratio': float(ratios[i]),
                            'weights': [weights[v] for v in edges[i]]} for i in top],
            'bones': {n: {'local_rotation_degrees': [float(v*180/np.pi) for v in rig.pose.bones[n].matrix_basis.to_euler()],
                          'local_scale': list(rig.pose.bones[n].matrix_basis.to_scale())} for n in bone_names}}
        report['samples'].append(sample)
(out / 'delivered_deformation.json').write_text(json.dumps(report, indent=2), encoding='utf8')
print('HAND_DEFORMATION_EVIDENCE', json.dumps([(s['action'],s['frame'],s['edge_ratio_p01_p50_p99_max']) for s in report['samples']]))
