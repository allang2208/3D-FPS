"""Save only the five M249 sparse profiles, with exact input/dirty guards."""
from pathlib import Path
import unreal as u
import pickle,gzip,json,hashlib,zipfile
r=Path(__file__).resolve().parent;project=r.parents[2]
d=pickle.load(open(r/'current.pkl','rb'));inputs=json.loads((r/'inputs.json').read_text())
extra=json.loads((r/'extra_inputs.json').read_text());d['profiles']['bipod']=extra['bipod'];inputs['hashes'].update(extra['hashes'])
mounts=[p for p in extra['hashes'] if '/Meshes/' in p]
paths=[p['asset'] for p in d['profiles'].values()]+mounts
receipt=json.loads((r/'install_receipt.json').read_text()) if (r/'install_receipt.json').exists() else dict(saved={},mounts={},unchanged_base_animations=True,complete=False)
receipt['complete']=False
def disk(path):return project/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
if '-run=' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('Existing PIE retained')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(paths):raise RuntimeError('Unsaved target profiles retained')
for path,sha in inputs['hashes'].items():
    if hashlib.sha256(disk(path).read_bytes()).hexdigest()!=receipt['saved'].get(path,sha):raise RuntimeError('Input changed: '+path)
if not (r/'before.zip').exists():
    with zipfile.ZipFile(r/'before.zip','x',zipfile.ZIP_DEFLATED) as z:
        for path in paths:z.write(disk(path),str(disk(path).relative_to(project)))
elif not (r/'install_receipt.json').exists():raise RuntimeError('Partial import needs explicit recovery')
for path in mounts:
    if path in receipt['saved']:continue
    a=u.load_asset(path)
    if a.get_num_lods()!=1:raise RuntimeError('Unexpected mount LODs: '+path)
    materials=[(str(s.material_slot_name),s.material_interface.get_path_name()) for s in a.static_materials]
    dm,result=u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(a,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Mount read '+path)
    _,points,_=u.GeometryScript_MeshQueries.get_all_vertex_positions(dm,False)
    points=u.GeometryScript_List.convert_vector_list_to_array(points)
    before=[v.to_tuple() for v in points]
    u.GeometryScript_MeshTransforms.translate_mesh(dm,u.Vector(0,3,0))
    options=u.GeometryScriptCopyMeshToAssetOptions();options.set_editor_property('use_original_vertex_order',True)
    _,result=u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dm,a,options,u.GeometryScriptMeshWriteLOD())
    if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Mount write '+path)
    if [(str(s.material_slot_name),s.material_interface.get_path_name()) for s in a.static_materials]!=materials:raise RuntimeError('Mount materials changed')
    if not u.EditorAssetLibrary.save_loaded_asset(a,False):raise RuntimeError('Mount save '+path)
    receipt['saved'][path]=hashlib.sha256(disk(path).read_bytes()).hexdigest()
    receipt['mounts'][path]=dict(shift_root_cm=[0,3,0],vertices=len(before),materials_preserved=True)
    (r/'install_receipt.json').write_text(json.dumps(receipt,indent=2))
for family,p in d['profiles'].items():
    payload=json.load(gzip.open(r/(family+'.json.gz'),'rt'))
    if any(c.get('retained') for c in payload['clips']):raise RuntimeError('Unexpected retained clip')
    a=u.load_asset(p['asset'])
    if not a.set_shared_clips_from_json(json.dumps(payload)):raise RuntimeError('Profile import failed: '+family)
    if not u.EditorAssetLibrary.save_loaded_asset(a,False):raise RuntimeError('Profile save failed: '+family)
    receipt['saved'][p['asset']]=hashlib.sha256(disk(p['asset']).read_bytes()).hexdigest()
    (r/'install_receipt.json').write_text(json.dumps(receipt,indent=2))
receipt['complete']=True;(r/'install_receipt.json').write_text(json.dumps(receipt,indent=2))
print('WRIST33_SAVED',len(receipt['saved']),'assets; base animations and skeletal mesh unchanged',flush=True)
