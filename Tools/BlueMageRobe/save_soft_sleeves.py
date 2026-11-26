"""Save up to four native sleeve packages per batch using the existing garment writer."""
import gc, hashlib, json, sys
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018/FPSoftSleeves20261020'
sys.path.insert(0,str(P/'Tools/BlueMageRobe'))
import save_assets as io
import soft_sleeve_materials
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():raise RuntimeError('End play before saving native robe sleeves')
manifest=json.loads((R/'manifest.json').read_text())
group=soft_sleeve_materials.create()
baseline=json.loads((P/'SourceAssets/BlueMageRobe20261018/saved_assets.json').read_text())
mats=[u.load_asset(p) for p in baseline['materials']['FP']]
mats[1],mats[2],mats[3]=group
io.receipt_path=R/'saved_assets.json'
io.receipt=json.loads(io.receipt_path.read_text()) if io.receipt_path.exists() else dict(saved={},runtime_tested=False)
io.receipt.update(completed=False,routes=manifest['routes'],materials=[m.get_path_name() for m in mats])

def dynamic(d,ref=None,display=False):
    ids={str(b.name):b.index for b in io.B.get_all_bones_info(ref)[1]}
    ps=[];ns=[];uv=[];ws=[];colors=[];fs=[];lookup={}
    for fi,face in enumerate(d['triangles']):
        tri=[]
        for ci,vi in enumerate(face):
            normal=d['normals'][fi][ci];tex=d['uv'][fi][ci]
            key=(vi,*[round(x,7) for x in normal+tex])
            if key not in lookup:
                lookup[key]=len(ps);ps.append(u.Vector(*d['positions'][vi]))
                ns.append(u.Vector(*normal));uv.append(u.Vector2D(*tex))
                ws.append(d['weights'][vi]);colors.append(u.LinearColor(*d['colors'][vi]))
            tri.append(lookup[key])
        fs.append(u.IntVector(*tri))
    dm=u.DynamicMesh()
    u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,
        u.GeometryScriptSimpleMeshBuffers(vertices=ps,normals=ns,uv0=uv,vertex_colors=colors,triangles=fs),0,True)
    io.B.copy_bones_from_mesh(ref,dm);io.B.mesh_create_bone_weights(dm)
    for i,bindings in enumerate(ws):
        _,ok=io.B.set_vertex_bone_weights(dm,i,[u.GeometryScriptBoneWeight(bone_index=ids[n],weight=w) for n,w in bindings.items()])
        if not ok:raise RuntimeError('Sleeve native binding '+d['profile'])
    for i,slot in enumerate(d['triangle_materials']):u.GeometryScript_Materials.set_triangle_material_id(dm,i,slot,True)
    return dm
io.dynamic=dynamic
io.record()
remaining=[r for r in manifest['records'] if
    io.receipt['saved'].get('FP/'+r['profile'],{}).get('author_sha256')!=
    hashlib.sha256(Path(r['file']).read_bytes()).hexdigest()]
for row in remaining[:4]:
    io.skeletal(Path(row['file']),mats,revision='FPSoftSleeves20261020')
    gc.collect();u.SystemLibrary.collect_garbage()
io.receipt['completed']=len(remaining)<=4
io.record()
print('SOFT_ROBE_SLEEVES_BATCH',len(io.receipt['saved']),len(manifest['records']),
      'complete='+str(io.receipt['completed']),flush=True)
