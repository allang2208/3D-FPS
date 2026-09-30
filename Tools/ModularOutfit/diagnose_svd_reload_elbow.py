"""User-requested SVD regrip diagnosis using current compressed/native inputs.

Compares the previous runtime correction, source pose and revised correction.
No editor, game, asset writes, or runtime visual acceptance.
"""
import importlib.util
from pathlib import Path
import numpy as np
import trimesh
import diagnose_chainmail_camera as current
from garment_pipeline import read, write, digest, asset_file
from garment_motion import matrix, prepare, posed

P = Path('D:/FPS3D/FPSGAME')
R = P / 'SourceAssets/SVDReloadElbow20260930'
SOURCE = P / 'SourceAssets/ChainmailCameraClearance20260929/SVD'
spec = importlib.util.spec_from_file_location('previous_clearance', R/'Before/diagnose_chainmail_camera.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)


def flex(bones, side):
    a, e, h = [bones[n+'_'+side][:3, 3] for n in ('upperarm', 'lowerarm', 'hand')]
    u, l = e-a, h-e
    return float(np.degrees(np.arccos(np.clip(u@l/np.linalg.norm(u)/np.linalg.norm(l), -1., 1.))))


def main():
    inputs = read(SOURCE/'poses.json')
    assert digest(asset_file(inputs['native'])) == inputs['native_sha256']
    for clip, sha in inputs['clips'].items():
        assert digest(asset_file(clip)) == sha, 'Resample changed clip: '+clip
    meshes = [read(SOURCE/f'LOD{lod}.json') for lod in range(3)]
    for mesh in meshes:
        assert digest(asset_file(mesh['source'])) == mesh['asset_sha256']
    data = [prepare(mesh) for mesh in meshes]
    upper_ids = np.array([i for i,w in enumerate(meshes[0]['weights'])
        if sum(v for n,v in w.items() if n.startswith(('clavicle', 'upperarm'))) > .65])
    bare = read(SOURCE/'bare.json')
    bare_data = prepare(bare)
    # Bind-space correspondence follows the SAME skin triangles over time. It
    # measures local sleeve/skin separation, not global mesh collision or WPO.
    # Exclude deliberate cuff overlaps and material 2 inner return/binding.
    shell_vertices = set(np.array(meshes[0]['triangles'])[np.array(meshes[0]['materials']) == 0].flat)
    arm_ids = np.array([i for i,w in enumerate(meshes[0]['weights']) if i in shell_vertices
        and sum(v for n,v in w.items() if n.endswith('_l') and n.startswith(('upperarm','lowerarm'))) > .95])
    skin_surface = trimesh.Trimesh(bare['positions'], bare['triangles'], process=False)
    closest, _, triangle = trimesh.proximity.closest_point(skin_surface, np.array(meshes[0]['positions'])[arm_ids])
    associated = np.array(bare['triangles'])[triangle]
    bary = trimesh.triangles.points_to_barycentric(skin_surface.triangles[triangle], closest)
    edge_sets = []
    for mesh in meshes:
        f = np.array(mesh['triangles'])
        left = np.array([sum(v for n,v in w.items() if n.endswith('_l')) > .95 for w in mesh['weights']])
        f = f[np.all(left[f], axis=1)]
        edges = np.unique(np.sort(np.concatenate([f[:,[0,1]], f[:,[1,2]], f[:,[2,0]]]), axis=1), axis=0)
        rest = np.linalg.norm(np.array(mesh['positions'])[edges[:,0]] - np.array(mesh['positions'])[edges[:,1]], axis=1)
        edge_sets.append((edges,rest))
    rows = []
    for sample in inputs['poses']:
        b = {n:matrix(t) for n,t in sample['bones'].items()}
        name = sample['clip'].rsplit('/',1)[-1]
        for optic in (['pso','lpvo'] if name.endswith('_aim') else ['hip']):
            frame = current.camera_frame(b, optic)
            old, old_details = previous.correct(b, frame)
            new, new_details = current.correct(b, frame)
            immutable = [n for n in b if n.startswith(('hand_','thumb_','index_','middle_','ring_','pinky_','WPN_'))]
            row = dict(clip=name, time=sample['time'], optic=optic,
                flex_source=flex(b,'l'), flex_previous=flex(old,'l'), flex_revised=flex(new,'l'),
                left_pose_delta=max(float(np.max(np.abs(new[n]-b[n]))) for n in b if n.endswith('_l')),
                immutable_delta=max(float(np.max(np.abs(new[n]-b[n]))) for n in immutable),
                max_length_error=max((max(c['upper_length_error'],c['lower_length_error']) for c in new_details),default=0),
                upper_intrusion_revised=current.intrusion(posed(data[0],new),frame,upper_ids),
                new_sides=[c['side'] for c in new_details])
            if 'reload' in name and sample['time'] >= 2.:
                row['sleeve'] = {}
                for label, bones in [('source',b),('previous',old),('revised',new)]:
                    points = posed(data[0],bones)
                    skin = posed(bare_data,bones)[associated]
                    # Native UE render triangles have clockwise front winding.
                    normals = np.cross(skin[:,2]-skin[:,0], skin[:,1]-skin[:,0])
                    normals /= np.maximum(np.linalg.norm(normals,axis=1)[:,None],1.e-12)
                    clearance = np.sum((points[arm_ids]-np.sum(skin*bary[:,:,None],axis=1))*normals,axis=1)
                    lods = []
                    for prepared,(edges,rest) in zip(data,edge_sets):
                        surface = posed(prepared,bones)
                        lengths = np.linalg.norm(surface[edges[:,0]]-surface[edges[:,1]],axis=1)
                        lods.append(dict(max_edge_cm=float(lengths.max()),
                            max_stretch=float(np.max(lengths[rest>.1]/rest[rest>.1]))))
                    row['sleeve'][label] = dict(min_clearance_cm=float(clearance.min()),
                        below_zero=int(np.sum(clearance<0)), lods=lods)
            rows.append(row)
    reloads = [r for r in rows if 'reload' in r['clip'] and r['time'] >= 2.]
    summary = dict(samples=len(rows),regrip_samples=len(reloads),
        previous_regrip_locked_samples=sum(r['flex_previous']<3. and r['flex_source']>10. for r in reloads),
        revised_regrip_locked_samples=sum(r['flex_revised']<3. and r['flex_source']>10. for r in reloads),
        max_regrip_left_source_delta=max(r['left_pose_delta'] for r in reloads),
        max_immutable_delta=max(r['immutable_delta'] for r in rows),
        max_length_error=max(r['max_length_error'] for r in rows),
        revised_upper_intrusion_cases=sum(r['upper_intrusion_revised']>0 for r in rows),
        max_regrip_clearance_change_cm=max(abs(r['sleeve']['source']['min_clearance_cm']-r['sleeve']['revised']['min_clearance_cm']) for r in reloads),
        min_regrip_clearance_cm=min(r['sleeve']['revised']['min_clearance_cm'] for r in reloads),
        runtime_visual='not_run',
        limits='Compressed samples, hip framing for reload; fixed upper cone; bind-corresponding sleeve/skin clearance excludes cuff/lining, WPO and global collisions')
    write(R/'diagnosis.json',dict(summary=summary,inputs=dict(native_sha256=inputs['native_sha256'],clips=inputs['clips']),rows=rows))
    print(summary, flush=True)


if __name__ == '__main__':
    main()
