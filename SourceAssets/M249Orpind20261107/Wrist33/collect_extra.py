from pathlib import Path
import unreal as u,json,pickle,hashlib
r=Path(__file__).resolve().parent;project=r.parents[2];data={};dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for key in ('vertical','tactical_vertical','prism'):
    path='/Game/Weapons/M249/CommonParts20261108/Meshes/SM_M249_'+key
    if path in dirty:raise RuntimeError('Unsaved mount retained')
    asset=u.load_asset(path);data[path]=hashlib.sha256((project/'Content'/(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()
path='/Game/Weapons/M249/Bipod/DA_M249_Bipod';a=u.load_asset(path)
if path in dirty:raise RuntimeError('Unsaved bipod retained')
data[path]=hashlib.sha256((project/'Content'/(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()
rows=[]
for c in a.get_editor_property('clips'):
    v=c.get_editor_property
    if v('retained'):raise RuntimeError('Retained bipod clip')
    rows.append(dict(base=v('base').get_path_name(),duration=v('duration'),retained=None,tracks=[dict(bone=str(t.get_editor_property('bone')),times=list(t.get_editor_property('times')),values=list(t.get_editor_property('values')))for t in v('tracks')]))
(r/'extra_inputs.json').write_text(json.dumps(dict(hashes=data,bipod=dict(asset=path,clips=rows)),indent=2))
(r/'geometry_api.txt').write_text(str(u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh.__doc__)+'\n'+str(u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh.__doc__)+'\n'+str(u.GeometryScript_MeshTransforms.translate_mesh.__doc__))
print('WRIST33_EXTRA_INPUTS',len(data),flush=True)
